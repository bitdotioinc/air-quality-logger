-- Aligns with logged columns in config.yaml and adds server-side timestamps
CREATE TABLE "andrewdoss/air_quality"."pm_measurements" (
    "datetime" timestamp with time zone default (now() at time zone 'utc'),
    "location" text,
    "sensor_id" integer,
    "pm_2_5" real,
    "pm_10" real
)