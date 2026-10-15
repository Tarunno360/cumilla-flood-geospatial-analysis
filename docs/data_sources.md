# Data Sources and Provenance

This document describes the geographic datasets used in the **Bangladesh Flood Exposure and Healthcare Facility Proximity Analysis (Cumilla District, August 2024)**.

---

## 1. Administrative Boundaries (geoBoundaries)
- **Dataset:** Bangladesh Administrative Level 2 (Districts)
- **Identifier:** `BGD-ADM2`
- **Provider:** William & Mary geoBoundaries Research Lab / Bangladesh Bureau of Statistics (BBS) / UN OCHA Regional Office for Asia and the Pacific (ROAP)
- **Retrieval URL:** [https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/](https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/)
- **Direct GeoJSON URL:** [https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/BGD/ADM2/geoBoundaries-BGD-ADM2.geojson](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/BGD/ADM2/geoBoundaries-BGD-ADM2.geojson)
- **License:** Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)
- **Native CRS:** WGS 84 (`EPSG:4326`)
- **Vintage:** 2020 (Dec 2023 release)
- **Analytical Role:** Delineates the official administrative territory of Cumilla District. Multi-part polygon geometries were checked, repaired using `shapely.validation.make_valid`, and dissolved into a single administrative mask.

---

## 2. Satellite-Derived Flood Extent (UNOSAT Product 3954)
- **Title:** Satellite detected water extents between 28 August & 4 September 2024 in Bangladesh
- **GLIDE Event Number:** `FL20240825BGD`
- **Product ID:** 3954
- **Provider:** United Nations Satellite Centre (UNOSAT / UNITAR)
- **Metadata Page:** [https://unosat.org/products/3954](https://unosat.org/products/3954)
- **Download Archive:** [https://unosat.org/static/unosat_filesystem/3954/FL20240825BGD_SHP.zip](https://unosat.org/static/unosat_filesystem/3954/FL20240825BGD_SHP.zip)
- **Sensor:** Copernicus Sentinel-1 Synthetic Aperture Radar (SAR)
- **Spatial Resolution:** 10 meters
- **Observation Windows:**
  - First satellite observation period: 18 to 26 August 2024
  - Second satellite observation period: 28 August to 04 September 2024
- **Analysis Methodology:** Automated machine learning water classification applied to dual-polarization SAR backscatter intensity.
- **License:** Open Access / Creative Commons Attribution (UNOSAT / UNITAR)
- **Native CRS:** WGS 84 (`EPSG:4326`)
- **Analytical Role:** Supplies the primary surface inundation vector polygons used for area calculation and facility proximity measurements.

---

## 3. High-Resolution Assessment Context (UNOSAT Product 3937)
- **Title:** Preliminary satellite-derived flood impact assessment, Cumilla City, Cumilla district, Chattogram Division, Bangladesh, 20 August 2024
- **Product ID:** 3937
- **Provider:** United Nations Satellite Centre (UNOSAT / UNITAR)
- **Metadata Page:** [https://unosat.org/products/3937](https://unosat.org/products/3937)
- **Report Document:** [https://unosat.org/static/unosat_filesystem/3937/UNOSAT_Preliminary_Assessment_Report_FL20240825BGD_Comilla_30Aug2024.pdf](https://unosat.org/static/unosat_filesystem/3937/UNOSAT_Preliminary_Assessment_Report_FL20240825BGD_Comilla_30Aug2024.pdf)
- **Sensors:** Pleiades (50 cm resolution, 29 August 2024) and GEOEYE-1 (50 cm resolution, 16 October 2023)
- **Analytical Role:** Qualitative validation context for urban vs. peri-urban inundation patterns in northern Cumilla City.

---

## 4. Healthcare Facilities (OpenStreetMap)
- **Dataset:** Mapped medical infrastructure (`amenity=hospital`, `amenity=clinic`, `amenity=doctors`, `healthcare=*`)
- **Provider:** OpenStreetMap Contributors
- **Acquisition Protocol:** Overpass API query within Cumilla District geographic envelope
- **License:** Open Database License (ODbL) 1.0
- **Native CRS:** WGS 84 (`EPSG:4326`)
- **Analytical Role:** Point locations for evaluating physical proximity to inundated areas.
- **Critical Caveat:** OSM records reflect community-contributed data at query time and do not represent verified historical operational status as of August 2024.
