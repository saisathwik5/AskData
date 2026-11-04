# --- Build Stage ---
FROM maven:3.9-eclipse-temurin-17-alpine AS builder
WORKDIR /build

# Cache dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Compile and package jar
COPY src ./src
RUN mvn clean package -DskipTests -B

# --- Production Runtime Stage ---
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Non-root security user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

COPY --from=builder /build/target/guard-1.0.0.jar /app/guard.jar

EXPOSE 8081

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8081/health || exit 1

ENTRYPOINT ["java", "-Xmx512m", "-Xms256m", "-jar", "/app/guard.jar"]
