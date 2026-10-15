# Methodology: Spatial Delineation and Exposure Modeling

This document provides a technical overview of the computational methods and geospatial transformations implemented in the project.

---

## 1. Projected Coordinate Reference System Selection
- **Target Projected CRS:** `EPSG:32646` (WGS 84 / UTM Zone 46N)
- **Unit of Measurement:** Meters
- **Geodetic Rationale:**
  - Cumilla District lies between longitudes 90°38′E and 91°22′E.
  - UTM Zone 46N is centered on 93°00′E, encompassing Bangladesh east of 90°E.
  - Scale factor distortion at 91°E is less than 0.08%, ensuring that planar metric calculations for polygon area (km²) and point-to-polygon Euclidean distance (meters) maintain high geodetic accuracy.

---

## 2. Geometric Validation and Cleaning
- Raw spatial vectors from remote sensing and crowd-sourced repositories frequently contain topological defects, such as self-intersections ("bowtie" polygons), unclosed rings, or sliver artifacts.
- Geometry cleaning pipeline:
  1. Detect invalid geometries via `gdf.geometry.is_valid`.
  2. Filter null or empty geometry instances.
  3. Apply `shapely.validation.make_valid` to restructure invalid rings into valid `MultiPolygon` or `Polygon` structures.
  4. Perform spatial clipping using `geopandas.clip` against the dissolved boundary of Cumilla District.

---

## 3. Surface Area Calculation
- Total district surface area and satellite-detected flood area are computed directly on projected polygon geometries:
  $$\text{Area}_{\text{km}^2} = \frac{\sum \text{Area}(\text{geometry}_i)}{1,000,000}$$
- Proportional flood coverage:
  $$\text{Flood Percentage} = \left(\frac{\text{Area}_{\text{flood}}}{\text{Area}_{\text{district}}}\right) \times 100$$

---

## 4. Facility Inundation and Distance Analysis
- **Inundation Intersection:**
  A healthcare facility point $P_j$ is classified as inundated if:
  $$P_j \cap \bigcup_{i} \text{FloodPoly}_i \neq \emptyset$$
- **Euclidean Distance to Flood Perimeter:**
  For facilities situated outside the detected flood extent, the minimum planar distance to the nearest flood polygon boundary is computed via Shapely vector distance:
  $$d(P_j, \text{Flood}) = \min_{i} \text{dist}(P_j, \text{FloodPoly}_i)$$
- **Proximity Categorization:**
  Facilities are assigned into standardized operational buffer tiers:
  - *Inside Flood Extent:* $d = 0\text{ m}$
  - *Within 500 m:* $0 < d \le 500\text{ m}$
  - *500 m – 1 km:* $500\text{ m} < d \le 1,000\text{ m}$
  - *1 km – 2.5 km:* $1,000\text{ m} < d \le 2,500\text{ m}$
  - *2.5 km – 5 km:* $2,500\text{ m} < d \le 5,000\text{ m}$
  - *> 5 km:* $d > 5,000\text{ m}$
