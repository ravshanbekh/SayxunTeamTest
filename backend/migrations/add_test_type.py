"""
Migration: Add test_type column to tests table.
Run this manually against the database.

ALTER TABLE tests ADD COLUMN IF NOT EXISTS test_type VARCHAR(20) DEFAULT 'sertifikat' NOT NULL;
UPDATE tests SET test_type = 'sertifikat' WHERE test_type IS NULL;
"""
