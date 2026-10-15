"""
Unit Tests for Spatial Exposure Metrics, Area Computations, and Distance Analysis.
"""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from src.spatial_analysis import compute_flood_and_exposure_metrics


@pytest.fixture
def sample_test_layers():
    """Create a controlled synthetic environment for unit testing metric formulas."""
    crs = "EPSG:32646"

    # District boundary: 10 km x 10 km square = 100 km²
    boundary_poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000), (0, 0)])
    boundary_gdf = gpd.GeoDataFrame({"shapeName": ["Test District"]}, geometry=[boundary_poly], crs=crs)

    # Flood extent: 4 km x 5 km = 20 km² inside the district
    # Located from X: 1000 to 5000, Y: 1000 to 6000
    flood_poly = Polygon([(1000, 1000), (5000, 1000), (5000, 6000), (1000, 6000), (1000, 1000)])
    flood_gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[flood_poly], crs=crs)

    # 4 synthetic healthcare facilities with known geometric positions:
    # 1. Point at (2000, 2000) -> INSIDE flood polygon (dist = 0.0)
    # 2. Point at (5300, 2000) -> 300m East of boundary X=5000 (dist = 300.0 m) -> 'Within 500m'
    # 3. Point at (5800, 2000) -> 800m East of boundary X=5000 (dist = 800.0 m) -> '500m - 1km'
    # 4. Point at (8000, 2000) -> 3000m East of boundary X=5000 (dist = 3000.0 m) -> '2.5km - 5km'
    points = [
        Point(2000, 2000),
        Point(5300, 2000),
        Point(5800, 2000),
        Point(8000, 2000),
    ]
    healthcare_gdf = gpd.GeoDataFrame(
        {
            "osm_id": ["node/1", "node/2", "node/3", "node/4"],
            "name": ["Hospital Inside", "Clinic 300m", "Clinic 800m", "Doctor 3km"],
            "amenity": ["hospital", "clinic", "clinic", "doctors"],
        },
        geometry=points,
        crs=crs,
    )

    mock_config = {
        "project": {
            "study_area": "Test District",
            "event_glide": "TEST2024",
        },
        "crs": {
            "geographic": "EPSG:4326",
            "projected": "EPSG:32646",
        },
        "data_sources": {
            "unosat_flood": {
                "sensor": "Synthetic Test",
                "pre_event_dates": "test",
                "post_event_dates": "test",
                "observation_periods": {
                    "period_1": {
                        "name": "First Satellite Observation Period (18 to 26 August 2024)",
                        "date_range": "18 to 26 August 2024",
                        "shapefile_name": "S1_20240818_20240826_FloodExtent_Bangladesh.shp",
                    },
                    "period_2": {
                        "name": "Second Satellite Observation Period (28 August to 04 September 2024)",
                        "date_range": "28 August to 04 September 2024",
                        "shapefile_name": "S1_20240828_20240904_FloodExtent_Bangladesh.shp",
                    },
                },
            }
        },
    }

    return boundary_gdf, flood_gdf, healthcare_gdf, mock_config


def test_area_calculations(sample_test_layers):
    """Verify that district area and flood extent are accurately converted to km²."""
    boundary_gdf, flood_gdf, healthcare_gdf, config = sample_test_layers
    results_df, summary = compute_flood_and_exposure_metrics(boundary_gdf, flood_gdf, healthcare_gdf, config)

    # 10,000 m * 10,000 m = 100,000,000 m² = 100.0 km²
    assert np.isclose(summary["district_metrics"]["total_area_km2"], 100.0)

    # 4,000 m * 5,000 m = 20,000,000 m² = 20.0 km²
    assert np.isclose(summary["flood_metrics"]["satellite_detected_flood_area_km2"], 20.0)

    # Percentage = 20 / 100 = 20.0%
    assert np.isclose(summary["flood_metrics"]["percentage_of_district_flooded"], 20.0)


def test_distance_and_inundation_exposure(sample_test_layers):
    """Verify point distances to polygon boundaries and proximity bands."""
    boundary_gdf, flood_gdf, healthcare_gdf, config = sample_test_layers
    results_df, summary = compute_flood_and_exposure_metrics(boundary_gdf, flood_gdf, healthcare_gdf, config)

    h1 = results_df.iloc[0]
    assert bool(h1["in_flood_extent"]) is True
    assert np.isclose(h1["distance_to_flood_m"], 0.0)
    assert h1["proximity_band"] == "Inside Flood Extent"

    h2 = results_df.iloc[1]
    assert bool(h2["in_flood_extent"]) is False
    assert np.isclose(h2["distance_to_flood_m"], 300.0)
    assert h2["proximity_band"] == "Within 500m"

    h3 = results_df.iloc[2]
    assert bool(h3["in_flood_extent"]) is False
    assert np.isclose(h3["distance_to_flood_m"], 800.0)
    assert h3["proximity_band"] == "500m - 1km"

    h4 = results_df.iloc[3]
    assert bool(h4["in_flood_extent"]) is False
    assert np.isclose(h4["distance_to_flood_m"], 3000.0)
    assert h4["proximity_band"] == "2.5km - 5km"

    # Check aggregate counts
    h_metrics = summary["healthcare_facility_metrics"]
    assert h_metrics["total_mapped_facilities"] == 4
    assert h_metrics["facilities_intersecting_flood_extent"] == 1
    assert h_metrics["facilities_within_500m"] == 2  # h1 (0m) and h2 (300m)
    assert h_metrics["facilities_within_1000m"] == 3  # h1, h2, h3


def test_empty_flood_extent_handling(sample_test_layers):
    """Verify robust handling when no flood polygons exist (0 km² inundation)."""
    boundary_gdf, _, healthcare_gdf, config = sample_test_layers
    empty_flood_gdf = gpd.GeoDataFrame({"id": []}, geometry=[], crs="EPSG:32646")

    results_df, summary = compute_flood_and_exposure_metrics(boundary_gdf, empty_flood_gdf, healthcare_gdf, config)

    assert summary["flood_metrics"]["satellite_detected_flood_area_km2"] == 0.0
    assert summary["flood_metrics"]["percentage_of_district_flooded"] == 0.0
    assert summary["healthcare_facility_metrics"]["facilities_intersecting_flood_extent"] == 0


def test_missing_config_raises_error():
    """Verify that attempting to load a non-existent config file raises FileNotFoundError."""
    from pathlib import Path
    from main import load_config

    with pytest.raises(FileNotFoundError):
        load_config(Path("non_existent_config_file.yaml"))


def test_find_cumilla_boundary_alias_not_found(sample_test_layers):
    """Verify that searching for an invalid district alias raises ValueError with informative message."""
    from src.validate import find_cumilla_boundary

    boundary_gdf, _, _, _ = sample_test_layers
    with pytest.raises(ValueError, match="Could not locate Cumilla boundary"):
        find_cumilla_boundary(boundary_gdf, ["NonExistentDistrictName"])


def test_disaggregated_category_grouping(sample_test_layers):
    """Verify that facilities are correctly partitioned into functional groups with separate metrics."""
    boundary_gdf, flood_gdf, healthcare_gdf, config = sample_test_layers
    results_df, summary = compute_flood_and_exposure_metrics(boundary_gdf, flood_gdf, healthcare_gdf, config)

    assert "category_group" in results_df.columns
    groups = results_df["category_group"].tolist()
    # sample_test_layers amenities: hospital, clinic, clinic, doctors
    assert groups[0] == "Hospitals & Clinics"  # hospital
    assert groups[1] == "Hospitals & Clinics"  # clinic
    assert groups[2] == "Hospitals & Clinics"  # clinic
    assert groups[3] == "Other / Unspecified"  # doctors

    disagg = summary["healthcare_facility_metrics"]["disaggregated_by_category_group"]
    assert "Hospitals & Clinics" in disagg
    assert disagg["Hospitals & Clinics"]["total_count"] == 3
    assert disagg["Hospitals & Clinics"]["intersecting_flood_extent"] == 1
    assert disagg["Hospitals & Clinics"]["within_500m"] == 2


def test_temporal_observation_window_documentation(sample_test_layers):
    """Verify that summary statistics clearly differentiate observation period 1 and 2."""
    boundary_gdf, flood_gdf, healthcare_gdf, config = sample_test_layers
    results_df, summary = compute_flood_and_exposure_metrics(boundary_gdf, flood_gdf, healthcare_gdf, config)

    flood_m = summary["flood_metrics"]
    assert "primary_analyzed_window" in flood_m
    assert "18 to 26 August 2024" in flood_m["primary_analyzed_window"]
    assert "observation_period_1" in flood_m
    assert "observation_period_2" in flood_m


def test_multi_period_independent_processing(sample_test_layers):
    """Verify that both observation periods are processed independently without hardcoded values."""
    boundary_gdf, flood_gdf_p1, healthcare_gdf, config = sample_test_layers

    # Create a smaller period 2 flood polygon: 2 km x 5 km = 10 km² (vs 20 km² in p1)
    crs = "EPSG:32646"
    poly_p2 = Polygon([(1000, 1000), (3000, 1000), (3000, 6000), (1000, 6000), (1000, 1000)])
    flood_gdf_p2 = gpd.GeoDataFrame({"id": [2]}, geometry=[poly_p2], crs=crs)

    multi_flood_dict = {
        "period_1": flood_gdf_p1,
        "period_2": flood_gdf_p2,
    }

    results_df, summary = compute_flood_and_exposure_metrics(
        boundary_gdf, multi_flood_dict, healthcare_gdf, config
    )

    assert "temporal_periods" in summary
    assert "period_1" in summary["temporal_periods"]
    assert "period_2" in summary["temporal_periods"]

    p1_m = summary["temporal_periods"]["period_1"]
    p2_m = summary["temporal_periods"]["period_2"]

    # Verify both areas are dynamically computed
    assert np.isclose(p1_m["flood_area_km2"], 20.0)
    assert np.isclose(p2_m["flood_area_km2"], 10.0)
    assert np.isclose(p1_m["percentage_of_district_flooded"], 20.0)
    assert np.isclose(p2_m["percentage_of_district_flooded"], 10.0)

    # Verify dynamic temporal comparison
    comp = summary["temporal_comparison"]
    assert np.isclose(comp["flood_area_change_km2"], -10.0)
    assert np.isclose(comp["flood_area_change_pct_points"], -10.0)


def test_explicit_unosat_shapefile_resolution_no_arbitrary_fallback():
    """Verify that get_unosat_shapefile requires explicit configuration and rejects arbitrary fallback."""
    from pathlib import Path
    from src.preprocess import get_unosat_shapefile

    raw_extract_dir = Path("data/raw/unosat_3954")
    if not raw_extract_dir.exists():
        pytest.skip("Raw UNOSAT directory not present for test")

    # Period 1 explicit resolution
    p1_shp = get_unosat_shapefile(raw_extract_dir, "period_1")
    assert p1_shp.exists()
    assert "20240818_20240826" in p1_shp.name

    # Period 2 explicit resolution
    p2_shp = get_unosat_shapefile(raw_extract_dir, "period_2")
    assert p2_shp.exists()
    assert "20240828_20240904" in p2_shp.name

    # Unknown period raises ValueError
    with pytest.raises(ValueError, match="Unknown observation period key"):
        get_unosat_shapefile(raw_extract_dir, "invalid_period_name")


def test_unosat_water_classification_inspection():
    """Verify that UNOSAT shapefile inspection accurately validates water classification attributes."""
    from pathlib import Path
    from src.preprocess import get_unosat_shapefile, inspect_and_verify_unosat_shapefile

    raw_extract_dir = Path("data/raw/unosat_3954")
    if not raw_extract_dir.exists():
        pytest.skip("Raw UNOSAT directory not present for test")

    p1_shp = get_unosat_shapefile(raw_extract_dir, "period_1")
    meta = inspect_and_verify_unosat_shapefile(p1_shp, "Period 1")

    assert meta["water_class"] == "Flood Water"
    assert meta["water_status"] == "New Water / Water Increase"
    assert "4326" in meta["source_crs"]


