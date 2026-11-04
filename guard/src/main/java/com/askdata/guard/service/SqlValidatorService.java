package com.askdata.guard.service;

import com.askdata.guard.model.ValidationResult;
import net.sf.jsqlparser.JSQLParserException;
import net.sf.jsqlparser.expression.Expression;
import net.sf.jsqlparser.expression.Function;
import net.sf.jsqlparser.expression.LongValue;
import net.sf.jsqlparser.parser.CCJSqlParserUtil;
import net.sf.jsqlparser.schema.Column;
import net.sf.jsqlparser.schema.Table;
import net.sf.jsqlparser.statement.Statement;
import net.sf.jsqlparser.statement.Statements;
import net.sf.jsqlparser.statement.select.*;
import net.sf.jsqlparser.util.TablesNamesFinder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Pattern;

@Service
public class SqlValidatorService {

    @Value("${guard.max-row-limit:1000}")
    private long maxRowLimit = 1000;

    // Allowed tables and analytical views
    private static final Set<String> ALLOWED_TABLES = Set.of(
            "v_users", "v_subscriptions", "v_payments", "v_events",
            "users", "subscriptions", "payments", "events"
    );

    // Blocked columns (PII, secrets, auth)
    private static final Set<String> BLOCKED_COLUMNS = Set.of(
            "email", "full_name", "password", "secret", "token", "passwd"
    );

    // Dangerous functions (DOS, file system access, execution)
    private static final Set<String> DANGEROUS_FUNCTIONS = Set.of(
            "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_write_file",
            "pg_terminate_backend", "pg_cancel_backend", "dblink", "dblink_exec",
            "query_to_xml", "system", "eval"
    );

    // Regex to detect multiple statements or comments attempting split bypass
    private static final Pattern MULTI_STATEMENT_PATTERN = Pattern.compile(";\\s*\\S+");

    public ValidationResult validateAndSanitize(String rawSql) {
        if (rawSql == null || rawSql.trim().isEmpty()) {
            return ValidationResult.reject("SQL query cannot be empty.");
        }

        String sql = rawSql.trim();

        // 1. AST Parsing and Multi-Statement Check
        Statements statements;
        try {
            statements = CCJSqlParserUtil.parseStatements(sql);
        } catch (JSQLParserException e) {
            return ValidationResult.reject("Invalid SQL syntax: " + e.getMessage());
        }

        if (statements.getStatements().size() != 1) {
            return ValidationResult.reject("Multiple SQL statements detected. Exactly one query is permitted.");
        }

        // Secondary check for semicolon chaining
        if (MULTI_STATEMENT_PATTERN.matcher(sql).find()) {
            return ValidationResult.reject("Multiple SQL statements or trailing commands are forbidden.");
        }

        Statement stmt = statements.getStatements().get(0);

        // 2. Enforce SELECT Statement Only
        if (!(stmt instanceof Select)) {
            return ValidationResult.reject("Non-SELECT statement rejected. Only read-only SELECT queries are permitted.");
        }

        Select select = (Select) stmt;

        // 3. Inspect Tables (Disallow system tables & unapproved relations)
        TablesNamesFinder tablesNamesFinder = new TablesNamesFinder();
        List<String> tableNames = tablesNamesFinder.getTableList((Statement) select);

        for (String rawTableName : tableNames) {
            String cleanTable = rawTableName.replace("\"", "").toLowerCase(Locale.ROOT);
            
            // Check for system catalog access
            if (cleanTable.startsWith("pg_") || cleanTable.startsWith("information_schema.")) {
                return ValidationResult.reject("Access to system catalog table '" + rawTableName + "' is strictly forbidden.");
            }

            // Remove schema qualifier if present (e.g. public.v_users -> v_users)
            if (cleanTable.contains(".")) {
                cleanTable = cleanTable.substring(cleanTable.lastIndexOf('.') + 1);
            }

            // Skip CTE names defined in WITH clause
            final String finalTable = cleanTable;
            if (select.getWithItemsList() != null) {
                boolean isCteName = select.getWithItemsList().stream()
                        .anyMatch(w -> w.getAlias() != null && w.getAlias().getName().equalsIgnoreCase(finalTable));
                if (isCteName) {
                    continue;
                }
            }

            if (!ALLOWED_TABLES.contains(cleanTable)) {
                return ValidationResult.reject("Table or view '" + rawTableName + "' is not permitted.");
            }
        }

        // 4. Inspect Columns, Functions, and Wildcards across the AST (including CTEs)
        try {
            inspectSelect(select);
        } catch (SecurityException se) {
            return ValidationResult.reject(se.getMessage());
        }

        // 5. Enforce LIMIT (Inject LIMIT 1000 if absent, clamp if > 1000)
        enforceLimit(select);

        return ValidationResult.accept(select.toString());
    }

    private void inspectSelect(Select select) {
        if (select == null) return;

        // Inspect Common Table Expressions (WITH clauses / CTEs)
        if (select.getWithItemsList() != null) {
            for (WithItem withItem : select.getWithItemsList()) {
                if (withItem.getSelect() != null) {
                    inspectSelect(withItem.getSelect());
                }
            }
        }

        if (select instanceof PlainSelect) {
            inspectPlainSelect((PlainSelect) select);
        } else if (select instanceof ParenthesedSelect) {
            inspectSelect(((ParenthesedSelect) select).getSelect());
        } else if (select instanceof SetOperationList) {
            SetOperationList setOp = (SetOperationList) select;
            for (Select subSelect : setOp.getSelects()) {
                inspectSelect(subSelect);
            }
        }
    }

    private void inspectPlainSelect(PlainSelect plainSelect) {
        // Check Select Items (Wildcard & Column references)
        if (plainSelect.getSelectItems() != null) {
            for (SelectItem item : plainSelect.getSelectItems()) {
                String itemStr = item.toString().trim();
                
                // Block SELECT * on base users table
                if (itemStr.equals("*") || itemStr.endsWith(".*")) {
                    FromItem from = plainSelect.getFromItem();
                    if (from instanceof Table) {
                        String tName = ((Table) from).getName().toLowerCase(Locale.ROOT);
                        if (tName.equals("users")) {
                            throw new SecurityException("Wildcard SELECT (*) is prohibited on base 'users' table due to PII. Please select explicit columns or use the 'v_users' view.");
                        }
                    }
                }

                // Check expression in SelectItem
                inspectExpression(item.getExpression());
            }
        }

        // Check WHERE clause
        if (plainSelect.getWhere() != null) {
            inspectExpression(plainSelect.getWhere());
        }

        // Check HAVING clause
        if (plainSelect.getHaving() != null) {
            inspectExpression(plainSelect.getHaving());
        }

        // Check Joins
        if (plainSelect.getJoins() != null) {
            for (Join join : plainSelect.getJoins()) {
                if (join.getOnExpression() != null) {
                    inspectExpression(join.getOnExpression());
                }
            }
        }

        // Check ORDER BY
        if (plainSelect.getOrderByElements() != null) {
            for (OrderByElement ob : plainSelect.getOrderByElements()) {
                inspectExpression(ob.getExpression());
            }
        }

        // Check GROUP BY
        if (plainSelect.getGroupBy() != null && plainSelect.getGroupBy().getGroupByExpressionList() != null) {
            for (Object obj : plainSelect.getGroupBy().getGroupByExpressionList()) {
                if (obj instanceof Expression expr) {
                    inspectExpression(expr);
                }
            }
        }
    }

    private void inspectExpression(Expression expression) {
        if (expression == null) return;

        // Check Column References
        if (expression instanceof Column col) {
            String colName = col.getColumnName().replace("\"", "").toLowerCase(Locale.ROOT);
            if (BLOCKED_COLUMNS.contains(colName)) {
                throw new SecurityException("Column '" + col.getColumnName() + "' is blocked for privacy and compliance reasons.");
            }
        }

        // Check Dangerous Functions (e.g. pg_sleep)
        if (expression instanceof Function func) {
            String funcName = func.getName().toLowerCase(Locale.ROOT);
            if (DANGEROUS_FUNCTIONS.contains(funcName)) {
                throw new SecurityException("Execution of dangerous function '" + func.getName() + "' is blocked.");
            }
            if (func.getParameters() != null) {
                for (Object param : func.getParameters()) {
                    if (param instanceof Expression expr) {
                        inspectExpression(expr);
                    }
                }
            }
        }

        // Check Subqueries (ParenthesedSelect or Select)
        if (expression instanceof ParenthesedSelect ps) {
            inspectSelect(ps.getSelect());
        } else if (expression instanceof Select s) {
            inspectSelect(s);
        }

        // Also check if expression string representation contains blocked tokens
        String exprStr = expression.toString().toLowerCase(Locale.ROOT);
        for (String blockedCol : BLOCKED_COLUMNS) {
            if (exprStr.matches(".*\\b" + blockedCol + "\\b.*")) {
                throw new SecurityException("Blocked identifier '" + blockedCol + "' detected in query expression.");
            }
        }
    }

    private void enforceLimit(Select select) {
        if (select instanceof PlainSelect plainSelect) {
            Limit limit = plainSelect.getLimit();
            if (limit == null) {
                Limit newLimit = new Limit();
                newLimit.setRowCount(new LongValue(maxRowLimit));
                plainSelect.setLimit(newLimit);
            } else if (limit.getRowCount() instanceof LongValue currentVal) {
                if (currentVal.getValue() > maxRowLimit) {
                    limit.setRowCount(new LongValue(maxRowLimit));
                }
            }
        }
    }
}
