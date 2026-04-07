"""
Zambia GeoHub data client.

Strategy:
  - Dynamically queries ArcGIS Online for ALL datasets tagged 'zmb' (public, no API key needed).
    Admin confirmed: "All data is tagged zmb so you can do an organisation query for that."
  - Results are cached at startup so search is fast.
  - New datasets added to the Hub with the zmb tag are automatically picked up.

No API key required — all zmb-tagged datasets used here are publicly accessible.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAX_FEATURES = int(os.getenv("MAX_FEATURES", "200"))
REQUEST_TIMEOUT = 20

# Irrelevant items that happen to have zmb in their tags (not Zambia geospatial data)
_SKIP_TITLES = {
    "1893 chicago ucla 3d", "mpjb", "enriched_gadm41_zmb_shp___gadm41_zmb_0",
}


class HubClient:
    """
    Zambia GeoHub data client.
    Searches ArcGIS Online for all public datasets tagged 'zmb'.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self._catalog: list = []  # cached on first use

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_datasets(self, query: str, max_results: int = 10) -> list:
        """
        Search the zmb catalog for datasets matching *query*.
        Loads and caches the full catalog on first call.
        """
        catalog = self._load_catalog()
        return self._rank(query, catalog)[:max_results]

    def fetch_geojson(self, feature_url: str, max_features: int = MAX_FEATURES) -> dict:
        """Fetch features from a FeatureServer layer as GeoJSON."""
        base = feature_url.rstrip("/")
        if base.endswith("/query"):
            base = base[:-6]

        params = {
            "where": "1=1",
            "outFields": "*",
            "resultRecordCount": max_features,
            "f": "geojson",
        }
        try:
            resp = self.session.get(f"{base}/query", params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            geojson = resp.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Feature fetch failed: {exc}") from exc

        if "features" not in geojson:
            raise ValueError(f"Response is not GeoJSON: {list(geojson.keys())}")
        return geojson

    def get_catalog(self) -> list:
        """Return the full zmb dataset catalog."""
        return self._load_catalog()

    def get_field_metadata(self, dataset: dict) -> list:
        return dataset.get("fields", [])

    # ------------------------------------------------------------------
    # Catalog loading
    # ------------------------------------------------------------------

    def _load_catalog(self) -> list:
        """Load catalog from ArcGIS Online (cached after first call)."""
        if self._catalog:
            return self._catalog

        try:
            resp = self.session.get(
                "https://www.arcgis.com/sharing/rest/search",
                params={
                    "q": 'tags:zmb type:"Feature Service"',
                    "f": "json",
                    "num": 100,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            # Fall back to built-in seed catalog if network fails
            self._catalog = _SEED_CATALOG
            return self._catalog

        catalog = []
        seen_urls = set()

        for r in results:
            title = r.get("title", "") or ""
            if title.lower() in _SKIP_TITLES:
                continue

            url = (r.get("url") or "").rstrip("/")
            if not url or "FeatureServer" not in url:
                continue

            # Ensure layer 0 is appended
            if not url.split("/")[-1].isdigit():
                url = url + "/0"

            if url in seen_urls:
                continue
            seen_urls.add(url)

            tags = r.get("tags") or []
            snippet = (r.get("snippet") or "")[:300]
            fields = self._fetch_fields(url)

            catalog.append({
                "id": r.get("id", ""),
                "name": title,
                "description": snippet,
                "url": url,
                "tags": [t.lower() for t in tags],
                "fields": fields,
                "geometry_type": "Unknown",
                "extent": {},
                "modified": str(r.get("modified", "")),
            })

        self._catalog = catalog if catalog else _SEED_CATALOG
        return self._catalog

    # ------------------------------------------------------------------
    # Search ranking
    # ------------------------------------------------------------------

    def _rank(self, query: str, catalog: list) -> list:
        """Rank catalog entries by relevance to query."""
        words = [w.lower() for w in query.split() if len(w) > 2]
        scored = []
        for ds in catalog:
            score = 0
            text = (ds["name"] + " " + ds["description"] + " " + " ".join(ds["tags"])).lower()
            for word in words:
                if word in text:
                    score += 2
                # partial match
                for token in text.split():
                    if word in token or token in word:
                        score += 0.5
            if score > 0:
                scored.append((score, ds))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return catalog  # return all if no match

        return [ds for _, ds in scored]

    # ------------------------------------------------------------------
    # Field metadata
    # ------------------------------------------------------------------

    def _fetch_fields(self, layer_url: str) -> list:
        """Fetch field definitions from a FeatureServer layer."""
        base = layer_url.rstrip("/")
        if base.endswith("/query"):
            base = base[:-6]
        try:
            resp = self.session.get(f"{base}?f=json", timeout=10)
            raw = resp.json().get("fields", [])
            return [
                {
                    "name": f.get("name", ""),
                    "alias": f.get("alias", f.get("name", "")),
                    "type": f.get("type", ""),
                }
                for f in raw
                if f.get("name") and not f.get("name", "").startswith("Shape")
            ]
        except Exception:
            return []


# ------------------------------------------------------------------
# Seed catalog — used as fallback if ArcGIS Online is unreachable
# Built from confirmed working zmb-tagged datasets (April 2025)
# ------------------------------------------------------------------
_SEED_CATALOG = [
    {"id": "f523a78b0e2b4c6a8719ef05a165ab4e", "name": "NSDI Zambia Operational Health Facility Layer",
     "description": "Operational health facilities across Zambia including hospitals, health centres, and clinics. Source: Ministry of Health and ZamStats.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_ZMB_HealthFac_v01beta/FeatureServer/0",
     "tags": ["health", "facilities", "hospitals", "clinics", "zambia", "zmb"], "fields": [], "geometry_type": "Point", "extent": {}, "modified": ""},
    {"id": "0c748bfc945c49ce81d07034b1560a68", "name": "GRID3 ZMB Operational Schools",
     "description": "Operational schools across Zambia including primary and secondary schools. Source: ZamStats and Ministry of General Education.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_ZMB_School_v01beta/FeatureServer/0",
     "tags": ["schools", "education", "primary", "secondary", "zambia", "zmb"], "fields": [], "geometry_type": "Point", "extent": {}, "modified": ""},
    {"id": "d27357c640394f11943316e36cebaba3", "name": "ZMB Operational Districts",
     "description": "Administrative district boundaries for Zambia 2020. Source: Office of the Surveyor General and Electoral Commission of Zambia.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_Administrative_Boundaries_Districts_2020/FeatureServer/0",
     "tags": ["districts", "boundaries", "administrative", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
    {"id": "a0293a6e84c143298227518eb3418d23", "name": "GRID3 ZMB Operational Settlement Names",
     "description": "Settlement point locations and names across Zambia. Source: ZamStats 2010 census cartography.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_Zambia_Operational_Settlement_Points_and_Names_Version01/FeatureServer/0",
     "tags": ["settlements", "villages", "towns", "population", "zambia", "zmb"], "fields": [], "geometry_type": "Point", "extent": {}, "modified": ""},
    {"id": "8f73c42ed3884256904ae12440fae558", "name": "ZMB Operational Points of Interest",
     "description": "Points of interest across Zambia including community facilities and services. Source: ZamStats and CLTS.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_Zambia_Operational_Points_of_Interest_Version01/FeatureServer/0",
     "tags": ["points of interest", "poi", "community", "facilities", "zambia", "zmb"], "fields": [], "geometry_type": "Point", "extent": {}, "modified": ""},
    {"id": "3fb6aa51dc9a4df1a1b7f4e48df5a374", "name": "GRID3 ZMB Risk Indicators by District and Province",
     "description": "Risk index and population at risk by district and province — covering socioeconomic vulnerability, WASH, communication access.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_Risk_Layers_Aggregated_Districts_Provinces/FeatureServer/0",
     "tags": ["risk", "vulnerability", "wash", "population", "districts", "provinces", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
    {"id": "f310fa8209cb4685b56e309cf6d1388f", "name": "Flood Prone Districts in Zambia",
     "description": "Districts in Zambia prone to flooding.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_Flood_Prone_Districts/FeatureServer/0",
     "tags": ["flood", "disaster", "risk", "districts", "environment", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
    {"id": "7d9e73eb624448c79826d3c3274bf790", "name": "OSM Zambia Rivers",
     "description": "Rivers in Zambia from OpenStreetMap.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/OSM_rivers/FeatureServer/0",
     "tags": ["rivers", "water", "osm", "environment", "zambia", "zmb"], "fields": [], "geometry_type": "Polyline", "extent": {}, "modified": ""},
    {"id": "ef791bcb05db473a9dc4eb04e41664b5", "name": "Zambia Wetlands and Lakes",
     "description": "Wetlands and lakes in Zambia from OpenStreetMap.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_wetlands_lakes/FeatureServer/0",
     "tags": ["wetlands", "lakes", "water", "environment", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
    {"id": "7be52e48252c464bbb8e1c713f87a5d1", "name": "Zambia Biodiversity Data",
     "description": "Biodiversity polygon data for Zambia. Source: RCMRD/CIFOR-ICRAF.",
     "url": "https://services6.arcgis.com/zOnyumh63cMmLBBH/arcgis/rest/services/Zambia_Biodiversity_Data/FeatureServer/0",
     "tags": ["biodiversity", "environment", "conservation", "nature", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
    {"id": "c6d0ce455cae4f4c96ef98e7d44f9793", "name": "Zambia Forests Data",
     "description": "Forest polygon data for Zambia. Source: RCMRD/CIFOR-ICRAF.",
     "url": "https://services6.arcgis.com/zOnyumh63cMmLBBH/arcgis/rest/services/Zambia_Forests_Data/FeatureServer/0",
     "tags": ["forests", "trees", "environment", "land cover", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
    {"id": "883e648672134f6488ffbc9f31533a65", "name": "Zambia Biodiversity Point Data",
     "description": "Biodiversity point observations across Zambia. Source: RCMRD/CIFOR-ICRAF.",
     "url": "https://services6.arcgis.com/zOnyumh63cMmLBBH/arcgis/rest/services/Zambia_Biodiversity_Point_Data/FeatureServer/0",
     "tags": ["biodiversity", "species", "environment", "conservation", "zambia", "zmb"], "fields": [], "geometry_type": "Point", "extent": {}, "modified": ""},
    {"id": "c571868321cc41ef99ed27535ffa964d", "name": "Zambia Major Roads",
     "description": "Major road network in Zambia.",
     "url": "https://services3.arcgis.com/t6lYS2Pmd8iVx1fy/arcgis/rest/services/glc_ZMB_trs_roads_major_b_view/FeatureServer/0",
     "tags": ["roads", "transport", "infrastructure", "highway", "zambia", "zmb"], "fields": [], "geometry_type": "Polyline", "extent": {}, "modified": ""},
    {"id": "bb0ba0c4ee1945f0ae35c1430b12574c", "name": "Lusaka Townships Risk Layers",
     "description": "Risk index by Lusaka township — socioeconomic vulnerability and communication access.",
     "url": "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Lusaka_Townships_Risk_Layers/FeatureServer/0",
     "tags": ["lusaka", "townships", "risk", "urban", "vulnerability", "zambia", "zmb"], "fields": [], "geometry_type": "Polygon", "extent": {}, "modified": ""},
]
