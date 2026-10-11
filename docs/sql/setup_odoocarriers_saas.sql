-- Base OdooCarriers Hub Gateway — utilizador saas (servidor de testes)
-- Executar como admin: sudo mysql < setup_odoocarriers_saas.sql

CREATE DATABASE IF NOT EXISTS odoocarriers
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON odoocarriers.* TO 'saas'@'%';
FLUSH PRIVILEGES;
