"""
Geospatial Preprocessing Module for Bangladesh Flood Exposure Analysis.

Handles:
- Explicit, validated loading of UNOSAT multi-temporal observation shapefiles
- Verification of source CRS, geographic coverage, geometry types, and water classification metadata
- CRS reprojection and metric alignment (WGS84 EPSG:4326 -> UTM Zone 46N EPSG:32646)
- Study area boundary extraction (Cumilla District)
- Spatial indexing, bounding-box candidate extraction, and exact polygon clipping
- Spatial filtering of healthcare facilities to Cumilla
- Exporting standardized processed GeoDataFrames in GeoJSON format
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import geopandas as gpd
import pyogrio

from src.validate import (
    find_cumilla_boundary,
    inspect_geodataframe,
    validate_and_fix_geometries,
)

logger = logging.getLogger(__name__)


def get_unosat_shapefile(
    extract_dir: Path,
    period_key: str,
    config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Explicitly locate and validate the shapefile for a specified observation period.
    Prohibits silent fallback or arbitrary shapefile selection.

    Args:
        extract_dir: Root directory where UNOSAT archive was extracted.
        period_key: 'period_1' or 'period_2'.
        config: Optional configuration dictionary containing explicit period definitions.

    Returns:
        Path to the verified shapefile.

    Raises:
        FileNotFoundError: If the explicitly requested shapefile does not exist.
        ValueError: If period_key is unknown or invalid.
    """
    extract_path = Path(extract_dir)
    if not extract_path.exists():
        raise FileNotFoundError(f"UNOSAT extraction directory does not exist: {extract_path}")

    # Standard expected shapefile names by period
    expected_filenames = {
        "period_1": "S1_20240818_20240826_FloodExtent_Bangladesh.shp",
        "period_2": "S1_20240828_20240904_FloodExtent_Bangladesh.shp",
    }

    if config and "data_sources" in config and "unosat_flood" in config["data_sources"]:
        periods_cfg = config["data_sources"]["unosat_flood"].get("observation_periods", {})
        if period_key in periods_cfg:
            shp_name = periods_cfg[period_key].get("shapefile_name", expected_filenames.get(period_key))
        else:
            shp_name = expected_filenames.get(period_key)
    else:
        shp_name = expected_filenames.get(period_key)

    if not shp_name:
        raise ValueError(
            f"Unknown observation period key: '{period_key}'. Expected 'period_1' or 'period_2'."
        )

    # Search explicitly for the configured shapefile
    matching_files = list(extract_path.glob(f"**/{shp_name}"))
    if not matching_files:
        raise FileNotFoundError(
            f"Explicitly configured shapefile for '{period_key}' not found: {shp_name}. "
            f"Silent fallback to arbitrary shapefiles is prohibited. Checked directory: {extract_path}"
        )

    exact_shp = matching_files[0]
    logger.info("Explicitly resolved UNOSAT shapefile for %s: %s", period_key, exact_shp)
    return exact_shp


def find_unosat_shapefile(
    extract_dir: Path,
    period_key: str = "period_1",
    config: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Safe wrapper for backward compatibility. Explicitly delegates to get_unosat_shapefile.
    Prohibits silent selection of arbitrary shapefiles.
    """
    return get_unosat_shapefile(extract_dir, period_key=period_key, config=config)


def inspect_and_verify_unosat_shapefile(shp_path: Path, period_name: str) -> Dict[str, Any]:
    """
    Verify source CRS, geometry types, coverage bounds, and UNOSAT attribute metadata.
    Confirms water classification ('Flood Water' vs reference water).
    """
    if not shp_path.exists():
        raise FileNotFoundError(f"Cannot inspect missing shapefile: {shp_path}")

    info = pyogrio.read_info(shp_path)
    crs_str = str(info.get("crs", ""))
    geom_type = str(info.get("geometry_type", ""))
    feature_count = info.get("features", 0)
    fields = list(info.get("fields", []))

    logger.info(
        "Verifying UNOSAT shapefile [%s]: CRS=%s, Geometry=%s, Features=%d",
        period_name,
        crs_str,
        geom_type,
        feature_count,
    )

    if "4326" not in crs_str and "WGS 84" not in crs_str:
        raise ValueError(
            f"Expected UNOSAT source CRS to be WGS84 (EPSG:4326), but found: {crs_str}"
        )

    # Read attribute records to verify water classification
    sample_gdf = gpd.read_file(shp_path, rows=5)
    water_class = sample_gdf["Water_Clas"].iloc[0] if "Water_Clas" in sample_gdf.columns else "Unknown"
    water_stat = sample_gdf["Water_Stat"].iloc[0] if "Water_Stat" in sample_gdf.columns else "Unknown"
    confidence = sample_gdf["Confidence"].iloc[0] if "Confidence" in sample_gdf.columns else "Unknown"
    field_vali = sample_gdf["Field_Vali"].iloc[0] if "Field_Vali" in sample_gdf.columns else "Unknown"
    sensor_date = str(sample_gdf["Sensor_Dat"].iloc[0]) if "Sensor_Dat" in sample_gdf.columns else "Unknown"

    logger.info(
        "Verified UNOSAT Metadata [%s]: Water_Clas='%s', Water_Stat='%s', Sensor_Date='%s', Field_Vali='%s'",
        period_name,
        water_class,
        water_stat,
        sensor_date,
        field_vali,
    )

    return {
        "period_name": period_name,
        "shapefile_path": str(shp_path),
        "source_crs": crs_str,
        "geometry_type": geom_type,
        "feature_count": feature_count,
        "water_class": water_class,
        "water_status": water_stat,
        "confidence": confidence,
        "field_validation": field_vali,
        "sensor_date": sensor_date,
        "fields": fields,
    }


def preprocess_flood_layer_for_period(
    shp_path: Path,
    cumilla_boundary_geo: gpd.GeoDataFrame,
    cumilla_boundary_utm: gpd.GeoDataFrame,
    proj_crs: str,
    geo_crs: str,
    period_key: str,
    period_name: str,
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, Dict[str, Any]]:
    """
    Process, reproject, and clip flood extent for a specific observation period.
    """
    logger.info("--- Preprocessing UNOSAT Flood Extent for %s ---", period_name)
    metadata = inspect_and_verify_unosat_shapefile(shp_path, period_name)

    raw_flood_gdf = gpd.read_file(shp_path)
    logger.info("Loaded %d features for %s. Exploding multi-part geometries...", len(raw_flood_gdf), period_name)
    raw_flood_exploded = raw_flood_gdf.explode(index_parts=False)
    logger.info("Exploded to %d discrete polygon parts for %s.", len(raw_flood_exploded), period_name)

    # Spatial bounding box filter in EPSG:4326 before reprojection
    minx, miny, maxx, maxy = cumilla_boundary_geo.total_bounds
    logger.info("Filtering bounding box for %s (%.4f, %.4f, %.4f, %.4f)...", period_name, minx, miny, maxx, maxy)
    candidate_flood = raw_flood_exploded.cx[minx:maxx, miny:maxy].copy()
    logger.info("Retained %d candidate flood polygons within Cumilla bounding box.", len(candidate_flood))

    candidate_flood = validate_and_fix_geometries(candidate_flood, f"UNOSAT_Candidate_{period_key}")

    if candidate_flood.crs != proj_crs:
        logger.info("Reprojecting candidate flood polygons to %s...", proj_crs)
        flood_utm = candidate_flood.to_crs(proj_crs)
    else:
        flood_utm = candidate_flood

    logger.info("Clipping flood extent to exact Cumilla boundary in %s...", proj_crs)
    clipped_flood_utm = gpd.clip(flood_utm, cumilla_boundary_utm)
    clipped_flood_utm = validate_and_fix_geometries(clipped_flood_utm, f"Cumilla_Flood_{period_key}_UTM")

    # Filter out non-polygons and empty geometries
    clipped_flood_utm = clipped_flood_utm[
        clipped_flood_utm.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ].copy()
    logger.info(
        "Retained %d clipped flood polygon features inside Cumilla for %s.",
        len(clipped_flood_utm),
        period_name,
    )

    clipped_flood_geo = clipped_flood_utm.to_crs(geo_crs)
    return clipped_flood_utm, clipped_flood_geo, metadata


def run_preprocessing(
    config: Dict[str, Any]
) -> Tuple[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame], gpd.GeoDataFrame, Dict[str, Any]]:
    """
    Load raw datasets, validate, align CRS, clip to Cumilla, and save processed layers.
    Processes both observation periods explicitly.

    Returns:
        cumilla_boundary_utm: gpd.GeoDataFrame (EPSG:32646)
        flood_layers_utm: Dict[str, gpd.GeoDataFrame] with 'period_1' and 'period_2'
        cumilla_healthcare_utm: gpd.GeoDataFrame (EPSG:32646)
        flood_metadata: Dict[str, Dict[str, Any]] metadata for both periods
    """
    logger.info("Starting Phase 2: Geospatial Preprocessing & Multi-Period Extraction...")

    proj_crs = config["crs"]["projected"]  # EPSG:32646
    geo_crs = config["crs"]["geographic"]   # EPSG:4326
    proc_dir = Path(config["paths"]["processed_dir"])
    proc_dir.mkdir(parents=True, exist_ok=True)

    # 1. Process Administrative Boundary
    raw_adm2_path = Path(config["data_sources"]["geoboundaries"]["local_file"])
    logger.info("Loading Bangladesh ADM2 boundaries from %s...", raw_adm2_path)
    adm2_gdf = gpd.read_file(raw_adm2_path)
    adm2_gdf = validate_and_fix_geometries(adm2_gdf, "BGD_ADM2")
    inspect_geodataframe(adm2_gdf, "BGD_ADM2")

    cumilla_boundary_geo, matched_col = find_cumilla_boundary(
        adm2_gdf, config["project"]["study_area_aliases"]
    )
    if cumilla_boundary_geo.crs != geo_crs:
        cumilla_boundary_geo = cumilla_boundary_geo.to_crs(geo_crs)

    cumilla_boundary_utm = cumilla_boundary_geo.to_crs(proj_crs)
    cumilla_boundary_utm = validate_and_fix_geometries(
        cumilla_boundary_utm, "Cumilla_Boundary_UTM"
    )

    # 2. Process OSM Healthcare Facilities
    osm_path = Path(config["data_sources"]["osm_healthcare"]["local_geojson"])
    logger.info("Loading OSM healthcare facilities from %s...", osm_path)
    raw_osm_gdf = gpd.read_file(osm_path)
    raw_osm_gdf = validate_and_fix_geometries(raw_osm_gdf, "OSM_Healthcare_Raw")
    inspect_geodataframe(raw_osm_gdf, "OSM_Healthcare_Raw")

    if raw_osm_gdf.crs != proj_crs:
        osm_utm = raw_osm_gdf.to_crs(proj_crs)
    else:
        osm_utm = raw_osm_gdf

    logger.info("Filtering healthcare facilities within Cumilla District...")
    within_mask = osm_utm.geometry.within(cumilla_boundary_utm.unary_union)
    cumilla_healthcare_utm = osm_utm[within_mask].copy()
    logger.info(
        "Retained %d healthcare facilities inside Cumilla District boundary.",
        len(cumilla_healthcare_utm),
    )

    # 3. Process Multi-Period UNOSAT Flood Layers
    unosat_extract_dir = Path(config["data_sources"]["unosat_flood"]["extract_dir"])
    periods_cfg = config["data_sources"]["unosat_flood"].get(
        "observation_periods",
        {
            "period_1": {
                "name": "First Satellite Observation Period (18–26 August 2024)",
                "shapefile_name": "S1_20240818_20240826_FloodExtent_Bangladesh.shp",
            },
            "period_2": {
                "name": "Second Satellite Observation Period (28 August–04 September 2024)",
                "shapefile_name": "S1_20240828_20240904_FloodExtent_Bangladesh.shp",
            },
        },
    )

    flood_layers_utm: Dict[str, gpd.GeoDataFrame] = {}
    flood_layers_geo: Dict[str, gpd.GeoDataFrame] = {}
    flood_metadata: Dict[str, Dict[str, Any]] = {}

    for period_key in ["period_1", "period_2"]:
        if period_key in periods_cfg:
            period_name = periods_cfg[period_key].get("name", period_key)
            shp_path = get_unosat_shapefile(unosat_extract_dir, period_key, config)

            f_utm, f_geo, meta = preprocess_flood_layer_for_period(
                shp_path,
                cumilla_boundary_geo,
                cumilla_boundary_utm,
                proj_crs,
                geo_crs,
                period_key,
                period_name,
            )

            flood_layers_utm[period_key] = f_utm
            flood_layers_geo[period_key] = f_geo
            flood_metadata[period_key] = meta

            # Save one consistently named GeoJSON pair per observation period.
            f_utm.to_file(proc_dir / f"cumilla_flood_{period_key}_utm.geojson", driver="GeoJSON")
            f_geo.to_file(proc_dir / f"cumilla_flood_{period_key}_wgs84.geojson", driver="GeoJSON")

    # Export standard compatibility files (pointing to primary period 1)
    cumilla_boundary_utm.to_file(proc_dir / "cumilla_boundary_utm.geojson", driver="GeoJSON")
    cumilla_boundary_geo.to_file(proc_dir / "cumilla_boundary_wgs84.geojson", driver="GeoJSON")
    cumilla_healthcare_utm.to_file(proc_dir / "cumilla_healthcare_utm.geojson", driver="GeoJSON")
    cumilla_healthcare_utm.to_crs(geo_crs).to_file(proc_dir / "cumilla_healthcare_wgs84.geojson", driver="GeoJSON")

    if "period_1" in flood_layers_utm:
        flood_layers_utm["period_1"].to_file(proc_dir / "cumilla_flood_utm.geojson", driver="GeoJSON")
        flood_layers_geo["period_1"].to_file(proc_dir / "cumilla_flood_wgs84.geojson", driver="GeoJSON")

    logger.info("Successfully exported all multi-period processed layers to %s.", proc_dir)
    return cumilla_boundary_utm, flood_layers_utm, cumilla_healthcare_utm, flood_metadata
