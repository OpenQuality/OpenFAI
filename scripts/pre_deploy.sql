-- Pre-deployment SQL script
-- Execute this BEFORE deployment to fix NULL values in parts table
-- This prevents deployment platform's sync mechanism from failing

-- Update all NULL values to default values
UPDATE parts SET cad_file_original_name = '' WHERE cad_file_original_name IS NULL;
UPDATE parts SET drawing_file_original_name = '' WHERE drawing_file_original_name IS NULL;
UPDATE parts SET pdf_file_original_name = '' WHERE pdf_file_original_name IS NULL;
UPDATE parts SET model_3d_file_original_name = '' WHERE model_3d_file_original_name IS NULL;
UPDATE parts SET model_3d_file_type = '' WHERE model_3d_file_type IS NULL;
UPDATE parts SET cad_file_size = 0 WHERE cad_file_size IS NULL;
UPDATE parts SET drawing_file_size = 0 WHERE drawing_file_size IS NULL;
UPDATE parts SET pdf_file_size = 0 WHERE pdf_file_size IS NULL;
UPDATE parts SET model_3d_file_size = 0 WHERE model_3d_file_size IS NULL;

-- Remove any NOT NULL constraints that might exist
ALTER TABLE parts ALTER COLUMN cad_file_original_name DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN drawing_file_original_name DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN pdf_file_original_name DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN model_3d_file_original_name DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN cad_file_size DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN drawing_file_size DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN pdf_file_size DROP NOT NULL;
ALTER TABLE parts ALTER COLUMN model_3d_file_size DROP NOT NULL;
