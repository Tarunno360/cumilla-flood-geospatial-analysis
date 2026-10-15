"""
Data Acquisition Module for Bangladesh Flood Exposure Analysis.

Retrieves authentic public geographic data from:
1. geoBoundaries (Bangladesh ADM2 District Boundaries)
2. UNOSAT Product 3954 (Sentinel-1 SAR Satellite Detected Water Extents)
3. UNOSAT Product 3937 (Cumilla City Flood Impact Assessment Context)
4. OpenStreetMap via Overpass API (Healthcare facilities in Cumilla District)
"""

import json
import logging
import os
import shutil
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def download_file_with_retry(
    url: str,
    dest_path: Path,
    expected_min_bytes: int = 100,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    headers: Optional[Dict[str, str]] = None,
) -> Path:
    """Download a file with exponential backoff and size validation."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and dest_path.stat().st_size >= expected_min_bytes:
        logger.info(
            "Cached file found at %s (%d bytes). Skipping download.",
            dest_path,
            dest_path.stat().st_size,
        )
        return dest_path

    request_headers = {
        "User-Agent": (
            "GeotechFloodAnalysis/1.0 (Research Portfolio; "
            "Erasmus Mundus Geospatial Technologies Application; academic research)"
        )
    }
    if headers:
        request_headers.update(headers)

    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Downloading %s (Attempt %d/%d)...", url, attempt, max_retries)
            with requests.get(
                url, stream=True, headers=request_headers, timeout=120
            ) as response:
                response.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            file_size = tmp_path.stat().st_size
            if file_size < expected_min_bytes:
                raise ValueError(
                    f"Downloaded file too small ({file_size} bytes < {expected_min_bytes} bytes)"
                )

            # Atomic move
            shutil.move(tmp_path, dest_path)
            logger.info("Successfully downloaded %s (%d bytes).", dest_path, file_size)
            return dest_path

        except Exception as exc:
            logger.warning("Attempt %d failed for %s: %s", attempt, url, exc)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            if attempt == max_retries:
                raise RuntimeError(
                    f"Failed to download {url} after {max_retries} attempts."
                ) from exc
            sleep_time = backoff_factor**attempt
            time.sleep(sleep_time)

    return dest_path


def download_geoboundaries(config: Dict[str, Any]) -> Path:
    """Download geoBoundaries Bangladesh ADM2 GeoJSON."""
    cfg = config["data_sources"]["geoboundaries"]
    dest_path = Path(cfg["local_file"])
    url = cfg["url"]
    return download_file_with_retry(url, dest_path, expected_min_bytes=500_000)


def download_unosat_flood_extent(config: Dict[str, Any]) -> Path:
    """Download and extract UNOSAT Product 3954 Flood Extent Shapefile."""
    cfg = config["data_sources"]["unosat_flood"]
    zip_path = Path(cfg["local_zip"])
    extract_dir = Path(cfg["extract_dir"])
    url = cfg["url"]

    download_file_with_retry(url, zip_path, expected_min_bytes=10_000_000)

    # Check whether both explicitly configured period shapefiles exist before re-extracting
    periods_cfg = cfg.get("observation_periods", {})
    all_periods_exist = True
    if periods_cfg:
        for p_key, p_info in periods_cfg.items():
            rel_path = p_info.get("relative_path")
            shp_name = p_info.get("shapefile_name")
            p_file = (extract_dir / rel_path) if rel_path else None
            if not p_file or not p_file.exists():
                matched = list(extract_dir.rglob(shp_name)) if (shp_name and extract_dir.exists()) else []
                if not matched:
                    all_periods_exist = False
                    break
    else:
        all_periods_exist = bool(list(extract_dir.rglob("*.shp"))) if extract_dir.exists() else False

    if not all_periods_exist:
        logger.info("Extracting UNOSAT flood shapefile archive to %s...", extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        extracted_shps = list(extract_dir.rglob("*.shp"))
        logger.info("Extracted %d shapefiles from archive into %s.", len(extracted_shps), extract_dir)
    else:
        logger.info(
            "Verified all configured UNOSAT shapefiles already extracted in %s. Skipping re-extraction.",
            extract_dir,
        )

    return extract_dir


def download_unosat_assessment_context(config: Dict[str, Any]) -> Path:
    """Download UNOSAT Product 3937 Cumilla Assessment PDF for contextual reference."""
    cfg = config["data_sources"]["unosat_assessment"]
    dest_path = Path(cfg["local_pdf"])
    url = cfg["url"]
    return download_file_with_retry(url, dest_path, expected_min_bytes=100_000)


def download_osm_healthcare(
    config: Dict[str, Any], bbox: Optional[list] = None
) -> Path:
    """
    Fetch mapped healthcare facilities (hospitals, clinics, doctors) in study area from Overpass API.
    Saves authentic OSM results as GeoJSON.
    """
    cfg = config["data_sources"]["osm_healthcare"]
    dest_path = Path(cfg["local_geojson"])
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and dest_path.stat().st_size >= 2000:
        logger.info(
            "Cached OSM healthcare facilities found at %s (%d bytes). Skipping download.",
            dest_path,
            dest_path.stat().st_size,
        )
        return dest_path

    # Cumilla District bounding box: South, West, North, East
    # Approximate bounds: 23.0N to 23.85N, 90.6E to 91.4E
    s, w, n, e = bbox if bbox else (23.0, 90.6, 23.85, 91.4)
    amenities = "|".join(cfg.get("amenity_tags", ["hospital", "clinic", "doctors"]))

    overpass_query = f"""[out:json][timeout:60];
(
  node["amenity"~"{amenities}"]({s},{w},{n},{e});
  way["amenity"~"{amenities}"]({s},{w},{n},{e});
  relation["amenity"~"{amenities}"]({s},{w},{n},{e});
  node["healthcare"]({s},{w},{n},{e});
  way["healthcare"]({s},{w},{n},{e});
);
out center tags;
"""

    endpoints = cfg.get(
        "endpoints",
        [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        ],
    )

    headers = {
        "User-Agent": (
            "GeotechFloodAnalysis/1.0 (Research Portfolio; "
            "Erasmus Mundus Geospatial Technologies Application; academic research)"
        )
    }

    last_error = None
    data = None
    for endpoint in endpoints:
        try:
            logger.info("Querying Overpass API at %s for healthcare facilities...", endpoint)
            resp = requests.post(
                endpoint,
                data={"data": overpass_query},
                headers=headers,
                timeout=25,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "elements" in data and len(data["elements"]) > 0:
                    logger.info(
                        "Overpass API returned %d raw elements from %s.",
                        len(data["elements"]),
                        endpoint,
                    )
                    break
            else:
                logger.warning("Overpass endpoint %s returned status %d", endpoint, resp.status_code)
        except Exception as exc:
            logger.warning("Overpass endpoint %s failed: %s", endpoint, exc)
            last_error = exc

    # If Overpass is completely down, use official Humanitarian OpenStreetMap Team (HOT) export
    if not data or "elements" not in data or len(data["elements"]) == 0:
        logger.warning(
            "Overpass API endpoints unavailable or rate-limited. Falling back to Humanitarian OpenStreetMap Team (HOT) BGD dataset..."
        )
        hot_url = cfg.get(
            "hot_osm_url",
            "https://production-raw-data-api.s3.amazonaws.com/ISO3/BGD/health_facilities/hotosm_bgd_health_facilities_osm_geojson.zip",
        )
        hot_zip_path = dest_path.parent / "hotosm_bgd_health_facilities.zip"
        download_file_with_retry(hot_url, hot_zip_path, expected_min_bytes=100_000)

        # Extract GeoJSON from HOT archive
        with zipfile.ZipFile(hot_zip_path, "r") as z:
            # Look for points geojson
            gj_names = [n for n in z.namelist() if n.endswith(".geojson") and "point" in n.lower()]
            if not gj_names:
                gj_names = [n for n in z.namelist() if n.endswith(".geojson")]
            if not gj_names:
                raise RuntimeError("No GeoJSON found in HOT OSM health facilities archive.")
            target_name = gj_names[0]
            with z.open(target_name) as zf, open(dest_path, "wb") as out_f:
                out_f.write(zf.read())
        logger.info("Extracted HOT OSM health facilities to %s", dest_path)
        return dest_path

    # Convert Overpass elements to standard GeoJSON FeatureCollection
    features = []
    for el in data["elements"]:
        tags = el.get("tags", {})
        el_type = el.get("type")
        el_id = el.get("id")

        if el_type == "node":
            lon = el.get("lon")
            lat = el.get("lat")
        else:
            center = el.get("center", {})
            lon = center.get("lon")
            lat = center.get("lat")

        if lon is None or lat is None:
            continue

        props = dict(tags)
        props["osm_id"] = f"{el_type}/{el_id}"
        props["osm_type"] = el_type
        props["name"] = tags.get("name", tags.get("name:en", "Unnamed Facility"))
        props["amenity"] = tags.get("amenity", tags.get("healthcare", "healthcare"))

        feature = {
            "type": "Feature",
            "id": f"{el_type}_{el_id}",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": props,
        }
        features.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "features": features,
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "metadata": {
            "retrieval_date": datetime.now(timezone.utc).isoformat(),
            "source": "OpenStreetMap contributors via Overpass API",
            "license": "Open Database License (ODbL) 1.0",
            "query_bbox": [s, w, n, e],
            "feature_count": len(features),
            "historical_note": (
                "NOTE: Current OpenStreetMap records represent mapped facilities and "
                "are not guaranteed historical snapshots as of August 2024."
            ),
        },
    }

    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2, ensure_ascii=False)

    logger.info(
        "Successfully wrote %d healthcare features to %s", len(features), dest_path
    )
    return dest_path


def create_source_data_manifest(
    config: Dict[str, Any], output_path: Optional[Path] = None
) -> Path:
    """
    Generate a machine-readable data provenance manifest recording source URLs,
    licensing, retrieval dates, and analytical roles.
    """
    manifest_path = (
        Path(output_path)
        if output_path
        else Path(config["paths"]["manifest_path"])
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    unosat_flood_cfg = config["data_sources"]["unosat_flood"]
    obs_periods_cfg = unosat_flood_cfg.get("observation_periods", {})
    obs_periods_manifest = {}
    for p_k, p_v in obs_periods_cfg.items():
        obs_periods_manifest[p_k] = {
            "id": p_v.get("id", p_k),
            "name": p_v.get("name"),
            "date_range": p_v.get("date_range"),
            "shapefile_name": p_v.get("shapefile_name"),
            "relative_path": p_v.get("relative_path"),
            "is_primary": p_v.get("is_primary", False),
            "description": p_v.get("description"),
        }

    manifest = {
        "project": config["project"]["title"],
        "manifest_generated_at": datetime.now(timezone.utc).isoformat(),
        "study_area": config["project"]["study_area"],
        "target_event": {
            "title": "August 2024 Eastern Bangladesh Floods",
            "glide_number": config["project"]["event_glide"],
            "dates": config["project"]["event_dates"],
        },
        "datasets": [
            {
                "identifier": "geoboundaries_bgd_adm2",
                "title": "geoBoundaries Bangladesh ADM2 (Districts)",
                "provider": "William & Mary geoBoundaries / BBS / OCHA ROAP",
                "source_url": config["data_sources"]["geoboundaries"]["url"],
                "license": config["data_sources"]["geoboundaries"]["license"],
                "vintage": config["data_sources"]["geoboundaries"]["vintage"],
                "native_crs": "EPSG:4326 (WGS84)",
                "local_path": config["data_sources"]["geoboundaries"]["local_file"],
                "role": "Delineation of Cumilla District administrative boundary.",
            },
            {
                "identifier": "unosat_product_3954",
                "title": unosat_flood_cfg["title"],
                "provider": "United Nations Satellite Centre (UNOSAT / UNITAR)",
                "product_id": unosat_flood_cfg["product_id"],
                "source_url": unosat_flood_cfg["url"],
                "metadata_page": unosat_flood_cfg["metadata_url"],
                "sensor": unosat_flood_cfg["sensor"],
                "primary_period": unosat_flood_cfg.get("primary_period", "period_1"),
                "observation_periods": obs_periods_manifest,
                "license": unosat_flood_cfg["license"],
                "native_crs": "EPSG:4326 (WGS84) / UTM",
                "local_path": unosat_flood_cfg["extract_dir"],
                "role": "Satellite-derived flood water extents aggregated from Sentinel-1 radar observations across two discrete observation windows.",
            },
            {
                "identifier": "unosat_product_3937",
                "title": config["data_sources"]["unosat_assessment"]["title"],
                "provider": "United Nations Satellite Centre (UNOSAT / UNITAR)",
                "product_id": config["data_sources"]["unosat_assessment"]["product_id"],
                "source_url": config["data_sources"]["unosat_assessment"]["url"],
                "metadata_page": config["data_sources"]["unosat_assessment"]["metadata_url"],
                "license": "UNOSAT / UNITAR Assessment",
                "local_path": config["data_sources"]["unosat_assessment"]["local_pdf"],
                "role": "High-resolution satellite preliminary impact assessment context for Cumilla City.",
            },
            {
                "identifier": "osm_healthcare_facilities",
                "title": "OpenStreetMap Healthcare Facilities (Hospitals, Clinics, Doctors)",
                "provider": "OpenStreetMap contributors via Overpass API",
                "source_endpoints": config["data_sources"]["osm_healthcare"]["endpoints"],
                "license": config["data_sources"]["osm_healthcare"]["license"],
                "native_crs": "EPSG:4326 (WGS84)",
                "local_path": config["data_sources"]["osm_healthcare"]["local_geojson"],
                "role": "Point locations of mapped hospitals, medical clinics, and doctors in the study area.",
                "scientific_limitation": (
                    "OpenStreetMap data represents crowd-sourced facilities at query time "
                    "and does not constitute verified historical status as of August 2024. "
                    "Incomplete mapping in rural areas may lead to spatial sampling bias."
                ),
            },
        ],
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Source data manifest saved to %s", manifest_path)
    return manifest_path


def run_data_acquisition(config: Dict[str, Any]) -> Dict[str, Path]:
    """Execute the full data acquisition pipeline."""
    logger.info("Starting Phase 2: Authentic Data Acquisition...")
    paths = {}
    paths["geoboundaries"] = download_geoboundaries(config)
    paths["unosat_flood"] = download_unosat_flood_extent(config)
    paths["unosat_assessment"] = download_unosat_assessment_context(config)
    paths["osm_healthcare"] = download_osm_healthcare(config)
    paths["manifest"] = create_source_data_manifest(config)
    logger.info("Phase 2 Data Acquisition complete.")
    return paths


if __name__ == "__main__":
    import sys
    root_dir = Path(__file__).resolve().parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    import yaml

    config_path = root_dir / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        app_config = yaml.safe_load(f)
    run_data_acquisition(app_config)
