package com.askdata.guard;

import com.askdata.guard.model.ValidationResult;
import com.askdata.guard.service.SqlValidatorService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.*;

public class SqlValidatorAttackTests {

    private SqlValidatorService validatorService;

    @BeforeEach
    void setUp() {
        validatorService = new SqlValidatorService();
    }

    @ParameterizedTest(name = "Attack Query [{index}]: {0}")
    @ValueSource(strings = {
            // 1-3. Multi-statement chaining & comment evasion
            "SELECT 1; DROP TABLE users;",
            "SELECT 1 --\n; DROP TABLE users;",
            "SELECT 1 /* comment */ ; DROP TABLE payments;",

            // 4-10. DDL, DML & DCL attacks
            "DROP TABLE payments;",
            "DELETE FROM users WHERE 1=1;",
            "UPDATE subscriptions SET status = 'active';",
            "INSERT INTO payments (id, amount) VALUES ('hack', 0.0);",
            "TRUNCATE TABLE events;",
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN;",
            "GRANT ALL PRIVILEGES ON ALL TABLES TO public;",

            // 11-15. Blocked column direct access & mixed case
            "SELECT email FROM users;",
            "SELECT full_name FROM users;",
            "SELECT u.email FROM users u;",
            "SELECT u.full_name FROM users u;",
            "sElEcT eMaIl fRoM users;",

            // 16-17. Wildcard on base PII tables
            "SELECT * FROM users;",
            "SELECT u.* FROM users u;",

            // 18-20. Subqueries reaching blocked columns
            "SELECT (SELECT email FROM users LIMIT 1) FROM payments;",
            "WITH cte AS (SELECT email FROM users) SELECT * FROM cte;",
            "SELECT 1 FROM v_payments WHERE user_id IN (SELECT id FROM users WHERE email = 'admin@corp.com');",

            // 21-23. Filtering, ordering and grouping by blocked columns
            "SELECT id FROM users WHERE email = 'test@example.com';",
            "SELECT country FROM users ORDER BY email;",
            "SELECT country FROM users GROUP BY email;",

            // 24-26. Dangerous functions (DOS & file-read)
            "SELECT pg_sleep(100);",
            "SELECT pg_sleep(10) AS nap FROM v_users;",
            "SELECT pg_read_file('/etc/passwd');",

            // 27-30. System tables and catalogs probing
            "SELECT * FROM pg_catalog.pg_tables;",
            "SELECT * FROM information_schema.tables;",
            "SELECT usename, passwd FROM pg_shadow;",
            "SELECT * FROM pg_user;",

            // 31-32. UNION-based extraction
            "SELECT country FROM v_users UNION SELECT email FROM users;",
            "SELECT plan FROM v_subscriptions UNION ALL SELECT full_name FROM users;",

            // 33-35. Process termination, unknown tables & non-select wrappers
            "SELECT pg_terminate_backend(1234) FROM v_events;",
            "SELECT * FROM secret_corporate_data;",
            "EXPLAIN DELETE FROM users;"
    })
    @DisplayName("Verify that all 35 attack vectors are strictly blocked by AST analysis")
    void shouldBlockAllAttackQueries(String attackSql) {
        ValidationResult result = validatorService.validateAndSanitize(attackSql);
        assertFalse(result.isValid(), "Attack should have been blocked: " + attackSql);
        assertNotNull(result.getReason(), "A clear rejection reason must be returned for: " + attackSql);
        System.out.println("[BLOCKED] " + attackSql + " -> Reason: " + result.getReason());
    }

    @Test
    @DisplayName("Valid query on safe view should be accepted and have LIMIT 1000 injected")
    void shouldAcceptValidQueryAndInjectLimit() {
        String validSql = "SELECT country, count(*) FROM v_users GROUP BY country;";
        ValidationResult result = validatorService.validateAndSanitize(validSql);

        assertTrue(result.isValid(), "Valid query on v_users must pass");
        assertNotNull(result.getSanitizedSql());
        assertTrue(result.getSanitizedSql().toUpperCase().contains("LIMIT 1000"), 
                "LIMIT 1000 must be appended if no limit was provided");
    }

    @Test
    @DisplayName("Query with excessive LIMIT should be clamped to 1000")
    void shouldClampExcessiveLimit() {
        String queryWithHugeLimit = "SELECT id FROM v_payments LIMIT 500000;";
        ValidationResult result = validatorService.validateAndSanitize(queryWithHugeLimit);

        assertTrue(result.isValid());
        assertTrue(result.getSanitizedSql().toUpperCase().contains("LIMIT 1000"), 
                "Limit exceeding 1000 must be clamped to 1000");
    }

    @Test
    @DisplayName("Query with reasonable LIMIT under 1000 should be preserved")
    void shouldPreserveReasonableLimit() {
        String queryWithSmallLimit = "SELECT id FROM v_payments LIMIT 25;";
        ValidationResult result = validatorService.validateAndSanitize(queryWithSmallLimit);

        assertTrue(result.isValid());
        assertTrue(result.getSanitizedSql().toUpperCase().contains("LIMIT 25"), 
                "Existing limit under 1000 should be preserved");
    }
}
