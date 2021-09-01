-- Aligns with logged columns in config.yaml
-- Update the first line with your table name 
CREATE TABLE "air_quality_log_test/air_quality"."pm_measurements" (
    "datetime" timestamp with time zone,
    "location" text,
    "sensor_id" integer,
    "pm_2_5" real,
    "pm_10" real
)