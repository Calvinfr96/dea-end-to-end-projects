-- Counts the total number of rows, as well as the total number of non-null values for certain rows which tend to be null.
-- Used to track whether the rows can be used in analysis.
SELECT 
  COUNT(1) as total_rows,
  COUNT(location_type) as populated_locations,
  COUNT(utm_source) as populated_utm_sources,
  COUNT(utm_campaign) as populated_utm_campaigns,
  COUNT(utm_medium) as populated_utm_mediums
FROM workspace.default.calendly_silver
