-- Buoy roster (PM Plan 3.4). Coordinates are fictional points in open water off the US West Coast.
-- Safe to re-run: existing buoys are left alone.
INSERT OR IGNORE INTO buoys (buoy_id, name, location_lat, location_lng) VALUES
    ('BUOY-01', 'Monterey Offshore',         36.80, -122.50),
    ('BUOY-02', 'Point Conception Offshore', 34.30, -120.90),
    ('BUOY-03', 'San Diego Offshore',        32.90, -117.90),
    ('BUOY-04', 'Cape Mendocino Offshore',   40.40, -124.60),
    ('BUOY-05', 'Point Reyes Offshore',      38.00, -123.50);
