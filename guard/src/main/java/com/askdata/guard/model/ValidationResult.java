package com.askdata.guard.model;

public class ValidationResult {
    private final boolean valid;
    private final String reason;
    private final String sanitizedSql;

    private ValidationResult(boolean valid, String reason, String sanitizedSql) {
        this.valid = valid;
        this.reason = reason;
        this.sanitizedSql = sanitizedSql;
    }

    public static ValidationResult accept(String sanitizedSql) {
        return new ValidationResult(true, null, sanitizedSql);
    }

    public static ValidationResult reject(String reason) {
        return new ValidationResult(false, reason, null);
    }

    public boolean isValid() {
        return valid;
    }

    public String getReason() {
        return reason;
    }

    public String getSanitizedSql() {
        return sanitizedSql;
    }
}
