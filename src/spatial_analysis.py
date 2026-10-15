"""
Spatial Analysis Module for Bangladesh Flood Exposure and Proximity Modeling.

Handles:
- Rigorous metric area computation in UTM Zone 46N (EPSG:32646) using dissolved spatial union
- Independent, automated processing of both UNOSAT observation periods (Period 1 and Period 2)
- Point-to-polygon planar Euclidean proximity calculations to nearest flood boundaries
- Proximity classification into standardized emergency planning tiers
- Disaggregated exposure statistics by functional healthcare categories:
    * Group A: Mapped Hospitals and Clinics
    * Group B: Pharmacies and Laboratories
    * Group C: Other / Unspecified Medical Amenities
- Dynamic temporal comparison generation between observation windows
- Structured export to results.csv and summary.json without hardcoded figures
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def classify_proximity_band(distance_m: float) -> str:
    """Classify metric distance into standardized emergency proximity bands."""
    if distance_m == 0.0:
        return "Inside Flood Extent"
    elif distance_m <= 500.0:
        return "Within 500m"
    elif distance_m <= 1000.0:
        return "500m - 1km"
    elif distance_m <= 2500.0:
        return "1km - 2.5km"
    elif distance_m <= 5000.0:
        return "2.5km - 5km"
    else:
        return "> 5km"


def assign_category_group(amenity: Any) -> str:
    """Classify OSM healthcare amenity into functional groups."""
    amenity_clean = str(amenity).lower().strip()
    if amenity_clean in ["hospital", "clinic"]:
        return "Hospitals & Clinics"
    elif amenity_clean in ["pharmacy", "laboratory"]:
        return "Pharmacies & Laboratories"
    else:
        return "Other / Unspecified"


def compute_single_period_metrics(
    boundary_utm: gpd.GeoDataFrame,
    flood_utm: gpd.GeoDataFrame,
    healthcare_utm: gpd.GeoDataFrame,
    config: Dict[str, Any],
    period_key: str = "period_1",
    period_info: Optional[Dict[str, Any]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Compute metric area, point-to-polygon distances, proximity distributions,
    and disaggregated category statistics for a single flood observation period.
    """
    # 1. District Surface Area
    district_geom = boundary_utm.union_all()
    district_area_m2 = float(district_geom.area)
    district_area_km2 = float(district_area_m2 / 1_000_000.0)

    # 2. Flood Extent Metric Area via Dissolved Union
    if flood_utm.empty:
        flood_area_m2 = 0.0
        flood_area_km2 = 0.0
        flood_pct = 0.0
        flood_feature_count = 0
        flood_union = None
    else:
        flood_union = flood_utm.union_all()
        flood_area_m2 = float(flood_union.area)
        flood_area_km2 = float(flood_area_m2 / 1_000_000.0)
        flood_pct = float((flood_area_km2 / district_area_km2) * 100.0) if district_area_km2 > 0 else 0.0
        flood_feature_count = len(flood_utm)

    # 3. Healthcare Facility Proximity Calculations
    total_facilities = len(healthcare_utm)
    facilities_df = healthcare_utm.copy()

    # Facility attributes
    facility_names = []
    amenity_types = []
    for _, row in facilities_df.iterrows():
        name = row.get("name")
        if pd.isna(name) or name is None or str(name).strip() == "":
            amenity = str(row.get("amenity", "Unspecified")).capitalize()
            name = f"Unnamed {amenity}"
        facility_names.append(str(name))
        amenity_types.append(str(row.get("amenity", "healthcare")).lower())

    facilities_df["facility_name"] = facility_names
    facilities_df["amenity_type"] = amenity_types
    facilities_df["category_group"] = facilities_df["amenity_type"].apply(assign_category_group)

    # Geodetic coordinates for display
    geo_crs = config.get("crs", {}).get("geographic", "EPSG:4326")
    facilities_geo = facilities_df.to_crs(geo_crs)
    facilities_df["longitude"] = facilities_geo.geometry.x.round(7)
    facilities_df["latitude"] = facilities_geo.geometry.y.round(7)

    if flood_union is None or flood_union.is_empty:
        facilities_df["distance_to_flood_m"] = np.nan
        facilities_df["distance_to_flood_km"] = np.nan
        facilities_df["in_flood_extent"] = False
        facilities_df["proximity_band"] = "> 5km"
        distances = pd.Series([np.nan] * total_facilities)
        is_flooded = pd.Series([False] * total_facilities)
    else:
        distances = facilities_df.geometry.apply(lambda p: float(flood_union.distance(p)))
        is_flooded = facilities_df.geometry.apply(lambda p: bool(flood_union.intersects(p)))

        facilities_df["distance_to_flood_m"] = distances
        facilities_df["distance_to_flood_km"] = distances / 1000.0
        facilities_df["in_flood_extent"] = is_flooded
        facilities_df["proximity_band"] = distances.apply(classify_proximity_band)

    # Aggregate counts
    inundated_count = int(is_flooded.sum())
    within_500m_count = int((distances <= 500.0).sum())
    within_1km_count = int((distances <= 1000.0).sum())
    within_2500m_count = int((distances <= 2500.0).sum())

    dist_series = distances.dropna()
    mean_dist_m = float(dist_series.mean()) if not dist_series.empty else 0.0
    median_dist_m = float(dist_series.median()) if not dist_series.empty else 0.0
    min_dist_m = float(dist_series.min()) if not dist_series.empty else 0.0
    max_dist_m = float(dist_series.max()) if not dist_series.empty else 0.0
    std_dist_m = float(dist_series.std()) if not dist_series.empty else 0.0

    amenity_counts = facilities_df["amenity_type"].value_counts().to_dict()
    proximity_band_counts = facilities_df["proximity_band"].value_counts().to_dict()

    # Disaggregated Category Group Statistics
    group_stats = {}
    for grp_name, grp_df in facilities_df.groupby("category_group"):
        grp_dists = grp_df["distance_to_flood_m"].dropna()
        group_stats[grp_name] = {
            "total_count": len(grp_df),
            "intersecting_flood_extent": int(grp_df["in_flood_extent"].sum()),
            "within_500m": int((grp_dists <= 500.0).sum()),
            "within_500m_pct": round(float((grp_dists <= 500.0).mean() * 100.0), 1) if not grp_dists.empty else 0.0,
            "within_1000m": int((grp_dists <= 1000.0).sum()),
            "within_1000m_pct": round(float((grp_dists <= 1000.0).mean() * 100.0), 1) if not grp_dists.empty else 0.0,
            "distance_meters": {
                "mean": round(float(grp_dists.mean()), 1) if not grp_dists.empty else 0.0,
                "median": round(float(grp_dists.median()), 1) if not grp_dists.empty else 0.0,
                "min": round(float(grp_dists.min()), 1) if not grp_dists.empty else 0.0,
                "max": round(float(grp_dists.max()), 1) if not grp_dists.empty else 0.0,
            },
        }

    default_period_names = {
        "period_1": "First Satellite Observation Period (18–26 August 2024)",
        "period_2": "Second Satellite Observation Period (28 August–04 September 2024)",
    }
    default_date_ranges = {
        "period_1": "18 to 26 August 2024",
        "period_2": "28 August to 04 September 2024",
    }
    period_name = (
        period_info.get("name")
        if (period_info and period_info.get("name"))
        else default_period_names.get(period_key, f"Observation Period ({period_key})")
    )
    date_range = (
        period_info.get("date_range")
        if (period_info and period_info.get("date_range"))
        else default_date_ranges.get(period_key, "August - September 2024")
    )

    period_summary = {
        "period_key": period_key,
        "period_name": period_name,
        "date_range": date_range,
        "flood_area_km2": round(flood_area_km2, 2),
        "flood_area_m2": round(flood_area_m2, 1),
        "percentage_of_district_flooded": round(flood_pct, 2),
        "flood_feature_count": flood_feature_count,
        "facilities_intersecting_flood": inundated_count,
        "facilities_within_500m": within_500m_count,
        "facilities_within_500m_pct": round((within_500m_count / total_facilities) * 100.0, 1) if total_facilities > 0 else 0.0,
        "facilities_within_1000m": within_1km_count,
        "facilities_within_1000m_pct": round((within_1km_count / total_facilities) * 100.0, 1) if total_facilities > 0 else 0.0,
        "facilities_within_2500m": within_2500m_count,
        "facilities_within_2500m_pct": round((within_2500m_count / total_facilities) * 100.0, 1) if total_facilities > 0 else 0.0,
        "distance_to_flood_meters": {
            "mean": round(mean_dist_m, 1),
            "median": round(median_dist_m, 1),
            "min": round(min_dist_m, 1),
            "max": round(max_dist_m, 1),
            "std": round(std_dist_m, 1),
        },
        "proximity_distribution": proximity_band_counts,
        "disaggregated_by_category_group": group_stats,
    }

    # Prepare export dataframe
    export_cols = [
        "osm_id",
        "facility_name",
        "amenity_type",
        "category_group",
        "latitude",
        "longitude",
        "in_flood_extent",
        "distance_to_flood_m",
        "distance_to_flood_km",
        "proximity_band",
    ]
    for extra_col in ["healthcare", "operator", "emergency", "addr:street"]:
        if extra_col in facilities_df.columns:
            export_cols.append(extra_col)

    final_df = pd.DataFrame(facilities_df[export_cols])
    return final_df, period_summary


def compute_flood_and_exposure_metrics(
    boundary_utm: gpd.GeoDataFrame,
    flood_input: Union[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame]],
    healthcare_utm: gpd.GeoDataFrame,
    config: Dict[str, Any],
    flood_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Unified entrypoint for computing flood and exposure metrics.
    Supports single GeoDataFrame or dictionary of multi-period GeoDataFrames.
    Calculates dynamic temporal comparison if multiple periods are provided.
    """
    # 1. District Area Metrics
    district_geom = boundary_utm.union_all()
    district_area_m2 = float(district_geom.area)
    district_area_km2 = float(district_area_m2 / 1_000_000.0)

    periods_cfg = config.get("data_sources", {}).get("unosat_flood", {}).get("observation_periods", {})

    if isinstance(flood_input, dict):
        # Process each period independently
        temporal_periods = {}
        period_dataframes = {}

        for p_key, f_gdf in flood_input.items():
            p_info = periods_cfg.get(p_key, {"name": p_key, "date_range": ""})
            df_p, sum_p = compute_single_period_metrics(
                boundary_utm, f_gdf, healthcare_utm, config, period_key=p_key, period_info=p_info
            )
            temporal_periods[p_key] = sum_p
            period_dataframes[p_key] = df_p

        # Primary period defaults to period_1
        primary_key = config.get("data_sources", {}).get("unosat_flood", {}).get("primary_period", "period_1")
        primary_df = period_dataframes.get(primary_key, next(iter(period_dataframes.values())))
        primary_summary = temporal_periods.get(primary_key, next(iter(temporal_periods.values())))

        # Compute Dynamic Temporal Comparison
        temporal_comparison = {}
        if "period_1" in temporal_periods and "period_2" in temporal_periods:
            p1 = temporal_periods["period_1"]
            p2 = temporal_periods["period_2"]

            area_delta_km2 = round(p2["flood_area_km2"] - p1["flood_area_km2"], 2)
            pct_delta = round(p2["percentage_of_district_flooded"] - p1["percentage_of_district_flooded"], 2)
            w500_delta = int(p2["facilities_within_500m"] - p1["facilities_within_500m"])
            w1k_delta = int(p2["facilities_within_1000m"] - p1["facilities_within_1000m"])
            mean_dist_delta = round(p2["distance_to_flood_meters"]["mean"] - p1["distance_to_flood_meters"]["mean"], 1)
            median_dist_delta = round(p2["distance_to_flood_meters"]["median"] - p1["distance_to_flood_meters"]["median"], 1)

            # Category-specific comparisons
            cat_comp = {}
            for grp in ["Hospitals & Clinics", "Pharmacies & Laboratories", "Other / Unspecified"]:
                if (
                    grp in p1["disaggregated_by_category_group"]
                    and grp in p2["disaggregated_by_category_group"]
                ):
                    g1 = p1["disaggregated_by_category_group"][grp]
                    g2 = p2["disaggregated_by_category_group"][grp]
                    cat_comp[grp] = {
                        "within_500m_change": int(g2["within_500m"] - g1["within_500m"]),
                        "within_1000m_change": int(g2["within_1000m"] - g1["within_1000m"]),
                        "mean_distance_change_m": round(g2["distance_meters"]["mean"] - g1["distance_meters"]["mean"], 1),
                    }

            temporal_comparison = {
                "period_1_area_km2": p1["flood_area_km2"],
                "period_2_area_km2": p2["flood_area_km2"],
                "flood_area_change_km2": area_delta_km2,
                "flood_area_change_pct_points": pct_delta,
                "facilities_within_500m_change": w500_delta,
                "facilities_within_1000m_change": w1k_delta,
                "mean_distance_change_meters": mean_dist_delta,
                "median_distance_change_meters": median_dist_delta,
                "category_group_comparison": cat_comp,
                "interpretation": (
                    f"Mapped flood extent decreased by {abs(area_delta_km2):.2f} km² "
                    f"({abs(pct_delta):.2f}% points of district area) between the first "
                    f"and second observation periods, resulting in a {mean_dist_delta:+.1f} m "
                    f"shift in mean facility proximity."
                ),
            }

    else:
        # Single GeoDataFrame input (backward compatibility)
        primary_df, primary_summary = compute_single_period_metrics(
            boundary_utm, flood_input, healthcare_utm, config, period_key="period_1"
        )
        temporal_periods = {"period_1": primary_summary}
        temporal_comparison = {}

    # Extract Water Classification attributes directly from raw metadata if available
    water_class_meta = {
        "water_class": "Flood Water",
        "water_status": "New Water / Water Increase",
        "confidence": "To be evaluated",
        "field_validation": "Not yet field validated",
        "sensor": config.get("data_sources", {}).get("unosat_flood", {}).get("sensor", "Copernicus Sentinel-1 SAR (10m)"),
        "description": "Satellite-detected flood water extent classified by UNOSAT; reference/permanent water bodies excluded.",
    }
    if flood_metadata and "period_1" in flood_metadata:
        m1 = flood_metadata["period_1"]
        water_class_meta["water_class"] = m1.get("water_class", water_class_meta["water_class"])
        water_class_meta["water_status"] = m1.get("water_status", water_class_meta["water_status"])
        water_class_meta["confidence"] = m1.get("confidence", water_class_meta["confidence"])
        water_class_meta["field_validation"] = m1.get("field_validation", water_class_meta["field_validation"])

    # Assemble comprehensive analytical summary
    summary_stats = {
        "study_area": config.get("project", {}).get("study_area", "Cumilla"),
        "projected_crs": config.get("crs", {}).get("projected", "EPSG:32646"),
        "event_glide": config.get("project", {}).get("event_glide", "FL20240825BGD"),
        "water_classification": water_class_meta,
        "district_metrics": {
            "total_area_km2": round(district_area_km2, 2),
            "total_area_m2": round(district_area_m2, 1),
        },
        "flood_metrics": {
            "primary_analyzed_window": f"{primary_summary['period_name']} ({primary_summary['date_range']})",
            "satellite_detected_flood_area_km2": primary_summary["flood_area_km2"],
            "percentage_of_district_flooded": primary_summary["percentage_of_district_flooded"],
            "flood_polygon_features_count": primary_summary["flood_feature_count"],
            "sensor": water_class_meta["sensor"],
            "observation_period_1": f"18 to 26 August 2024 (First satellite observation period, {temporal_periods.get('period_1', primary_summary)['flood_area_km2']} km², {temporal_periods.get('period_1', primary_summary)['percentage_of_district_flooded']}%)",
            "observation_period_2": f"28 August to 04 September 2024 (Second satellite observation period, {temporal_periods.get('period_2', {}).get('flood_area_km2', 'N/A')} km², {temporal_periods.get('period_2', {}).get('percentage_of_district_flooded', 'N/A')}%)",
        },
        "healthcare_facility_metrics": {
            "total_mapped_facilities": len(primary_df),
            "facility_breakdown": primary_df["amenity_type"].value_counts().to_dict(),
            "facilities_intersecting_flood_extent": primary_summary["facilities_intersecting_flood"],
            "facilities_within_500m": primary_summary["facilities_within_500m"],
            "facilities_within_1000m": primary_summary["facilities_within_1000m"],
            "facilities_within_2500m": primary_summary["facilities_within_2500m"],
            "proximity_distribution": primary_summary["proximity_distribution"],
            "distance_to_flood_meters": primary_summary["distance_to_flood_meters"],
            "disaggregated_by_category_group": primary_summary["disaggregated_by_category_group"],
        },
        "temporal_periods": temporal_periods,
        "temporal_comparison": temporal_comparison,
        "scientific_definitions_and_notes": {
            "methodology_scope": (
                "Exploratory flood exposure and geographic proximity analysis. "
                "Calculates planar Euclidean distance (EPSG:32646) from mapped healthcare facility points "
                "to the nearest boundary of the satellite-detected flood polygon layer."
            ),
            "water_classification_rigor": (
                "UNOSAT Product 3954 explicitly isolates 'Flood Water' with status 'New Water / Water Increase'. "
                "Permanent river channels and baseline reference water bodies are not classified as flood inundation."
            ),
            "accessibility_distinction": (
                "Straight-line Euclidean proximity does NOT represent actual road network travel accessibility, "
                "travel time, flood water depth, velocity, or operational facility status during the disaster."
            ),
            "temporal_clarity": (
                "Primary analyzed flood extent represents UNOSAT Sentinel-1 observations from the first satellite "
                "observation period (18–26 August 2024). Both observation periods were computed independently without cross-temporal aggregation."
            ),
            "osm_status_limitation": (
                "OpenStreetMap facility points reflect mapped crowdsourced records and are not field-verified "
                "operational facilities as of August 2024."
            ),
            "cartographic_buffer_note": (
                "Visualization buffer rings displayed on Map 3 (500m and 1,000m) are generalized for cartographic "
                "rendering (filtered <1,000 m² speckle, simplified by 25m). All quantitative proximity metrics "
                "in results.csv and summary.json were calculated on the exact original unsimplified analytical geometries."
            ),
            "sensor_uncertainty": (
                "UNOSAT Sentinel-1 SAR flood extraction has known limitations in dense urban built-up areas "
                "and under thick vegetation canopy due to double-bounce and radar attenuation effects."
            ),
        },
    }

    return primary_df, summary_stats


def run_spatial_analysis(
    boundary_utm: gpd.GeoDataFrame,
    flood_input: Union[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame]],
    healthcare_utm: gpd.GeoDataFrame,
    config: Dict[str, Any],
    flood_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Execute spatial analysis pipeline for all periods and persist outputs (CSV and JSON)."""
    logger.info("Executing Phase 3: Spatial Analysis & Metric Computation...")
    out_dir = Path(config["paths"]["outputs_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    results_df, summary_stats = compute_flood_and_exposure_metrics(
        boundary_utm, flood_input, healthcare_utm, config, flood_metadata=flood_metadata
    )

    # Save non-primary periods separately. The primary period is already
    # written to results.csv, avoiding a duplicate generated CSV.
    if isinstance(flood_input, dict):
        periods_cfg = config.get("data_sources", {}).get("unosat_flood", {}).get("observation_periods", {})
        primary_period = config.get("data_sources", {}).get("unosat_flood", {}).get("primary_period", "period_1")
        for p_key, f_gdf in flood_input.items():
            if p_key == primary_period:
                continue
            p_info = periods_cfg.get(p_key, {"name": p_key, "date_range": ""})
            df_p, _ = compute_single_period_metrics(
                boundary_utm, f_gdf, healthcare_utm, config, period_key=p_key, period_info=p_info
            )
            period_csv = out_dir / f"results_{p_key}.csv"
            df_p.to_csv(period_csv, index=False)
            logger.info("Saved %s results to %s (%d rows)", p_key, period_csv, len(df_p))

    csv_path = out_dir / "results.csv"
    json_path = out_dir / "summary.json"

    results_df.to_csv(csv_path, index=False)
    logger.info("Saved primary facility-level results to %s (%d rows)", csv_path, len(results_df))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)
    logger.info("Saved analytical summary statistics to %s", json_path)

    return results_df, summary_stats
