-- Migration 002: Odoo database UUID + DPD connections (PROPOSTA §2)
-- Apply once after odoocarriers_schema.sql (scripts/apply-odoocarriers-db.sh or mysql client)

SET NAMES utf8mb4;

ALTER TABLE accounts
    ADD COLUMN odoo_database_uuid CHAR(36) NULL;

ALTER TABLE accounts
    ADD UNIQUE KEY uq_accounts_odoo_database_uuid (odoo_database_uuid);

CREATE TABLE IF NOT EXISTS connections (
    id                      CHAR(36)        NOT NULL,
    account_id              BIGINT UNSIGNED NOT NULL,
    external_ref            VARCHAR(64)     NOT NULL,
    company_name            VARCHAR(255)    NULL,
    warehouse_ref           VARCHAR(64)     NULL,
    country_code            CHAR(2)         NOT NULL,
    environment             ENUM('stage', 'live') NOT NULL DEFAULT 'stage',
    carrier_code            VARCHAR(16)     NOT NULL DEFAULT 'dpd',
    status                  ENUM('active', 'suspended') NOT NULL DEFAULT 'active',
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uq_connection_account_ref (account_id, external_ref),
    KEY idx_connections_account (account_id, country_code, environment),
    CONSTRAINT fk_connections_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS connection_secrets (
    connection_id           CHAR(36)        NOT NULL,
    secrets_ciphertext      MEDIUMBLOB      NOT NULL,
    secrets_key_version     TINYINT UNSIGNED NOT NULL DEFAULT 1,
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (connection_id),
    CONSTRAINT fk_connection_secrets_connection FOREIGN KEY (connection_id)
        REFERENCES connections (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
