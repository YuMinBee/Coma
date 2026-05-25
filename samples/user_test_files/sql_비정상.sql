CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(30)
);

INSERT INTO users (id, username, password, email, phone)
VALUES (1, 'admin', 'admin1234', 'admin@example.com', '010-9876-5432');

INSERT INTO users (id, username, password, email, phone)
VALUES (2, 'root', 'rootpass123', 'root@example.com', '010-2222-3333');

GRANT ALL PRIVILEGES ON users TO PUBLIC;

CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY,
    service_name VARCHAR(100),
    api_key VARCHAR(255)
);

INSERT INTO api_keys (id, service_name, api_key)
VALUES (1, 'external_service', 'sk-test-abcdef1234567890abcdef123456');

INSERT INTO api_keys (id, service_name, api_key)
VALUES (2, 'billing_worker', 'AKIAIOSFODNN7EXAMPLE');

CREATE TABLE customer_payment_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    card_number VARCHAR(32),
    token VARCHAR(255)
);

INSERT INTO customer_payment_tokens (id, user_id, card_number, token)
VALUES (1, 1, '4111-1111-1111-1111', 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJwYXkiOiIxIn0.sig');

CREATE VIEW public_user_dump AS
SELECT id, username, password, email, phone
FROM users;

CREATE PROCEDURE get_user_by_name(IN input_name VARCHAR(100))
BEGIN
    SET @query = CONCAT(
        'SELECT * FROM users WHERE username = ''',
        input_name,
        ''''
    );

    PREPARE stmt FROM @query;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END;

CREATE PROCEDURE rotate_api_key(IN service VARCHAR(100), IN next_key VARCHAR(255))
BEGIN
    SET @sql = CONCAT(
        'UPDATE api_keys SET api_key = ''',
        next_key,
        ''' WHERE service_name = ''',
        service,
        ''''
    );

    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END;

GRANT SELECT ON public_user_dump TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO PUBLIC;
