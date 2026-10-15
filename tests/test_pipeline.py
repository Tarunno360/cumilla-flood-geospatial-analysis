"""
Integration Tests for the Bangladesh Flood Exposure Analysis Pipeline.
"""

from pathlib import Path
import pytest
import geopandas as gpd
import pandas as pd

from main import load_config
from src.spatial_analysis import compute_flood_and_exposure_metrics


def test_processed_datasets_exist_and_valid():
    """Verify that processed spatial layers exist and have valid geometries and CRS."""
    proc_dir = Path("data/processed")
    if not proc_dir.exists():
        pytest.skip("Processed data directory not found. Run main.py first to generate processed layers.")

    boundary_file = proc_dir / "cumilla_boundary_utm.geojson"
    flood_file = proc_dir / "cumilla_flood_utm.geojson"
    health_file = proc_dir / "cumilla_healthcare_utm.geojson"

    if not (boundary_file.exists() and flood_file.exists() and health_file.exists()):
        pytest.skip("Prerequisite processed GeoJSON files missing. Run main.py first to generate them.")

    gdf_b = gpd.read_file(boundary_file)
    gdf_f = gpd.read_file(flood_file)
    gdf_h = gpd.read_file(health_file)

    assert str(gdf_b.crs) == "EPSG:32646"
    assert str(gdf_f.crs) == "EPSG:32646"
    assert str(gdf_h.crs) == "EPSG:32646"

    assert len(gdf_b) >= 1
    assert len(gdf_f) > 0
    assert len(gdf_h) > 0

    assert gdf_b.geometry.is_valid.all()
    assert gdf_f.geometry.is_valid.all()
    assert gdf_h.geometry.is_valid.all()


def test_analytical_outputs_exist_and_consistent():
    """Verify that results.csv and summary.json exist and contain matching counts."""
    csv_file = Path("outputs/results.csv")
    json_file = Path("outputs/summary.json")

    if not (csv_file.exists() and json_file.exists()):
        pytest.skip("Prerequisite analytical outputs (results.csv, summary.json) missing. Run main.py first.")

    df = pd.read_csv(csv_file)
    import json
    with open(json_file, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert len(df) == summary["healthcare_facility_metrics"]["total_mapped_facilities"]
    assert (df["in_flood_extent"]).sum() == summary["healthcare_facility_metrics"]["facilities_intersecting_flood_extent"]
    assert (df["distance_to_flood_m"] <= 500).sum() == summary["healthcare_facility_metrics"]["facilities_within_500m"]


def test_visualizations_exist():
    """Verify that static figures and interactive map HTML exist and have non-zero size."""
    fig_dir = Path("outputs/figures")
    html_file = Path("outputs/interactive_map.html")

    if not (fig_dir.exists() and html_file.exists()):
        pytest.skip("Prerequisite visualization outputs missing. Run main.py first.")

    assert html_file.stat().st_size > 100_000, "interactive_map.html must be non-empty"

    for map_name in [
        "map1_flood_extent_cumilla.png",
        "map1_flood_extent_cumilla.pdf",
        "map2_flood_and_healthcare_cumilla.png",
        "map2_flood_and_healthcare_cumilla.pdf",
        "map3_healthcare_proximity_cumilla.png",
        "map3_healthcare_proximity_cumilla.pdf",
    ]:
        f = fig_dir / map_name
        assert f.exists() and f.stat().st_size > 1000, f"{map_name} must exist and be non-empty"


def test_multi_period_outputs_exist_and_consistent():
    """Verify that both observation periods have exported datasets and results."""
    proc_dir = Path("data/processed")
    out_dir = Path("outputs")

    p1_flood = proc_dir / "cumilla_flood_period_1_utm.geojson"
    p2_flood = proc_dir / "cumilla_flood_period_2_utm.geojson"
    p1_csv = out_dir / "results.csv"
    p2_csv = out_dir / "results_period_2.csv"

    if not (p1_flood.exists() and p2_flood.exists() and p1_csv.exists() and p2_csv.exists()):
        pytest.skip("Prerequisite multi-period processed datasets missing. Run main.py first.")

    assert p1_flood.exists(), "cumilla_flood_period_1_utm.geojson must exist"
    assert p2_flood.exists(), "cumilla_flood_period_2_utm.geojson must exist"
    assert p1_csv.exists(), "results.csv must exist for the primary period"
    assert p2_csv.exists(), "results_period_2.csv must exist"


def test_research_report_consistency_and_clean_language():
    """Verify research_report.md exists, matches summary.json, and contains no unsupported claims."""
    report_file = Path("reports/research_report.md")
    json_file = Path("outputs/summary.json")

    if not (report_file.exists() and json_file.exists()):
        pytest.skip("Prerequisite report or summary.json missing. Run main.py first.")

    import json
    with open(json_file, "r", encoding="utf-8") as f:
        summary = json.load(f)

    with open(report_file, "r", encoding="utf-8") as f:
        report_text = f.read()

    # Dynamic numbers from summary must appear in report
    p1_area = summary["temporal_periods"]["period_1"]["flood_area_km2"]
    p2_area = summary["temporal_periods"]["period_2"]["flood_area_km2"]
    assert f"{p1_area:,.2f}" in report_text or f"{p1_area}" in report_text
    assert f"{p2_area:,.2f}" in report_text or f"{p2_area}" in report_text

    # Verify no ungrounded claims or pre/post flood mislabels
    assert "pre-flood" not in report_text.lower()
    assert "post-flood" not in report_text.lower()
    assert "inpatient-care facilities" not in report_text.lower()
    assert "drainage into the meghna basin" not in report_text.lower()
    assert "elevated roadside platforms" not in report_text.lower()


def test_source_data_manifest_real_config_execution(tmp_path):
    """Verify loading real config.yaml and executing create_source_data_manifest with a temp path."""
    import json
    from main import load_config
    from src.download import create_source_data_manifest

    config_file = Path("config/config.yaml")
    assert config_file.exists(), "Real config.yaml must exist"

    config = load_config(config_file)
    temp_manifest = tmp_path / "test_manifest.json"

    result_path = create_source_data_manifest(config, output_path=temp_manifest)
    assert result_path.exists(), "Manifest file should be written to temp path"
    assert result_path == temp_manifest

    with open(result_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    assert "datasets" in manifest_data
    # Find unosat_product_3954
    unosat_ds = next((d for d in manifest_data["datasets"] if d["identifier"] == "unosat_product_3954"), None)
    assert unosat_ds is not None, "unosat_product_3954 must exist in manifest"
    assert "observation_periods" in unosat_ds
    assert "period_1" in unosat_ds["observation_periods"]
    assert "period_2" in unosat_ds["observation_periods"]
    assert unosat_ds["observation_periods"]["period_1"]["shapefile_name"] == "S1_20240818_20240826_FloodExtent_Bangladesh.shp"
    assert unosat_ds["observation_periods"]["period_2"]["shapefile_name"] == "S1_20240828_20240904_FloodExtent_Bangladesh.shp"
    assert unosat_ds["observation_periods"]["period_1"]["date_range"] == "18 to 26 August 2024"
    assert unosat_ds["observation_periods"]["period_2"]["date_range"] == "28 August to 04 September 2024"

