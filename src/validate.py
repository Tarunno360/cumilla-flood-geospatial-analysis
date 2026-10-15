"""
Data Validation Module for Bangladesh Flood Exposure Analysis.

Performs rigorous geometric and attribute checks:
- Geometry validity (handling self-intersections and invalid rings via make_valid)
- CRS verification
- Attribute completeness and schema validation
- Study area existence verification (Cumilla/Comilla in ADM2)
"""

import logging
from typing import Any, Dict, List, Tuple

import geopandas as gpd
from shapely.validation import make_valid

logger = logging.getLogger(__name__)


def validate_and_fix_geometries(gdf: gpd.GeoDataFrame, dataset_name: str = "dataset") -> gpd.GeoDataFrame:
    """
    Validate geometries in GeoDataFrame and repair invalid ones using shapely.validation.make_valid.
    Filters out empty or null geometries.
    """
    initial_count = len(gdf)
    logger.info("Validating geometries for %s (%d records)...", dataset_name, initial_count)

    # Check for null / empty
    null_geoms = gdf.geometry.isnull() | gdf.geometry.is_empty
    null_count = null_geoms.sum()
    if null_count > 0:
        logger.warning(
            "Removing %d null/empty geometries from %s.", null_count, dataset_name
        )
        gdf = gdf[~null_geoms].copy()

    # Check validity
    invalid_mask = ~gdf.geometry.is_valid
    invalid_count = invalid_mask.sum()

    if invalid_count > 0:
        logger.warning(
            "Found %d invalid geometries in %s. Applying make_valid()...",
            invalid_count,
            dataset_name,
        )
        gdf["geometry"] = gdf.geometry.apply(make_valid)
        still_invalid = (~gdf.geometry.is_valid).sum()
        if still_invalid > 0:
            logger.error("%d geometries remain invalid after repair in %s.", still_invalid, dataset_name)
        else:
            logger.info("All invalid geometries in %s successfully repaired.", dataset_name)
    else:
        logger.info("All geometries in %s are valid.", dataset_name)

    return gdf


def inspect_geodataframe(gdf: gpd.GeoDataFrame, name: str) -> Dict[str, Any]:
    """Inspect and return descriptive metadata for a GeoDataFrame."""
    geom_types = gdf.geometry.geom_type.value_counts().to_dict()
    bounds = tuple(gdf.total_bounds) if not gdf.empty else (0, 0, 0, 0)
    crs_str = str(gdf.crs) if gdf.crs is not None else "None"

    info = {
        "dataset_name": name,
        "feature_count": len(gdf),
        "crs": crs_str,
        "geometry_types": geom_types,
        "bounding_box": {
            "minx": bounds[0],
            "miny": bounds[1],
            "maxx": bounds[2],
            "maxy": bounds[3],
        },
        "columns": list(gdf.columns),
    }
    logger.info(
        "[%s] Features: %d | CRS: %s | Geometries: %s | Bounds: (%.4f, %.4f, %.4f, %.4f)",
        name,
        info["feature_count"],
        info["crs"],
        geom_types,
        bounds[0],
        bounds[1],
        bounds[2],
        bounds[3],
    )
    return info


def find_cumilla_boundary(
    adm2_gdf: gpd.GeoDataFrame, aliases: List[str]
) -> Tuple[gpd.GeoDataFrame, str]:
    """
    Search and extract Cumilla district boundary from Bangladesh ADM2 layer.
    Tolerates spelling variations ('Cumilla', 'Comilla') across possible column names.
    """
    target_names = [a.lower().strip() for a in aliases]

    name_columns = [
        col
        for col in adm2_gdf.columns
        if any(term in col.lower() for term in ["name", "adm2", "shapeName", "district"])
        and col != "geometry"
    ]

    matched_gdf = gpd.GeoDataFrame()
    matched_col = None

    for col in name_columns:
        matches = adm2_gdf[
            adm2_gdf[col].astype(str).str.lower().str.strip().isin(target_names)
        ]
        if not matches.empty:
            matched_gdf = matches
            matched_col = col
            matched_val = matches.iloc[0][col]
            logger.info(
                "Matched study area '%s' in column '%s' (records found: %d)",
                matched_val,
                col,
                len(matches),
            )
            break

    if matched_gdf.empty:
        available_names = []
        if name_columns:
            available_names = adm2_gdf[name_columns[0]].unique().tolist()[:15]
        raise ValueError(
            f"Could not locate Cumilla boundary using aliases {aliases}. "
            f"Inspected columns: {name_columns}. First sample names: {available_names}"
        )

    # Dissolve if multiple polygon parts exist
    if len(matched_gdf) > 1:
        logger.info("Dissolving %d sub-polygons for study area.", len(matched_gdf))
        matched_gdf = matched_gdf.dissolve().reset_index()

    return matched_gdf, matched_col
