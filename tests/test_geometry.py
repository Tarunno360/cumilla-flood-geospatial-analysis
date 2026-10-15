"""
Unit Tests for Spatial Geometry Operations and CRS Transformations.
"""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from src.validate import validate_and_fix_geometries


def test_validate_and_fix_invalid_geometry():
    """Verify that self-intersecting 'bowtie' polygons are repaired to valid multipolygons/polygons."""
    # Classic self-intersecting bowtie polygon
    bowtie = Polygon([(0, 0), (0, 2), (2, 0), (2, 2), (0, 0)])
    assert not bowtie.is_valid, "Test polygon must start as invalid"

    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[bowtie], crs="EPSG:32646")
    repaired_gdf = validate_and_fix_geometries(gdf, "test_bowtie")

    assert len(repaired_gdf) == 1
    assert repaired_gdf.geometry.iloc[0].is_valid, "Repaired geometry must be valid"
    assert repaired_gdf.geometry.iloc[0].area > 0, "Repaired geometry must have positive area"


def test_remove_null_and_empty_geometries():
    """Verify that null and empty geometries are cleanly removed."""
    valid_poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    empty_poly = Polygon()
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[valid_poly, empty_poly, None],
        crs="EPSG:32646",
    )

    cleaned_gdf = validate_and_fix_geometries(gdf, "test_null_filtering")
    assert len(cleaned_gdf) == 1
    assert cleaned_gdf.iloc[0]["id"] == 1


def test_crs_reprojection_consistency():
    """Verify reprojection between WGS84 (EPSG:4326) and UTM Zone 46N (EPSG:32646)."""
    # Cumilla District Center coordinates ~ (23.46°N, 91.18°E)
    pt_wgs84 = Point(91.18, 23.46)
    gdf_wgs84 = gpd.GeoDataFrame({"name": ["Cumilla Center"]}, geometry=[pt_wgs84], crs="EPSG:4326")

    gdf_utm = gdf_wgs84.to_crs("EPSG:32646")
    pt_utm = gdf_utm.geometry.iloc[0]

    # Verify UTM coordinates fall within reasonable bounds for UTM Zone 46N in Bangladesh
    # Easting for Cumilla (91.18°E, west of central meridian 93°E) is ~314,000 meters; Northing ~ 2,595,000 meters
    assert 200_000 < pt_utm.x < 450_000, f"Unexpected UTM Easting: {pt_utm.x}"
    assert 2_500_000 < pt_utm.y < 2_700_000, f"Unexpected UTM Northing: {pt_utm.y}"

    # Reproject back and check round-trip tolerance (< 1e-5 degrees)
    gdf_roundtrip = gdf_utm.to_crs("EPSG:4326")
    pt_back = gdf_roundtrip.geometry.iloc[0]
    assert np.isclose(pt_back.x, 91.18, atol=1e-5)
    assert np.isclose(pt_back.y, 23.46, atol=1e-5)


def test_spatial_clipping():
    """Verify polygon clipping against a bounding mask."""
    # Outer district: 10km x 10km (0 to 10000)
    district_poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000), (0, 0)])
    district_gdf = gpd.GeoDataFrame({"name": ["Test District"]}, geometry=[district_poly], crs="EPSG:32646")

    # Flood feature crossing boundary: from 5000 to 15000 in X, 2000 to 4000 in Y
    # Part inside district is 5000 wide x 2000 tall = 10,000,000 m² = 10 km²
    flood_poly = Polygon([(5000, 2000), (15000, 2000), (15000, 4000), (5000, 4000), (5000, 2000)])
    flood_gdf = gpd.GeoDataFrame({"type": ["Flood"]}, geometry=[flood_poly], crs="EPSG:32646")

    clipped_gdf = gpd.clip(flood_gdf, district_gdf)
    assert len(clipped_gdf) == 1
    clipped_area_m2 = clipped_gdf.geometry.iloc[0].area
    assert np.isclose(clipped_area_m2, 10_000_000, atol=1.0), f"Expected 10 km², got {clipped_area_m2/1e6} km²"
