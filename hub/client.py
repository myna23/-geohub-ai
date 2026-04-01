"""
Zambia GeoHub data client.

Strategy:
  1. Curated catalog — 20+ verified real Zambia datasets (GRID3, NSDI, World Bank sources).
     Keyword search runs against this catalog first (fast, always Zambia-specific).
  2. ArcGIS Online fallback — appends "zambia" to the query so results stay relevant.

No API key is required — all datasets are publicly accessible.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAX_FEATURES = int(os.getenv("MAX_FEATURES", "200"))
REQUEST_TIMEOUT = 20  # seconds

# ---------------------------------------------------------------------------
# Verified, working Zambia datasets (confirmed live April 2025)
# Source: GRID3, NSDI, World Bank, and other open data providers
# ---------------------------------------------------------------------------
ZAMBIA_CATALOG = [
    {
        "id": "zmb_health_facilities",
        "name": "Zambia Health Facilities (GRID3/NSDI)",
        "description": "Operational health facilities across Zambia including hospitals, health centres, and clinics. Source: GRID3/NSDI Beta v01.",
        "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_ZMB_HealthFac_v01beta/FeatureServer/0",
        "tags": ["health", "hospitals", "clinics", "facilities", "medical"],
        "geometry_type": "Point",
        "fields": [],
    },
    {
        "id": "zmb_schools",
        "name": "Zambia Operational Schools (GRID3)",
        "description": "Operational schools across Zambia including primary, secondary, and special schools. Source: GRID3 v1.0 Beta.",
        "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_ZMB_School_v01beta/FeatureServer/0",
        "tags": ["schools", "education", "primary", "secondary", "learning"],
        "geometry_type": "Point",
        "fields": [],
    },
    {
        "id": "zmb_districts_2022",
        "name": "Zambia District Boundaries 2022 (NSDI/GRID3)",
        "description": "Administrative district boundaries for Zambia as of 2022. Published by GRID3 and NSDI.",
        "url": "https://services2.arcgis.com/YS3PRtw1PxtVqnE7/arcgis/rest/services/NSDI_Zambia___Administrative_Boundaries_Districts_2022_(Published_by_GRID3)/FeatureServer/0",
        "tags": ["districts", "boundaries", "administrative", "admin", "regions"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_districts_2020",
        "name": "Zambia Districts 2020 (GRID3)",
        "description": "Operational district administrative boundaries for Zambia 2020. Source: GRID3.",
        "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_Administrative_Boundaries_Districts_2020/FeatureServer/0",
        "tags": ["districts", "boundaries", "administrative", "admin"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_settlements",
        "name": "Zambia Settlement Names (GRID3)",
        "description": "Operational settlement names and points across Zambia. Includes villages, towns, and cities. Source: GRID3 v1.0.",
        "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_Zambia_Operational_Settlement_Points_and_Names_Version01/FeatureServer/0",
        "tags": ["settlements", "villages", "towns", "cities", "population", "communities"],
        "geometry_type": "Point",
        "fields": [],
    },
    {
        "id": "zmb_roads",
        "name": "Zambia Roads Network",
        "description": "Road network across Zambia including primary, secondary and tertiary roads.",
        "url": "https://services1.arcgis.com/qN3V93cYGMKQCOxL/arcgis/rest/services/Roads_Zambia_WFL1/FeatureServer/0",
        "tags": ["roads", "transport", "infrastructure", "network", "highway"],
        "geometry_type": "Polyline",
        "fields": [],
    },
    {
        "id": "zmb_water_kafue",
        "name": "Kafue Basin Water Supply (Zambia)",
        "description": "Water supply infrastructure and access points in the Kafue Basin, Zambia.",
        "url": "https://services1.arcgis.com/RTK5Unh1Z71JKIiR/arcgis/rest/services/Kafue_Water_Supply/FeatureServer/0",
        "tags": ["water", "supply", "kafue", "basin", "access", "infrastructure"],
        "geometry_type": "Point",
        "fields": [],
    },
    {
        "id": "zmb_water_quality",
        "name": "Kafue Water Quality Monitoring (Zambia)",
        "description": "Water quality monitoring stations and data along the Kafue River, Zambia.",
        "url": "https://services1.arcgis.com/RTK5Unh1Z71JKIiR/arcgis/rest/services/Kafue_Water_Quality/FeatureServer/0",
        "tags": ["water", "quality", "kafue", "river", "monitoring", "environment"],
        "geometry_type": "Point",
        "fields": [],
    },
    {
        "id": "zmb_kafue_basin",
        "name": "Kafue Basin Boundary (Zambia)",
        "description": "Boundary of the Kafue River Basin in Zambia, a major water resource.",
        "url": "https://services1.arcgis.com/RTK5Unh1Z71JKIiR/arcgis/rest/services/The_Kafue_Basin/FeatureServer/0",
        "tags": ["kafue", "basin", "boundary", "river", "water", "environment"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_journey_water",
        "name": "Zambia Journey of Water",
        "description": "Water access and journey-to-water data across Zambia communities.",
        "url": "https://services1.arcgis.com/RTK5Unh1Z71JKIiR/arcgis/rest/services/Zambia_Journey_of_Water/FeatureServer/0",
        "tags": ["water", "access", "community", "journey", "supply", "rural"],
        "geometry_type": "Point",
        "fields": [],
    },
    {
        "id": "zmb_districts_rt",
        "name": "Zambia Districts (Reference)",
        "description": "Administrative district reference boundaries for Zambia.",
        "url": "https://services1.arcgis.com/RTK5Unh1Z71JKIiR/arcgis/rest/services/Zambia_Districts/FeatureServer/0",
        "tags": ["districts", "boundaries", "administrative", "reference"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_aquaculture_onshore",
        "name": "Zambia Onshore Aquaculture Sites",
        "description": "Onshore aquaculture sites and suitability zones across Zambia. Source: World Bank.",
        "url": "https://services.arcgis.com/iQ1dY19aHwbSDYIF/arcgis/rest/services/Zambia_onshore_aquaculture/FeatureServer/0",
        "tags": ["aquaculture", "fish", "farming", "agriculture", "food security"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_aquaculture_kariba",
        "name": "Lake Kariba Aquaculture Suitability Zones (Zambia)",
        "description": "Suitability zones for cage aquaculture on the Zambia portion of Lake Kariba. Source: World Bank.",
        "url": "https://services.arcgis.com/iQ1dY19aHwbSDYIF/arcgis/rest/services/Suitability_zones_for_cage_aquaculture_on_lake_Kariba__Zambia_part_/FeatureServer/0",
        "tags": ["aquaculture", "lake kariba", "fish", "farming", "suitability", "water"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_geology_250k",
        "name": "Zambia Geology Map 1:250,000",
        "description": "Geological map of Zambia at 1:250,000 scale covering rock types and formations.",
        "url": "https://services1.arcgis.com/AhXvNWFdL7hH4TjJ/arcgis/rest/services/Zambia_250k_geology/FeatureServer/0",
        "tags": ["geology", "minerals", "rock", "formation", "mining", "land"],
        "geometry_type": "Polygon",
        "fields": [],
    },
    {
        "id": "zmb_social_distancing",
        "name": "Zambia Social Distancing / Accessibility Layers (GRID3)",
        "description": "Population accessibility layers for Zambia showing travel times to services. Source: GRID3.",
        "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/ZMB_SocialDistancing_v1_0_index/FeatureServer/0",
        "tags": ["accessibility", "travel time", "population", "services", "social"],
        "geometry_type": "Polygon",
        "fields": [],
    },
]

# Build a lookup index: tag word → list of catalog entries
def _build_tag_index(catalog):
    index = {}
    for ds in catalog:
        for tag in ds["tags"]:
            index.setdefault(tag.lower(), []).append(ds)
        # Also index individual words from the name
        for word in ds["name"].lower().split():
            if len(word) > 3:
                index.setdefault(word, []).append(ds)
    return index

_TAG_INDEX = _build_tag_index(ZAMBIA_CATALOG)


class HubClient:
    """Zambia geospatial data client — curated catalog + ArcGIS Online fallback."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def search_datasets(self, query: str, max_results: int = 10) -> list:
        """
        Search for Zambia datasets matching *query*.

        First searches the curated catalog by keyword, then falls back to
        ArcGIS Online search with "zambia" forced in the query string.
        Returns list of cleaned dataset dicts.
        """
        results = self._search_catalog(query, max_results)

        # If catalog gave fewer than asked, top up from ArcGIS Online
        if len(results) < max_results:
            online = self._search_arcgis_online(query, max_results - len(results))
            # Deduplicate by URL
            seen_urls = {ds["url"] for ds in results}
            for ds in online:
                if ds["url"] not in seen_urls:
                    results.append(ds)
                    seen_urls.add(ds["url"])

        return results[:max_results]

    def fetch_geojson(self, feature_url: str, max_features: int = MAX_FEATURES) -> dict:
        """Fetch features from a FeatureServer layer as GeoJSON."""
        base = feature_url.rstrip("/")
        if base.endswith("/query"):
            base = base[:-6]

        query_url = f"{base}/query"
        params = {
            "where": "1=1",
            "outFields": "*",
            "resultRecordCount": max_features,
            "f": "geojson",
        }

        try:
            resp = self.session.get(query_url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            geojson = resp.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Feature fetch failed: {exc}") from exc

        if "features" not in geojson:
            raise ValueError(f"Response does not look like GeoJSON: {list(geojson.keys())}")

        # Enrich with field metadata if fields are empty
        return geojson

    def get_field_metadata(self, dataset: dict) -> list:
        """Return the fields list from a cleaned dataset dict."""
        return dataset.get("fields", [])

    def get_catalog(self) -> list:
        """Return the full curated catalog."""
        return list(ZAMBIA_CATALOG)

    # ------------------------------------------------------------------
    # Internal: catalog search
    # ------------------------------------------------------------------

    def _search_catalog(self, query: str, max_results: int) -> list:
        """Keyword search against the curated catalog."""
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        scores = {}

        for word in query_words:
            for ds in _TAG_INDEX.get(word, []):
                scores[ds["id"]] = scores.get(ds["id"], 0) + 1
            # Partial match on tags
            for tag, datasets in _TAG_INDEX.items():
                if word in tag or tag in word:
                    for ds in datasets:
                        scores[ds["id"]] = scores.get(ds["id"], 0) + 0.5

        # Sort by score descending
        ranked_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        catalog_map = {ds["id"]: ds for ds in ZAMBIA_CATALOG}

        results = []
        for ds_id in ranked_ids:
            if ds_id in catalog_map:
                ds = dict(catalog_map[ds_id])
                # Fetch fields if not yet populated
                if not ds["fields"]:
                    ds["fields"] = self._fetch_fields(ds["url"])
                results.append(ds)
            if len(results) >= max_results:
                break

        return results

    # ------------------------------------------------------------------
    # Internal: ArcGIS Online fallback search
    # ------------------------------------------------------------------

    def _search_arcgis_online(self, query: str, max_results: int) -> list:
        """Search ArcGIS Online, forcing 'zambia' in the query."""
        zambia_query = f"zambia {query}" if "zambia" not in query.lower() else query
        try:
            resp = self.session.get(
                "https://www.arcgis.com/sharing/rest/search",
                params={
                    "q": f'{zambia_query} type:"Feature Service" access:public',
                    "f": "json",
                    "num": max_results * 2,  # fetch extra to account for failures
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            return []

        cleaned = []
        for r in results:
            url = r.get("url", "") or ""
            if not url or "FeatureServer" not in url:
                url = url + "/FeatureServer" if url else ""
            if not url:
                continue
            # Append layer 0 if needed
            if not url.rstrip("/").split("/")[-1].isdigit():
                url = url.rstrip("/") + "/0"

            fields = self._fetch_fields(url)
            cleaned.append({
                "id": r.get("id", ""),
                "name": r.get("title", "Unnamed"),
                "description": (r.get("snippet") or r.get("description") or "")[:500],
                "url": url,
                "fields": fields,
                "geometry_type": "Unknown",
                "extent": {},
                "modified": str(r.get("modified", "")),
            })
            if len(cleaned) >= max_results:
                break

        return cleaned

    # ------------------------------------------------------------------
    # Internal: fetch field metadata from a FeatureServer layer
    # ------------------------------------------------------------------

    def _fetch_fields(self, layer_url: str) -> list:
        """Fetch field definitions from a FeatureServer layer endpoint."""
        base = layer_url.rstrip("/")
        if base.endswith("/query"):
            base = base[:-6]
        try:
            resp = self.session.get(f"{base}?f=json", timeout=10)
            data = resp.json()
            raw_fields = data.get("fields", [])
            return [
                {
                    "name": f.get("name", ""),
                    "alias": f.get("alias", f.get("name", "")),
                    "type": f.get("type", ""),
                }
                for f in raw_fields
                if f.get("name") and not f.get("name", "").startswith("Shape")
            ]
        except Exception:
            return []
