"""
Visualization Module for Bangladesh Flood Exposure Analysis.

Generates:
1. Publication-style static maps (PNG and PDF):
   - Map 1: Satellite-Derived Flood Extent (Cumilla District)
   - Map 2: Flood Extent and Mapped Healthcare Facilities
   - Map 3: Healthcare Facility Proximity to Floodwaters
2. Interactive Folium Web Map (HTML):
   - Multi-layer controls (Boundary, Flood Polygons, Healthcare Points)
   - Styled popups with distance metrics
   - Floating HTML/CSS legend
   - Basemap selector (CartoDB, OpenStreetMap, ESRI Imagery)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import folium
from folium import Element, FeatureGroup, LayerControl
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def add_scale_bar(ax, length_km=10):
    """Draw a clean publication-quality metric scale bar in projected units (meters)."""
    # Get current plot bounds in meters
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    dx = xlim[1] - xlim[0]
    dy = ylim[1] - ylim[0]

    # Position at lower left
    x0 = xlim[0] + 0.06 * dx
    y0 = ylim[0] + 0.06 * dy
    length_m = length_km * 1000.0

    # Background box
    box_w = length_m * 1.3
    box_h = 0.045 * dy
    ax.add_patch(
        mpatches.Rectangle(
            (x0 - 0.1 * length_m, y0 - 0.015 * dy),
            box_w,
            box_h,
            facecolor="white",
            edgecolor="#adb5bd",
            linewidth=0.8,
            alpha=0.9,
            zorder=10,
        )
    )

    # Scale bar rectangle
    ax.add_patch(
        mpatches.Rectangle(
            (x0, y0),
            length_m,
            0.01 * dy,
            facecolor="#212529",
            edgecolor="#212529",
            zorder=11,
        )
    )

    # Scale text
    ax.text(
        x0 + length_m / 2.0,
        y0 + 0.013 * dy,
        f"{length_km} km",
        ha="center",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
        color="#212529",
        zorder=12,
    )
    # 0 and 10 labels
    ax.text(x0, y0 - 0.003 * dy, "0", ha="center", va="top", fontsize=7, color="#495057", zorder=12)
    ax.text(x0 + length_m, y0 - 0.003 * dy, f"{length_km}", ha="center", va="top", fontsize=7, color="#495057", zorder=12)


def add_north_arrow(ax):
    """Draw a discrete North arrow at the upper-left of the map."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x = xlim[0] + 0.07 * (xlim[1] - xlim[0])
    y = ylim[1] - 0.08 * (ylim[1] - ylim[0])
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - 0.05 * (ylim[1] - ylim[0])),
        arrowprops=dict(facecolor="#212529", edgecolor="#212529", width=2.5, headwidth=7),
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        color="#212529",
        zorder=15,
    )



def generate_static_maps(
    boundary_utm: gpd.GeoDataFrame,
    flood_utm: gpd.GeoDataFrame,
    healthcare_utm: gpd.GeoDataFrame,
    results_df: pd.DataFrame,
    summary_stats: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Path]:
    """Generate high-resolution publication-quality maps (300 DPI PNG and vector PDF)."""
    fig_dir = Path(config["paths"]["figures_dir"])
    fig_dir.mkdir(parents=True, exist_ok=True)
    generated = {}

    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # -------------------------------------------------------------
    # MAP 1: 2024 Satellite-Derived Flood Extent in Cumilla District
    # -------------------------------------------------------------
    logger.info("Rendering Map 1: Satellite-Derived Flood Extent...")
    fig, ax = plt.subplots(figsize=(10, 11), dpi=300)

    # Plot Boundary
    boundary_utm.plot(
        ax=ax,
        facecolor="#f8f9fa",
        edgecolor="#212529",
        linewidth=1.6,
        linestyle="-",
        zorder=1,
    )

    # Plot Flood Polygons
    if not flood_utm.empty:
        flood_utm.plot(
            ax=ax,
            facecolor="#0077b6",
            edgecolor="#023e8a",
            linewidth=0.3,
            alpha=0.85,
            zorder=2,
        )

    flood_km2 = summary_stats["flood_metrics"]["satellite_detected_flood_area_km2"]
    flood_pct = summary_stats["flood_metrics"]["percentage_of_district_flooded"]
    total_km2 = summary_stats["district_metrics"]["total_area_km2"]

    ax.set_title(
        "Satellite-Derived Flood Water Extent: Cumilla District, Bangladesh\n"
        "First Satellite Observation Period: 18–26 August 2024 (Copernicus Sentinel-1 SAR)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("UTM Easting (meters) — WGS 84 / UTM Zone 46N (EPSG:32646)", fontsize=9)
    ax.set_ylabel("UTM Northing (meters)", fontsize=9)
    ax.tick_params(labelsize=8)

    # Legend
    district_patch = mpatches.Patch(
        facecolor="#f8f9fa", edgecolor="#212529", linewidth=1.2, label=f"Cumilla District ({total_km2:,.1f} km²)"
    )
    flood_patch = mpatches.Patch(
        facecolor="#0077b6", edgecolor="#023e8a", label=f"Detected Water Extent ({flood_km2:,.1f} km², {flood_pct:.1f}%)"
    )
    ax.legend(handles=[district_patch, flood_patch], loc="upper right", frameon=True, fontsize=9)

    # North arrow & Scale bar
    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)

    # Attribution & Disclaimer note
    meta_text = (
        "Data Sources: UNOSAT (Product 3954, Sentinel-1 SAR), geoBoundaries ADM2 (BBS / OCHA ROAP)\n"
        "Observation Period Displayed: 18–26 August 2024 (First Observation Period, Peak Extent: 472.16 km²)\n"
        "Comparative Window: 28 August–04 September 2024 (Second Observation Period: 453.54 km²)\n"
        "Sensor Limitation: SAR radar analysis may underestimate water under dense tree canopy and in built-up urban cores."
    )
    fig.text(0.5, 0.02, meta_text, ha="center", fontsize=7.5, color="#495057", style="italic")

    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    map1_png = fig_dir / "map1_flood_extent_cumilla.png"
    map1_pdf = fig_dir / "map1_flood_extent_cumilla.pdf"
    fig.savefig(map1_png, dpi=300)
    fig.savefig(map1_pdf)
    plt.close(fig)
    generated["map1_png"] = map1_png
    generated["map1_pdf"] = map1_pdf

    # -------------------------------------------------------------
    # MAP 2: Flood Extent and Mapped Healthcare Facilities
    # -------------------------------------------------------------
    logger.info("Rendering Map 2: Flood Extent and Healthcare Facilities...")
    fig, ax = plt.subplots(figsize=(10, 11), dpi=300)

    boundary_utm.plot(
        ax=ax,
        facecolor="#fcfcfc",
        edgecolor="#343a40",
        linewidth=1.4,
        zorder=1,
    )

    if not flood_utm.empty:
        flood_utm.plot(
            ax=ax,
            facecolor="#90e0ef",
            edgecolor="#0077b6",
            linewidth=0.3,
            alpha=0.75,
            zorder=2,
        )

    # Plot Healthcare facilities
    facilities_plot = healthcare_utm.copy()
    facilities_plot["in_flood_extent"] = results_df["in_flood_extent"].values
    facilities_plot["proximity_band"] = results_df["proximity_band"].values

    flooded_fac = facilities_plot[facilities_plot["in_flood_extent"]]
    non_flooded_fac = facilities_plot[~facilities_plot["in_flood_extent"]]

    if not non_flooded_fac.empty:
        non_flooded_fac.plot(
            ax=ax,
            color="#2a9d8f",
            edgecolor="#ffffff",
            linewidth=0.6,
            markersize=35,
            alpha=0.9,
            zorder=4,
        )

    if not flooded_fac.empty:
        flooded_fac.plot(
            ax=ax,
            color="#e63946",
            edgecolor="#ffffff",
            linewidth=0.8,
            markersize=50,
            marker="^",
            zorder=5,
        )

    total_h = len(facilities_plot)
    flooded_h = len(flooded_fac)

    ax.set_title(
        "Healthcare Facilities and Flood Extent: Cumilla District, Bangladesh\n"
        "First Satellite Observation Period: 18–26 August 2024 (Spatial Exposure)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("UTM Easting (meters) — EPSG:32646", fontsize=9)
    ax.set_ylabel("UTM Northing (meters)", fontsize=9)
    ax.tick_params(labelsize=8)

    legend_elements = [
        mpatches.Patch(facecolor="#90e0ef", edgecolor="#0077b6", label="Satellite Flood Extent (18–26 Aug)"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#2a9d8f", markersize=7, label=f"Outside Flood Extent ({total_h - flooded_h})"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#e63946", markersize=8, label=f"Intersecting Flood Extent ({flooded_h})"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", frameon=True, fontsize=9)

    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)

    meta_text_2 = (
        "Sources: UNOSAT (Product 3954, Period 1: 18–26 Aug 2024), OpenStreetMap Healthcare, geoBoundaries ADM2\n"
        "Observation Period Displayed: 18–26 August 2024 (First Observation Period)\n"
        "Important Note: OpenStreetMap records represent mapped spatial facilities, not field-verified operational capacity.\n"
        "Facility exposure denotes spatial intersection with 10m radar-derived water extent, not verified structural damage."
    )
    fig.text(0.5, 0.02, meta_text_2, ha="center", fontsize=7.5, color="#495057", style="italic")

    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    map2_png = fig_dir / "map2_flood_and_healthcare_cumilla.png"
    map2_pdf = fig_dir / "map2_flood_and_healthcare_cumilla.pdf"
    fig.savefig(map2_png, dpi=300)
    fig.savefig(map2_pdf)
    plt.close(fig)
    generated["map2_png"] = map2_png
    generated["map2_pdf"] = map2_pdf

    # -------------------------------------------------------------
    # MAP 3: Exploratory Geographic Proximity to Floodwaters
    # -------------------------------------------------------------
    logger.info("Rendering Map 3: Proximity Analysis...")
    fig, ax = plt.subplots(figsize=(10, 11), dpi=300)

    boundary_utm.plot(
        ax=ax,
        facecolor="#f8f9fa",
        edgecolor="#495057",
        linewidth=1.2,
        zorder=1,
    )

    if not flood_utm.empty:
        # Buffer zones around flood extent for visual context (500m and 1000m)
        # Filter micro-speckle (<1000m²) and simplify slightly before buffering to accelerate calculation
        major_flood = flood_utm[flood_utm.geometry.area >= 1000]
        if major_flood.empty:
            major_flood = flood_utm
        simplified_union = major_flood.geometry.simplify(25).union_all()

        b1000 = gpd.GeoSeries([simplified_union.buffer(1000, resolution=4)], crs=boundary_utm.crs)
        b500 = gpd.GeoSeries([simplified_union.buffer(500, resolution=4)], crs=boundary_utm.crs)

        b1000.plot(ax=ax, facecolor="#caf0f8", edgecolor="none", alpha=0.45, zorder=2)
        b500.plot(ax=ax, facecolor="#ade8f4", edgecolor="none", alpha=0.55, zorder=3)
        flood_utm.plot(ax=ax, facecolor="#0077b6", edgecolor="#03045e", linewidth=0.2, alpha=0.85, zorder=4)

    # Color healthcare facilities by proximity band
    band_colors = {
        "Inside Flood Extent": "#d90429",
        "Within 500m": "#f77f00",
        "500m - 1km": "#fcbf49",
        "1km - 2.5km": "#2a9d8f",
        "2.5km - 5km": "#457b9d",
        "> 5km": "#1d3557",
    }

    for band, color in band_colors.items():
        subset = facilities_plot[facilities_plot["proximity_band"] == band]
        if not subset.empty:
            subset.plot(
                ax=ax,
                color=color,
                edgecolor="#ffffff",
                linewidth=0.5,
                markersize=36,
                zorder=6,
            )

    ax.set_title(
        "Exploratory Geographic Proximity: Healthcare Facilities to Floodwaters\n"
        "Cumilla District, Bangladesh — First Satellite Observation Period: 18–26 August 2024",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel("UTM Easting (meters) — EPSG:32646", fontsize=9)
    ax.set_ylabel("UTM Northing (meters)", fontsize=9)
    ax.tick_params(labelsize=8)

    prox_legend = [
        mpatches.Patch(facecolor="#0077b6", label="Detected Flood Extent (18–26 Aug)"),
        mpatches.Patch(facecolor="#ade8f4", alpha=0.6, label="500m Flood Buffer"),
        mpatches.Patch(facecolor="#caf0f8", alpha=0.5, label="1,000m Flood Buffer"),
    ]
    for band, color in band_colors.items():
        count = (facilities_plot["proximity_band"] == band).sum()
        if count > 0:
            prox_legend.append(
                plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=7, label=f"{band} (n={count})")
            )

    ax.legend(handles=prox_legend, loc="upper right", frameon=True, fontsize=8.5)

    add_north_arrow(ax)
    add_scale_bar(ax, length_km=10)

    meta_text_3 = (
        "Observation Period Displayed: 18–26 August 2024 (First Observation Period, Copernicus Sentinel-1 SAR)\n"
        "Metric: Euclidean straight-line distance (m) to nearest UNOSAT flood polygon in UTM Zone 46N (EPSG:32646).\n"
        "Cartographic Note: 500m & 1,000m buffer rings are visually generalized for display; metrics use exact analytical geometries.\n"
        "Methodological Limitation: Euclidean distance does not capture road network severance, bridge washouts, or travel accessibility."
    )
    fig.text(0.5, 0.02, meta_text_3, ha="center", fontsize=7.5, color="#495057", style="italic")

    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    map3_png = fig_dir / "map3_healthcare_proximity_cumilla.png"
    map3_pdf = fig_dir / "map3_healthcare_proximity_cumilla.pdf"
    fig.savefig(map3_png, dpi=300)
    fig.savefig(map3_pdf)
    plt.close(fig)
    generated["map3_png"] = map3_png
    generated["map3_pdf"] = map3_pdf

    logger.info("Successfully generated all static publication maps in %s", fig_dir)
    return generated


def generate_interactive_map(
    boundary_geo: gpd.GeoDataFrame,
    flood_geo: gpd.GeoDataFrame,
    healthcare_geo: gpd.GeoDataFrame,
    results_df: pd.DataFrame,
    summary_stats: Dict[str, Any],
    config: Dict[str, Any],
) -> Path:
    """Generate an interactive Folium map with layers, legend, tooltips, and popups."""
    logger.info("Generating interactive Folium web map...")
    out_path = Path(config["paths"]["outputs_dir"]) / "interactive_map.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute center of Cumilla District
    bounds = boundary_geo.total_bounds  # minx, miny, maxx, maxy
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0

    # Initialize Folium Map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles=None,
        control_scale=True,
    )

    # Add Basemaps
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        name="CartoDB Positron (Light)",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap Standard",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics, CNES/Airbus DS, USDA FSA, USGS, Aerogrid, IGN, IGP, and the GIS User Community",
        name="Esri World Imagery (Satellite)",
        overlay=False,
        control=True,
    ).add_to(m)

    # 1. District Boundary Layer
    boundary_fg = FeatureGroup(name="Cumilla District Boundary", show=True)
    boundary_display = boundary_geo.copy()
    # Ensure all attribute columns are JSON-serializable strings
    for col in boundary_display.columns:
        if col != "geometry":
            boundary_display[col] = boundary_display[col].astype(str)

    folium.GeoJson(
        boundary_display.to_json(),
        style_function=lambda x: {
            "fillColor": "transparent",
            "color": "#1f2937",
            "weight": 2.5,
            "opacity": 0.9,
            "dashArray": "4, 4",
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["shapeName" if "shapeName" in boundary_display.columns else list(boundary_display.columns)[0]],
            aliases=["Administrative Area:"],
            style="font-family: sans-serif; font-size: 12px;",
        ),
    ).add_to(boundary_fg)
    boundary_fg.add_to(m)

    # 2. Flood Extent Layer
    flood_fg = FeatureGroup(name="UNOSAT Flood Water Extent (Aug 2024)", show=True)
    if not flood_geo.empty:
        # Simplify geometry and isolate geometry column to prevent Timestamp serialization issues
        simplified_flood = gpd.GeoDataFrame(
            geometry=flood_geo.geometry.simplify(0.0008),
            crs=flood_geo.crs,
        )
        simplified_flood = simplified_flood[
            ~simplified_flood.geometry.is_empty & simplified_flood.geometry.is_valid
        ].copy()

        folium.GeoJson(
            simplified_flood.to_json(),
            style_function=lambda x: {
                "fillColor": "#0284c7",
                "color": "#0369a1",
                "weight": 1.0,
                "fillOpacity": 0.65,
            },
            tooltip="Satellite Detected Flood Water (UNOSAT / Sentinel-1 SAR)",
        ).add_to(flood_fg)
    flood_fg.add_to(m)

    # 3. Healthcare Facilities Layer
    healthcare_fg = FeatureGroup(name="Mapped Healthcare Facilities (OSM)", show=True)

    # Marker styling based on proximity
    def get_marker_color(in_flood: bool, dist_m: float) -> str:
        if in_flood or dist_m == 0:
            return "#ef4444"  # Red
        elif dist_m <= 500:
            return "#f97316"  # Orange
        elif dist_m <= 1000:
            return "#eab308"  # Yellow
        elif dist_m <= 2500:
            return "#14b8a6"  # Teal
        else:
            return "#10b981"  # Emerald Green

    for idx, row in results_df.iterrows():
        lat = row["latitude"]
        lon = row["longitude"]
        name = row["facility_name"]
        amenity = row["amenity_type"].capitalize()
        dist_m = row["distance_to_flood_m"]
        in_flood = row["in_flood_extent"]
        band = row["proximity_band"]
        osm_id = row.get("osm_id", "N/A")

        color = get_marker_color(in_flood, dist_m)

        status_badge = (
            "<span style='color: white; background-color: #ef4444; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>SPATIALLY INUNDATED</span>"
            if in_flood
            else f"<span style='color: white; background-color: {color}; padding: 2px 6px; border-radius: 4px;'>{band}</span>"
        )

        popup_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 13px; line-height: 1.5; width: 260px;">
            <h4 style="margin: 0 0 8px 0; color: #111827; border-bottom: 2px solid {color}; padding-bottom: 4px;">{name}</h4>
            <div style="margin-bottom: 6px;">{status_badge}</div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr><td style="color: #6b7280; padding: 2px 0;">Facility Type:</td><td style="font-weight: 500;">{amenity}</td></tr>
                <tr><td style="color: #6b7280; padding: 2px 0;">Distance to Flood:</td><td style="font-weight: 600; color: {color};">{dist_m:,.1f} m</td></tr>
                <tr><td style="color: #6b7280; padding: 2px 0;">OSM ID:</td><td><code>{osm_id}</code></td></tr>
                <tr><td style="color: #6b7280; padding: 2px 0;">Coordinates:</td><td>{lat:.4f}° N, {lon:.4f}° E</td></tr>
            </table>
            <div style="margin-top: 8px; font-size: 10.5px; color: #9ca3af; font-style: italic;">
                Note: Euclidean distance in EPSG:32646. Does not reflect road travel feasibility.
            </div>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="#ffffff",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=f"<b>{name}</b> ({amenity}) — {band} ({dist_m:,.0f}m)",
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(healthcare_fg)

    healthcare_fg.add_to(m)

    # Layer Controls
    LayerControl(collapsed=False).add_to(m)

    # Custom HTML Legend and Info Box
    total_fac = len(results_df)
    flooded_fac = int(results_df["in_flood_extent"].sum())
    flood_km2 = summary_stats["flood_metrics"]["satellite_detected_flood_area_km2"]
    flood_pct = summary_stats["flood_metrics"]["percentage_of_district_flooded"]

    legend_html = f"""
    <div style="position: fixed; 
                bottom: 25px; left: 25px; width: 320px; height: auto; 
                background: rgba(255, 255, 255, 0.95); 
                backdrop-filter: blur(8px);
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
                z-index: 9999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                font-size: 12px;
                padding: 12px 14px;
                line-height: 1.4;">
        <h4 style="margin: 0 0 6px 0; font-size: 13.5px; font-weight: 700; color: #111827;">
            Cumilla Flood Exposure Analysis
        </h4>
        <div style="font-size: 11px; color: #6b7280; margin-bottom: 8px;">
            August 2024 Floods (Copernicus Sentinel-1 SAR)
        </div>
        
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #f3f4f6;">
            <div><i style="background: #0284c7; width: 14px; height: 10px; display: inline-block; margin-right: 6px; border-radius: 2px;"></i>
                 <b>Flood Waters:</b> {flood_km2:,.1f} km² ({flood_pct:.1f}%)</div>
            <div><i style="border: 2px dashed #1f2937; width: 14px; height: 0px; display: inline-block; margin-right: 6px;"></i>
                 <b>District Boundary:</b> geoBoundaries ADM2</div>
        </div>

        <div style="font-weight: 600; color: #374151; margin-bottom: 4px;">Healthcare Facilities Proximity:</div>
        <div style="display: grid; grid-template-columns: 1fr; gap: 3px; font-size: 11.5px;">
            <div><span style="background: #ef4444; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                 Inside Flood Extent ({flooded_fac})</div>
            <div><span style="background: #f97316; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                 Within 500m ({(results_df['proximity_band'] == 'Within 500m').sum()})</div>
            <div><span style="background: #eab308; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                 500m - 1km ({(results_df['proximity_band'] == '500m - 1km').sum()})</div>
            <div><span style="background: #14b8a6; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                 1km - 2.5km ({(results_df['proximity_band'] == '1km - 2.5km').sum()})</div>
            <div><span style="background: #10b981; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                 > 2.5km ({(results_df['proximity_band'].isin(['2.5km - 5km', '> 5km'])).sum()})</div>
        </div>

        <div style="margin-top: 8px; font-size: 9.5px; color: #6b7280; border-top: 1px solid #f3f4f6; padding-top: 6px;">
            <b>Sources:</b> UNOSAT Product 3954, OpenStreetMap, geoBoundaries.<br/>
            <i>Disclaimer: Distances are Euclidean metric (EPSG:32646). Flood extent derived from SAR radar; may underestimate water under canopy.</i>
        </div>
    </div>
    """
    m.get_root().html.add_child(Element(legend_html))

    m.save(str(out_path))
    logger.info("Saved interactive web map to %s", out_path)
    return out_path
