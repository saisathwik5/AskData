package com.askdata.guard.model;

public class QueryRequest {
    private String sql;
    private String userId;
    private String question;

    public QueryRequest() {}

    public QueryRequest(String sql, String userId, String question) {
        this.sql = sql;
        this.userId = userId;
        this.question = question;
    }

    public String getSql() {
        return sql;
    }

    public void setSql(String sql) {
        this.sql = sql;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }
}
