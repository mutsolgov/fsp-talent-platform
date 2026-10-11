-- Initialization script for Keycloak PostgreSQL schema isolation
CREATE SCHEMA IF NOT EXISTS keycloak;
GRANT ALL ON SCHEMA keycloak TO fsp_user;
