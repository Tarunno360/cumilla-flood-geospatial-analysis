# Limitations and Scientific Caveats

This document articulates the remote sensing, geometric, and cartographic limitations inherent in this case study.

---

## 1. Remote Sensing & Sensor Physics
- **Sensor:** Copernicus Sentinel-1 C-band Synthetic Aperture Radar (SAR), ~5.405 GHz center frequency (~5.6 cm wavelength), 10 m pixel spacing.
- **Specular Reflection Assumption:** Open, unperturbed standing water reflects radar signals away from the sensor, yielding very low backscatter (dark pixels).
- **Vegetation Attenuation:** In Bangladesh's rural landscape, homesteads (*bari*) are typically surrounded by dense clumps of fruit trees, bamboo, and betel nut palms. C-band radar cannot penetrate dense foliage canopy, leading to systematic under-detection of submerged residential plots.
- **Urban Built-Up Environments:** In urban Cumilla City, vertical masonry walls and flat inundated streets produce "double-bounce" corner reflections, which generate high backscatter that can mask standing water in narrow street canyons.

---

## 2. Geometric Metric vs. Network Accessibility
- **Euclidean (Planar) Proximity:**
  The proximity metrics presented in this study reflect Euclidean straight-line distance.
- **Travel Impedance Realities:**
  In riverine delta floodplains:
  - Roads may be washed out, submerged under rapid currents, or blocked by stranded vehicles.
  - Bridge approaches and culverts frequently collapse during peak embankment breaches.
  - A healthcare facility separated from a settlement by a submerged road or river channel may be completely inaccessible by foot or road vehicle, regardless of straight-line distance.

---

## 3. Data Vintage & Crowdsourcing Bias
- **OpenStreetMap Vintages:**
  OpenStreetMap facility data reflects crowdsourced geographic contributions collected over multiple years and updated dynamically. It does not represent a timestamped census of functioning facilities during the emergency week of August 2024.
- **Urban vs. Rural Mapping Density:**
  Urban hospitals and commercial diagnostic centers in Cumilla Sadar are thoroughly mapped in OSM, whereas rural Union Health & Family Welfare Centers (UHFWC) and community clinics may be under-represented.

---

## 4. Lack of Hydrodynamic Depth and Velocity
- UNOSAT flood extents provide binary (wet/dry) spatial footprints without depth or flow velocity. A 10 cm sheet flood across an agricultural field has vastly different humanitarian consequences than a 2-meter violent breach from the Gumti River embankment.
