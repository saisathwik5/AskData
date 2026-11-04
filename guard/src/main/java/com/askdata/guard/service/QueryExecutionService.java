package com.askdata.guard.service;

import com.askdata.guard.model.QueryRequest;
import com.askdata.guard.model.QueryResponse;
import com.askdata.guard.model.ValidationResult;
import com.askdata.guard.repository.AuditLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.ResultSetMetaData;
import java.util.*;

@Service
public class QueryExecutionService {

    private final SqlValidatorService validatorService;
    private final JdbcTemplate jdbcTemplate;
    private final AuditLogRepository auditLogRepository;

    @Value("${guard.statement-timeout-seconds:5}")
    private int statementTimeoutSeconds = 5;

    @Autowired
    public QueryExecutionService(SqlValidatorService validatorService,
                                 JdbcTemplate jdbcTemplate,
                                 AuditLogRepository auditLogRepository) {
        this.validatorService = validatorService;
        this.jdbcTemplate = jdbcTemplate;
        this.auditLogRepository = auditLogRepository;
    }

    public QueryResponse execute(QueryRequest request) {
        String rawSql = request.getSql();
        String userId = request.getUserId();
        String question = request.getQuestion();

        // 1. AST Validation
        ValidationResult valResult = validatorService.validateAndSanitize(rawSql);
        if (!valResult.isValid()) {
            auditLogRepository.logQuery(userId, question, rawSql, false, valResult.getReason(), 0L, 0);
            return QueryResponse.blocked("SECURITY_VIOLATION", valResult.getReason(), rawSql);
        }

        String sanitizedSql = valResult.getSanitizedSql();
        long startTime = System.currentTimeMillis();

        try {
            // 2. Set timeout on connection/statement
            jdbcTemplate.setQueryTimeout(statementTimeoutSeconds);

            // 3. Execute and map results
            List<String> columnNames = new ArrayList<>();
            List<Map<String, Object>> rows = jdbcTemplate.query(sanitizedSql, rs -> {
                ResultSetMetaData meta = rs.getMetaData();
                int colCount = meta.getColumnCount();
                for (int i = 1; i <= colCount; i++) {
                    columnNames.add(meta.getColumnLabel(i));
                }

                List<Map<String, Object>> resultList = new ArrayList<>();
                while (rs.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int i = 1; i <= colCount; i++) {
                        row.put(meta.getColumnLabel(i), rs.getObject(i));
                    }
                    resultList.add(row);
                }
                return resultList;
            });

            long durationMs = System.currentTimeMillis() - startTime;
            int rowCount = (rows != null) ? rows.size() : 0;

            // 4. Record successful audit log
            auditLogRepository.logQuery(userId, question, sanitizedSql, true, null, durationMs, rowCount);

            return QueryResponse.ok(columnNames, rows, rowCount, durationMs, sanitizedSql);

        } catch (Exception e) {
            long durationMs = System.currentTimeMillis() - startTime;
            String errMsg = "Execution error: " + e.getMessage();
            auditLogRepository.logQuery(userId, question, sanitizedSql, false, errMsg, durationMs, 0);
            return QueryResponse.blocked("EXECUTION_FAILED", errMsg, sanitizedSql);
        }
    }
}
