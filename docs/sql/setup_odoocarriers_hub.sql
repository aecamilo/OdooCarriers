-- OdooCarriers Hub Gateway — base de validação (servidor de testes Hetzner)
-- Executar como administrador MySQL no servidor (ex.: sudo mysql < setup_odoocarriers_hub.sql)
-- A password do utilizador deve ser definida aqui ou via ALTER USER após import.

CREATE DATABASE IF NOT EXISTS odoocarriers_hub
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Apenas ligações a partir do próprio servidor (gateway + túnel SSH na máquina de dev).
CREATE USER IF NOT EXISTS 'odoocarriers_hub'@'localhost'
  IDENTIFIED BY 'SUBSTITUIR_PASSWORD_FORTE';

GRANT ALL PRIVILEGES ON odoocarriers_hub.* TO 'odoocarriers_hub'@'localhost';
FLUSH PRIVILEGES;
