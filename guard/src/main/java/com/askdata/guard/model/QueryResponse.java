package com.askdata.guard.model;

import java.util.List;
import java.util.Map;

public class QueryResponse {
    private boolean success;
    private String message;
    private String errorCode;
    private List<String> columns;
    private List<Map<String, Object>> rows;
    private int rowCount;
    private long executionTimeMs;
    private String executedSql;

    public QueryResponse() {}

    public static QueryResponse ok(List<String> columns, List<Map<String, Object>> rows, int rowCount, long executionTimeMs, String executedSql) {
        QueryResponse res = new QueryResponse();
        res.success = true;
        res.message = "Query executed successfully";
        res.columns = columns;
        res.rows = rows;
        res.rowCount = rowCount;
        res.executionTimeMs = executionTimeMs;
        res.executedSql = executedSql;
        return res;
    }

    public static QueryResponse blocked(String errorCode, String message, String originalSql) {
        QueryResponse res = new QueryResponse();
        res.success = false;
        res.errorCode = errorCode;
        res.message = message;
        res.executedSql = originalSql;
        return res;
    }

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public void setErrorCode(String errorCode) {
        this.errorCode = errorCode;
    }

    public List<String> getColumns() {
        return columns;
    }

    public void setColumns(List<String> columns) {
        this.columns = columns;
    }

    public List<Map<String, Object>> getRows() {
        return rows;
    }

    public void setRows(List<Map<String, Object>> rows) {
        this.rows = rows;
    }

    public int getRowCount() {
        return rowCount;
    }

    public void setRowCount(int rowCount) {
        this.rowCount = rowCount;
    }

    public long getExecutionTimeMs() {
        return executionTimeMs;
    }

    public void setExecutionTimeMs(long executionTimeMs) {
        this.executionTimeMs = executionTimeMs;
    }

    public String getExecutedSql() {
        return executedSql;
    }

    public void setExecutedSql(String executedSql) {
        this.executedSql = executedSql;
    }
}
