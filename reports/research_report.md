# Flood Exposure and Healthcare Facility Proximity Analysis
## An Exploratory Case Study of the August 2024 Bangladesh Floods in Cumilla District

**Author:** Azmain
**Role:** Associate Research Engineer | Applicant, Erasmus Mundus MSc in Geospatial Technologies
**Report Generated:** 2026-10-15 10:41:26 UTC
**Target Event:** 2024 Eastern Bangladesh Floods (GLIDE: `FL20240825BGD`)
**Study Boundary:** Cumilla District (Chattogram Division, Bangladesh)
**Project Repository:** [cumilla-flood-geospatial-analysis](https://github.com/Tarunno360/cumilla-flood-geospatial-analysis)

---

## Abstract

In late August 2024, extreme monsoon precipitation combined with transboundary river runoff in the Gumti River basin caused severe flooding across eastern Bangladesh, including Cumilla, Feni, and Noakhali districts. During humanitarian relief operations, locating inundated terrain and estimating how closely floodwaters encroached upon medical infrastructure was critical for logistical coordination. This research portfolio project implements an automated, reproducible Python GIS pipeline to analyze the spatial relationship between satellite-detected flood extents and mapped healthcare infrastructure across Cumilla District. Using Sentinel-1 Synthetic Aperture Radar (SAR) observations from the United Nations Satellite Centre (UNOSAT Product 3954), William & Mary geoBoundaries administrative boundaries (ADM2), and OpenStreetMap healthcare vectors, we quantify surface inundation and planar proximity within a projected metric coordinate reference system (WGS 84 / UTM Zone 46N, EPSG:32646). 

The primary analysis of the first satellite observation period (18–26 August 2024) reveals that **472.16 km²** (15.29%) of Cumilla District's **3,088.66 km²** territory was inundated. An independent evaluation of the second satellite observation period (28 August–04 September 2024) indicates a mapped water extent of **453.54 km²** (14.68%), representing a reduction of **18.62 km²** in mapped flood extent and confirming no cross-temporal aggregation in the primary metrics. Of the **86** mapped healthcare facilities in the district, none directly intersected the satellite flood extent, but **61** facilities (70.9%) were situated within 500 meters of detected floodwaters, and **81** (94.2%) were within 1,000 meters. Disaggregating by facility category reveals that **mapped hospitals and clinics** (N=64) exhibited a lower mean distance to floodwaters (mean distance 345.1 m; 78.1% within 500m) compared to commercial pharmacies and laboratories (N=19; mean distance 572.0 m; 47.4% within 500m). Crucially, this study emphasizes that straight-line proximity represents an exploratory geographic exposure metric and does not demonstrate actual population healthcare accessibility, which is dictated by road network travel impedance, infrastructure damage, and real-time operational status.

---

## 1. Background and Personal Motivation

During the August 2024 floods in Cumilla District, Bangladesh, I participated as a field volunteer helping supply emergency relief to water-trapped communities. In the field, navigating rural settlements was hindered by the difficulty of locating isolated homesteads submerged beneath dense tree canopy, alongside limited access to aerial drone technology for local reconnaissance. As a researcher with a background in Computer Science and Software Engineering, this experience motivated an exploration of how open satellite Earth observation (such as Copernicus Sentinel-1 Synthetic Aperture Radar) and open spatial infrastructure data can be systematically and reproducibly integrated to quantify flood extent and evaluate geometric proximity to mapped healthcare facilities.

---

## 2. Research Questions and Methodological Scope

### Core Distinction: Proximity vs. Accessibility
In geospatial disaster epidemiology, researchers must maintain a strict conceptual distinction between:
1. **Facility Proximity to Floodwaters:** The geometric distance from a fixed facility coordinate to the nearest boundary of a mapped inundation polygon.
2. **Geographic Accessibility of Populations:** The spatial impedance (travel distance, travel time, or cost-distance) separating vulnerable population clusters from care facilities under normal or flooded network conditions.
3. **Actual Disaster-Time Healthcare Accessibility:** The dynamic ability of patients to reach a functioning facility, accounting for road submergence, bridge failures, vehicle availability, flood water depth/velocity, and facility operational capacity.

This project focuses explicitly on **(1) Exploratory Flood Exposure and Facility Proximity Analysis**. It does **not** claim to measure population travel times, flood depth dynamics, or verified real-time facility operations.

### Primary Research Question
*How can open-access Sentinel-1 SAR satellite observations and open spatial datasets be integrated through an automated, reproducible GIS pipeline to quantify district-level flood extent and evaluate the physical proximity of mapped healthcare facilities to floodwaters in Cumilla District during the August 2024 event?*

### Specific Objectives
1. **Authentic Multi-Source Ingestion:** Acquire authentic spatial datasets from UNOSAT (Products 3954 and 3937), geoBoundaries (ADM2), and OpenStreetMap via Overpass API without synthetic substitutions.
2. **Explicit Multi-Period Processing:** Independently analyze both Sentinel-1 observation periods (Period 1: 18–26 August vs. Period 2: 28 August–04 September 2024) to avoid cross-temporal aggregation and dynamically compute temporal differences.
3. **Water Classification Rigor:** Verify UNOSAT attributes (`Water_Clas = 'Flood Water'`, `Water_Stat = 'New Water / Water Increase'`) to ensure that baseline/reference water bodies are not confounded with newly inundated land.
4. **Geodetic & Geometric Rigor:** Execute all spatial transformations in a projected metric coordinate system (**WGS 84 / UTM Zone 46N, EPSG:32646**), validate topology using `shapely.validation.make_valid`, and eliminate overlapping polygon double-counting via spatial union dissolving.
5. **Disaggregated Proximity Modeling:** Quantify planar Euclidean distances from healthcare facilities to flood perimeters, categorizing facilities into functional tiers (Hospitals/Clinics vs. Pharmacies/Labs vs. Other).
6. **Reproducible Dissemination:** Produce publication-ready static cartographic figures, an interactive multi-layer web map, a machine-readable provenance manifest, and a comprehensive automated test suite.

---

## 3. Study Area: Cumilla District

**Cumilla District** (historically Comilla) is located in southeastern Bangladesh within Chattogram Division, bordering the Indian state of Tripura to the east. The district lies between 23°02′N to 23°47′N latitude and 90°38′E to 91°22′E longitude, covering approximately 3,088.66 km².

The terrain is dominated by flat alluvial deltaic floodplains formed by the Gumti and Meghna river systems, flanked by the undulating red clay Lalmai Hills in the west-central portion. The Gumti River enters Cumilla from the Tripura hills and meanders westward across the district. In late August 2024, heavy rainfall in the upstream catchment combined with intense local monsoon precipitation triggered severe riverine flooding across agricultural fields, villages, and regional transport arteries in Cumilla District.

---

## 4. Authentic Data Sources and Provenance

Each dataset used in this analysis was retrieved from the documented public source. The pipeline checks configured administrative and sensor metadata where those fields are available.

| Dataset | Provider | Identifier / URL | License | Native CRS | Temporal Vintage / Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **District Boundary (ADM2)** | geoBoundaries / BBS / OCHA ROAP | [BGD-ADM2](https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/) | CC BY 3.0 IGO | EPSG:4326 | 2020 (Dec 2023 release) |
| **Satellite Flood Water Extent** | UNOSAT / UNITAR | [Product 3954](https://unosat.org/products/3954) | Open Access / UNOSAT | EPSG:4326 | Period 1: 18–26 Aug 2024<br/>Period 2: 28 Aug–04 Sep 2024 |
| **Preliminary Impact Assessment** | UNOSAT / UNITAR | [Product 3937](https://unosat.org/products/3937) | UNOSAT Report | N/A | Pleiades (29–30 Aug 2024) |
| **Healthcare Infrastructure** | OpenStreetMap Contributors | Overpass API (`amenity=hospital/clinic/doctors`, `healthcare=*`) | ODbL 1.0 | EPSG:4326 | Mapped crowdsourced records |

### 4.1 UNOSAT Water Classification Verification
Source attribute inspection of UNOSAT Product 3954 confirmed that:
- **`Water_Clas` Attribute:** Explicitly coded as `"Flood Water"`.
- **`Water_Stat` Attribute:** Coded as `"New Water / Water Increase"`.
- **Reference Water Separation:** Permanent river channels and baseline water bodies were excluded by UNOSAT and are not counted as flood inundation.
- **Validation Status:** Marked by UNOSAT as `"Not yet field validated"`, reflecting rapid satellite-derived emergency mapping without ground-truth calibration.

*A complete machine-readable provenance manifest is maintained at `data/source_data_manifest.json`.*

---

## 5. Methodology & Geospatial Processing

```
[UNOSAT Product 3954 (Period 1 & Period 2) / geoBoundaries ADM2 / OSM API]
                         │
                         ▼
   [Phase 1: Validation & Topology Repair]
     - Verify source CRS (EPSG:4326), geometry types, and metadata attributes
     - shapely.validation.make_valid
     - Drop null / empty geometries
                         │
                         ▼
   [Phase 2: Administrative Extraction & Spatial Indexing]
     - Match Cumilla boundary in ADM2
     - MultiPolygon explosion
     - Bounding box indexing (.cx[minx:maxx, miny:maxy]) in source CRS
                         │
                         ▼
   [Phase 3: Coordinate Reprojection & Metric Clipping]
     - Reproject to WGS 84 / UTM Zone 46N (EPSG:32646)
     - geopandas.clip against Cumilla boundary for Period 1 and Period 2
     - Filter healthcare facilities within study area
                         │
                         ▼
   [Phase 4: Metric Quantification & Multi-Temporal Proximity Analysis]
     - Planar surface area computation (km²) via dissolved union (union_all())
     - Point-in-polygon flood inundation test
     - Euclidean distance (meters) to nearest flood polygon boundary
     - Classification into proximity tiers (<500m, 500m-1km, 1-2.5km, 2.5-5km)
     - Disaggregation: Hospitals/Clinics vs. Pharmacies/Labs vs. Other
     - Dynamic temporal comparison (area delta, distance shift)
                         │
                         ▼
   [Phase 5: Cartography, Interactive Web GIS & Automated Reporting]
     - Static publication maps with explicit observation period labels (Map 1, Map 2, Map 3 in PNG/PDF)
     - Multi-layer Folium web map
     - Dynamic synthesis of outputs/summary.json and reports/research_report.md
```

---

## 6. Empirical Results

All metrics reported below were computed directly from the processed authentic spatial layers:

### 6.1 District Flood Extent & Temporal Comparison
- **Total District Area:** 3,088.66 km² (3,088,658,441 m²)
- **First Observation Period (18–26 Aug 2024):** **472.16 km²** (15.29% of district)
- **Second Observation Period (28 Aug–04 Sep 2024):** **453.54 km²** (14.68% of district)
- **Mapped Inundation Difference:** **-18.62 km²** (-0.61% points of district area)

#### Table 6.1: UNOSAT Multi-Temporal Observation Window Comparison (Cumilla District)
| Observation Window | Satellite Sensor | Inundated Area (km²) | District Coverage (%) | Facilities within 500m | Mean Distance (m) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Period 1: 18–26 August 2024 (First Observation Period)** | Sentinel-1 SAR (10m) | **472.16** | **15.29%** | **61** (70.9%) | **396.3** |
| **Period 2: 28 Aug–04 Sep 2024 (Second Observation Period)** | Sentinel-1 SAR (10m) | **453.54** | **14.68%** | **56** (65.1%) | **431.6** |
| **Net Difference** | — | **-18.62 km²** | **-0.61%** | **-5 facilities** | **+35.3 m** |

*Note: Both observation periods were computed independently from authentic UNOSAT shapefiles without cross-temporal aggregation.*

### 6.2 Healthcare Facility Exposure and Proximity (Period 1)

- **Total Mapped Healthcare Facilities:** 86
- **Inundation Exposure (All Facilities):**
  - Facilities directly intersecting satellite flood extent: **0** (0.0%)
  - Facilities within 500 meters of flood waters: **61** (70.9%)
  - Facilities within 1,000 meters (1 km) of flood waters: **81** (94.2%)
  - Facilities within 2,500 meters (2.5 km) of flood waters: **86** (100.0%)
- **Distance Metrics (All Facilities, EPSG:32646):**
  - **Mean Distance:** 396.3 meters
  - **Median Distance:** 289.3 meters
  - **Standard Deviation:** 313.2 meters
  - **Minimum Distance:** 31.9 meters
  - **Maximum Distance:** 1,245.2 meters

#### Table 6.2: Disaggregated Proximity Metrics by Functional Healthcare Category (Period 1)
| Functional Category | Total Facilities | Intersecting Flood | Within 500m | Within 1,000m | Mean Distance (m) | Median Distance (m) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Group A: Hospitals & Clinics** | 64 | 0 (0.0%) | 50 (78.1%) | 62 (96.9%) | 345.1 | 275.0 |
| **Group B: Pharmacies & Laboratories** | 19 | 0 (0.0%) | 9 (47.4%) | 16 (84.2%) | 572.0 | 532.3 |
| **Group C: Other / Unspecified** | 3 | 0 (0.0%) | 2 (66.7%) | 3 (100.0%) | 374.5 | 454.9 |
| **Total Mapped Facilities** | **86** | **0 (0.0%)** | **61 (70.9%)** | **81 (94.2%)** | **396.3** | **289.3** |

*Note: Group A includes mapped hospitals and clinics (such as Upazila Health Complexes, specialized hospitals, and community clinics). Group B includes commercial retail pharmacies and diagnostic laboratories. Group C includes alternative medicine and unclassified medical amenities.*

---

## 7. Discussion

The disaggregated empirical findings yield key insights into rural-urban spatial patterns in disaster exposure:
1. **Proximity of Mapped Hospitals and Clinics:** **78.1%** of mapped hospitals and clinics (Group A, 50 of 64) were situated within 500 meters of detected floodwaters. Government facilities—such as Debidwar Upazila Health Complex (distance 31.9 meters), Brahmanpara Upazila Health Complex, and Burichang Upazila Health Complex—were located along the flooded Gumti river corridor. While no mapped facility points directly overlapped the detected water extent in this analysis, their immediate surroundings were in close proximity to inundation boundaries.
2. **Commercial Pharmacy Clustering:** Commercial pharmacies and diagnostic laboratories exhibited greater mean distance to floodwaters (572.0 m) with only 47.4% within 500m. This reflects their spatial concentration in the central commercial district of Cumilla Sadar, which sits on slightly higher alluvial terrace topography.
3. **Temporal Comparison:** The comparison between Period 1 and Period 2 indicates a 18.62 km² reduction in mapped flood extent between observation periods, with mean facility distance shifting from 396.3 m to 431.6 m (+35.3 m).

---

## 8. Limitations and Scientific Caveats

Scientific integrity requires explicit articulation of data and sensor limitations:

1. **Radar Remote Sensing Physical Constraints:**
   UNOSAT Product 3954 is derived from Copernicus Sentinel-1 C-band Synthetic Aperture Radar (SAR) imagery at 10-meter spatial resolution. While SAR penetrates clouds and atmospheric rain:
   - In **dense rural tree canopy** (homestead groves of bamboo, mango, and betel nut palms), C-band microwave radiation (~5.6 cm wavelength) cannot fully penetrate foliage, leading to systematic under-detection of submerged residential homesteads (*bari*).
   - In **urban built-up centers**, vertical building walls and flat water surfaces cause double-bounce corner reflection, elevating radar backscatter and masking standing water in narrow urban streets.
2. **Euclidean Distance vs. Network Travel Impedance:**
   The proximity metrics computed in this study represent planar straight-line (Euclidean) distances. Straight-line distance does not measure travel time, road elevation, bridge structural integrity, or transit impassability. In deltaic Bangladesh, a hospital situated 800 meters away across an inundated road or severed bridge may be completely unreachable without motorized watercraft.
3. **OpenStreetMap Data Vintage & Completeness:**
   OpenStreetMap records reflect community-contributed spatial data retrieved via Overpass API. They do not constitute verified historical facility rosters as of August 2024. Furthermore, remote rural Union Health & Family Welfare Centers (UHFWC) may be under-represented in OSM compared to tertiary facilities in urban Cumilla.
4. **Absence of Flood Depth and Velocity:**
   Satellite-detected 2D flood extents indicate surface water presence but provide no data on flood water depth, flow velocity, or duration of standing inundation—factors critical for assessing building accessibility.
5. **Cartographic Buffer Generalization on Map 3:**
   The 500m and 1,000m buffer zones shown on Map 3 are cartographically generalized for visualization readability (speckle filtered <1,000 m², geometry simplified by 25m). All quantitative proximity metrics in `results.csv` and `summary.json` were computed on the exact original unsimplified analytical geometries.

---

## 9. Future Research Directions

To expand this foundational GIS project for advanced research:
1. **Multimodal Earth Observation:** Integrate optical imagery (Sentinel-2, PlanetScope) using water indices (NDWI, MNDWI) during cloud-free windows to validate SAR detection.
2. **Network Routing & Isochrone Modeling:** Integrate OpenStreetMap road networks via `osmnx` and elevation models (FABDEM or SRTM) to compute actual drive-time and walk-time isochrones under flooded road constraints.
3. **Hydrodynamic Inundation Modeling:** Pair satellite observations with 2D hydrodynamic models (e.g., LISFLOOD-FP or HEC-RAS) driven by precipitation and upstream gauge discharge.
4. **Demographic Exposure Integration:** Overlay high-resolution gridded population datasets (WorldPop / High-Resolution Settlement Layer) to estimate vulnerable populations cut off from medical care.

---

## 10. Development Note

AI tools were used to assist with coding and documentation.

---

## 11. Data References

1. **United Nations Satellite Centre (UNOSAT) / UNITAR (2024).** *Satellite detected water extents between 28 August & 4 September 2024 in Bangladesh (Product ID: 3954).* GLIDE: FL20240825BGD. Geneva, Switzerland. [https://unosat.org/products/3954](https://unosat.org/products/3954).
2. **United Nations Satellite Centre (UNOSAT) / UNITAR (2024).** *Preliminary satellite-derived flood impact assessment, Cumilla City, Cumilla district, Chattogram Division, Bangladesh (Product ID: 3937).* Geneva, Switzerland. [https://unosat.org/products/3937](https://unosat.org/products/3937).
3. **Runfola, D. et al. (2020).** *geoBoundaries: A global database of political administrative boundaries.* PLoS ONE 15(4): e0231866. [https://www.geoboundaries.org/](https://www.geoboundaries.org/).
4. **OpenStreetMap Contributors (2024).** *Healthcare facility points in Cumilla District, Bangladesh.* Retrieved via Overpass API under the Open Database License (ODbL). [https://www.openstreetmap.org/](https://www.openstreetmap.org/).
5. **Bangladesh Bureau of Statistics (BBS) & UN OCHA ROAP (2020).** *Administrative boundaries of Bangladesh.* Humanitarian Data Exchange (HDX).
