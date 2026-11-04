package com.askdata.guard.repository;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;

@Repository
public class AuditLogRepository {

    private final JdbcTemplate jdbcTemplate;

    @Autowired
    public AuditLogRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void logQuery(String userId, String question, String sql, boolean allowed, 
                         String rejectionReason, Long executionTimeMs, Integer rowCount) {
        String insertSql = """
            INSERT INTO query_audit_logs 
            (id, user_id, question, sql_query, allowed, rejection_reason, execution_time_ms, row_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """;

        try {
            jdbcTemplate.update(
                insertSql,
                UUID.randomUUID().toString(),
                userId != null ? userId : "anonymous",
                question,
                sql,
                allowed,
                rejectionReason,
                executionTimeMs,
                rowCount,
                Timestamp.from(Instant.now())
            );
        } catch (Exception e) {
            // Log to console if audit table insertion fails so service does not crash
            System.err.println("[AuditLogRepository] Warning: failed to write audit log: " + e.getMessage());
        }
    }
}
