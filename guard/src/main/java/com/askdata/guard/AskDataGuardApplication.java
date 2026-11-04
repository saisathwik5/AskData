package com.askdata.guard;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;

@SpringBootApplication
public class AskDataGuardApplication {

    public static void main(String[] args) {
        loadDotEnv();
        SpringApplication.run(AskDataGuardApplication.class, args);
    }

    private static void loadDotEnv() {
        File[] envFiles = {
            new File(".env"),
            new File("../.env"),
            new File("../../.env")
        };

        for (File f : envFiles) {
            if (f.exists()) {
                try (BufferedReader reader = new BufferedReader(new FileReader(f))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        line = line.trim();
                        if (line.isEmpty() || line.startsWith("#") || !line.contains("=")) {
                            continue;
                        }
                        int eqIdx = line.indexOf('=');
                        String key = line.substring(0, eqIdx).trim();
                        String val = line.substring(eqIdx + 1).trim();
                        if ((val.startsWith("\"") && val.endsWith("\"")) || (val.startsWith("'") && val.endsWith("'"))) {
                            val = val.substring(1, val.length() - 1);
                        }
                        if (System.getProperty(key) == null && System.getenv(key) == null) {
                            System.setProperty(key, val);
                        }
                    }
                    System.out.println("[AskDataGuardApplication] Successfully loaded secrets from: " + f.getCanonicalPath());
                } catch (Exception e) {
                    System.err.println("[AskDataGuardApplication] Warning reading .env: " + e.getMessage());
                }
                break;
            }
        }
    }
}
