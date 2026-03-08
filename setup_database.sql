-- FarmGuard Database Setup Script
-- Run this in PostgreSQL to create the database

-- Create database
CREATE DATABASE farmguard;

-- Connect to the database
\c farmguard;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table is created automatically by SQLAlchemy
-- But here are the table structures for reference:

-- Tables will be created automatically when you run the Flask app
-- The following is just for documentation:

/*
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE animals (
    id SERIAL PRIMARY KEY,
    tag_number VARCHAR(50) UNIQUE NOT NULL,
    species VARCHAR(50) NOT NULL,
    farmer_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drugs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    withdrawal_period_days INTEGER NOT NULL,
    max_dosage FLOAT,
    unit VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE amu_entries (
    id SERIAL PRIMARY KEY,
    entry_id VARCHAR(50) UNIQUE NOT NULL,
    farmer_id INTEGER REFERENCES users(id),
    animal_id INTEGER REFERENCES animals(id),
    drug_id INTEGER REFERENCES drugs(id),
    dosage FLOAT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    treatment_date DATE NOT NULL,
    withdrawal_end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    vet_id INTEGER REFERENCES users(id),
    vet_notes TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    related_entry_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    alert_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_amu_entries_farmer ON amu_entries(farmer_id);
CREATE INDEX idx_amu_entries_status ON amu_entries(status);
CREATE INDEX idx_amu_entries_withdrawal ON amu_entries(withdrawal_end_date);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_alerts_user ON alerts(user_id);
*/

-- Grant privileges (adjust username as needed)
GRANT ALL PRIVILEGES ON DATABASE farmguard TO your_username;