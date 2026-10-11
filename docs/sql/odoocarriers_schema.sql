-- OdooCarriers Hub Gateway — schema (greenfield)
-- Prerequisite: database odoocarriers + user saas (setup_odoocarriers_saas.sql)
-- Apply: mysql -u saas -p odoocarriers < odoocarriers_schema.sql

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS accounts (
    id                      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    status                  ENUM('active', 'suspended') NOT NULL DEFAULT 'active',
    contact_email           VARCHAR(255)    NULL,
    iap_account_token_hash  BINARY(32)      NULL,
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uq_accounts_iap_token_hash (iap_account_token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS api_token_hashes (
    account_id              BIGINT UNSIGNED NOT NULL,
    token_hash              BINARY(32)      NOT NULL,
    token_hash_version      TINYINT UNSIGNED NOT NULL DEFAULT 1,
    rotated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (account_id),
    UNIQUE KEY uq_api_token_hash (token_hash),
    CONSTRAINT fk_api_token_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subscriptions (
    account_id              BIGINT UNSIGNED NOT NULL,
    plan_code               ENUM('free', 'starter', 'pro', 'enterprise') NOT NULL DEFAULT 'free',
    status                  ENUM('active', 'past_due', 'canceled', 'trialing') NOT NULL DEFAULT 'active',
    usage_yyyymm            CHAR(6)         NOT NULL,
    labels_used             INT UNSIGNED    NOT NULL DEFAULT 0,
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (account_id),
    CONSTRAINT fk_subscription_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hmac_nonces (
    nonce                   VARCHAR(64)     NOT NULL,
    account_id              BIGINT UNSIGNED NOT NULL,
    expires_at              TIMESTAMP(3)    NOT NULL,
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (nonce),
    KEY idx_hmac_nonces_expires (expires_at),
    CONSTRAINT fk_hmac_nonce_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rate_limit_windows (
    account_id              BIGINT UNSIGNED NOT NULL,
    window_key              VARCHAR(20)     NOT NULL,
    request_count           INT UNSIGNED    NOT NULL DEFAULT 0,
    burst_count             INT UNSIGNED    NOT NULL DEFAULT 0,
    last_request_at         TIMESTAMP(3)    NULL,
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (account_id, window_key),
    CONSTRAINT fk_rate_limit_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS shipment_logs (
    id                      CHAR(36)        NOT NULL,
    account_id              BIGINT UNSIGNED NOT NULL,
    usage_yyyymm            CHAR(6)         NOT NULL,
    operation               ENUM('quote_shipment', 'create_shipment') NOT NULL,
    order_reference         VARCHAR(64)     NOT NULL,
    idempotency_key         VARCHAR(64)     NULL,
    carrier_code            VARCHAR(32)     NOT NULL,
    carrier_service         VARCHAR(32)     NOT NULL,
    tracking_number         VARCHAR(128)    NULL,
    status                  ENUM('success', 'error') NOT NULL,
    http_status_code        SMALLINT UNSIGNED NOT NULL,
    error_code              VARCHAR(64)     NULL,
    parcels_count           INT UNSIGNED    NOT NULL DEFAULT 1,
    total_weight_kg         DECIMAL(8, 2)   NOT NULL DEFAULT 0,
    is_overage              TINYINT(1)      NOT NULL DEFAULT 0,
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uq_shipment_idempotency (account_id, idempotency_key),
    KEY idx_sl_quota (account_id, usage_yyyymm, operation, status),
    KEY idx_sl_account_created (account_id, created_at),
    CONSTRAINT fk_sl_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS iap_transactions (
    id                      CHAR(36)        NOT NULL,
    account_id              BIGINT UNSIGNED NOT NULL,
    iap_transaction_id      VARCHAR(128)    NOT NULL,
    credit_amount           DECIMAL(10, 2)  NOT NULL DEFAULT 1,
    status                  ENUM('authorized', 'captured', 'cancelled') NOT NULL,
    idempotency_key         VARCHAR(128)    NULL,
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uq_iap_tx_external (iap_transaction_id),
    UNIQUE KEY uq_iap_idempotency (account_id, idempotency_key),
    CONSTRAINT fk_iap_tx_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS iap_credit_ledger (
    id                      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    account_id              BIGINT UNSIGNED NOT NULL,
    delta_credits           DECIMAL(10, 2)  NOT NULL,
    reason                  VARCHAR(64)     NOT NULL,
    reference_id            VARCHAR(128)    NULL,
    created_at              TIMESTAMP(3)    NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_iap_ledger_account (account_id, created_at),
    CONSTRAINT fk_iap_ledger_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
