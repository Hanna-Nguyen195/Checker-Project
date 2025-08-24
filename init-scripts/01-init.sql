-- Create database if it doesn't exist
SELECT 'CREATE DATABASE plagiarism_detector'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'plagiarism_detector')\gexec

-- Connect to the database
\c plagiarism_detector;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";