-- init.sql
CREATE TABLE IF NOT EXISTS sensors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    unit VARCHAR(10) NOT NULL,
    value FLOAT,
    status VARCHAR(20) DEFAULT 'active'
);