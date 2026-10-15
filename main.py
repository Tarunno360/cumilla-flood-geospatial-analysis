#!/usr/bin/env python3
"""
Main execution pipeline for Bangladesh flood exposure and healthcare facility proximity analysis.
Case Study: Cumilla District, August 2024 Floods.

Supported execution:
    conda run -n geotech-flood python main.py
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

import geopandas as gpd
import yaml

from src.download import run_data_acquisition
from src.preprocess import run_preprocessing
from src.reporting import generate_research_report
from src.spatial_analysis import run_spatial_analysis
from src.visualize import generate_interactive_map, generate_static_maps

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(config_path: Path = Path("config/config.yaml")) -> Dict[str, Any]:
    """Load and validate YAML configuration file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def main():
    parser = argparse.ArgumentParser(
        description="Geospatial pipeline: Cumilla flood exposure and healthcare facility proximity"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.yaml"),
        help="Path to YAML configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip data download and use existing cached files in data/raw/",
    )
    args = parser.parse_args()

    start_time = time.time()
    logger.info("=" * 70)
    logger.info("Bangladesh Flood Exposure and Healthcare Facility Proximity Analysis")
    logger.info("Case Study: Cumilla District, August 2024 (GLIDE: FL20240825BGD)")
    logger.info("=" * 70)

    # 1. Configuration
    config = load_config(args.config)
    logger.info("Loaded configuration from %s", args.config)

    # 2. Authentic Data Acquisition
    if not args.skip_download:
        logger.info("\n--- STEP 1/5: AUTHENTIC DATA ACQUISITION ---")
        run_data_acquisition(config)
    else:
        logger.info("\n--- STEP 1/5: SKIPPING DOWNLOAD (Using cached data) ---")

    # 3. Geospatial Preprocessing & Clipping
    logger.info("\n--- STEP 2/5: GEOSPATIAL PREPROCESSING & MULTI-PERIOD EXTRACTION ---")
    boundary_utm, flood_layers_utm, healthcare_utm, flood_metadata = run_preprocessing(config)

    # 4. Spatial Analysis & Metric Computation
    logger.info("\n--- STEP 3/5: SPATIAL ANALYSIS & PROXIMITY METRICS ---")
    results_df, summary_stats = run_spatial_analysis(
        boundary_utm, flood_layers_utm, healthcare_utm, config, flood_metadata=flood_metadata
    )

    # 5. Visualization Generation
    logger.info("\n--- STEP 4/5: MAP GENERATION (STATIC & INTERACTIVE) ---")
    flood_primary_utm = (
        flood_layers_utm.get("period_1", next(iter(flood_layers_utm.values())))
        if isinstance(flood_layers_utm, dict)
        else flood_layers_utm
    )
    generate_static_maps(
        boundary_utm, flood_primary_utm, healthcare_utm, results_df, summary_stats, config
    )

    # Load geographic layers for Folium interactive map
    proc_dir = Path(config["paths"]["processed_dir"])
    boundary_geo = gpd.read_file(proc_dir / "cumilla_boundary_wgs84.geojson")
    flood_geo = gpd.read_file(proc_dir / "cumilla_flood_wgs84.geojson")
    healthcare_geo = gpd.read_file(proc_dir / "cumilla_healthcare_wgs84.geojson")

    generate_interactive_map(
        boundary_geo, flood_geo, healthcare_geo, results_df, summary_stats, config
    )

    # 6. Research Report Synthesis
    logger.info("\n--- STEP 5/5: RESEARCH REPORT SYNTHESIS ---")
    report_path = generate_research_report(summary_stats, results_df, config)

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY IN %.2f SECONDS!", elapsed)
    logger.info("Outputs Generated:")
    logger.info("  - Static Figures:    outputs/figures/")
    logger.info("  - Interactive Map:   outputs/interactive_map.html")
    logger.info("  - Facility Results:  outputs/results.csv")
    logger.info("  - Summary Metrics:   outputs/summary.json")
    logger.info("  - Research Report:   %s", report_path)
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.critical("Fatal error during pipeline execution: %s", exc, exc_info=True)
        sys.exit(1)
