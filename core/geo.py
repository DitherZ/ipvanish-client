"""
core/geo.py
Geo-lookup and haversine distance sorting for IPVanish-Client v2.

Uses ip-api.com (free, no API key) for:
  - Current user's public IP, city, country, lat/lon, ISP
  - Sorting server lists nearest → furthest from user
"""

import math
from PyQt6.QtCore import QObject, pyqtSignal, QThread


# ──── SERVER COORDINATES ──── #

CITY_COORDS: dict[str, tuple[float, float]] = {
    # Asia
    "Mumbai":        (19.076,  72.877),
    "Taipei":        (25.033, 121.565),
    "Seoul":         (37.566, 126.978),
    "Tel Aviv":      (32.085,  34.781),
    "Tokyo":         (35.690, 139.692),
    "Singapore":     ( 1.352, 103.820),
    "Istanbul":      (41.015,  28.979),
    "Kuala Lumpur":  ( 3.140, 101.687),
    "Dubai":         (25.204,  55.270),
    # North America
    "Guadalajara":   (20.659, -103.349),
    "Vancouver":     (49.283, -123.121),
    "Montreal":      (45.508,  -73.588),
    "Toronto":       (43.651,  -79.347),
    "Houston":       (29.760,  -95.370),
    "New Orleans":   (29.951,  -90.071),
    "Charlotte":     (35.227,  -80.843),
    "Atlanta":       (33.749,  -84.388),
    "Ashburn":       (39.043,  -77.487),
    "Boston":        (42.360,  -71.059),
    "Dallas":        (32.777,  -96.797),
    "Miami":         (25.775,  -80.208),
    "Los Angeles":   (34.052, -118.244),
    "Chicago":       (41.878,  -87.630),
    "San Jose":      (37.338, -121.886),
    "New York":      (40.713,  -74.006),
    "Seattle":       (47.607, -122.332),
    "Denver":        (39.739, -104.984),
    "Las Vegas":     (36.174, -115.137),
    "Phoenix":       (33.449, -112.074),
    "Cincinnati":    (39.103,  -84.512),
    # Central America
    "Costa Rica":    ( 9.748,  -83.754),
    # Europe
    "Manchester":    (53.480,   -2.242),
    "London":        (51.507,   -0.128),
    "Glasgow":       (55.864,   -4.252),
    "Birmingham":    (52.486,   -1.890),
    "Copenhagen":    (55.676,   12.568),
    "Valencia":      (39.470,   -0.376),
    "Madrid":        (40.416,   -3.703),
    "Belgrade":      (44.787,   20.457),
    "Reykjavik":     (64.128,  -21.828),
    "Lisbon":        (38.717,   -9.139),
    "Brussels":      (50.850,    4.352),
    "Oslo":          (59.913,   10.752),
    "Budapest":      (47.498,   19.040),
    "Sofia":         (42.698,   23.322),
    "Ljubljana":     (46.056,   14.505),
    "Athens":        (37.983,   23.727),
    "Bordeaux":      (44.837,   -0.580),
    "Paris":         (48.857,    2.352),
    "Marseille":     (43.297,    5.381),
    "Stockholm":     (59.334,   18.063),
    "Amsterdam":     (52.374,    4.898),
    "Warsaw":        (52.230,   21.012),
    "Frankfurt":     (50.110,    8.682),
    "Dublin":        (53.333,   -6.249),
    "Bucharest":     (44.432,   26.104),
    "Prague":        (50.088,   14.420),
    "Zurich":        (47.377,    8.541),
    "Bratislava":    (48.148,   17.107),
    "Zagreb":        (45.815,   15.982),
    "Vienna":        (48.209,   16.373),
    "Milan":         (45.464,    9.190),
    "Luxembourg":    (49.612,    6.132),
    "Tirana":        (41.330,   19.831),
    "Riga":          (56.946,   24.106),
    "Helsinki":      (60.169,   24.939),
    "Chisinau":      (47.011,   28.858),
    # South America
    "Bogota":        ( 4.711,  -74.073),
    "Santiago":      (-33.459, -70.648),
    "Buenos Aires":  (-34.603, -58.381),
    "Lima":          (-12.046, -77.043),
    "Sao Paulo":     (-23.550, -46.633),
    # Oceania
    "Auckland":      (-36.867, 174.767),
    "Perth":         (-31.952, 115.861),
    "Brisbane":      (-27.468, 153.028),
    "Sydney":        (-33.869, 151.209),
    "Adelaide":      (-34.929, 138.601),
    "Melbourne":     (-37.814, 144.963),
}

# Country name → representative city for distance calc
COUNTRY_CITY: dict[str, str] = {
    "India":                "Mumbai",
    "Taiwan":               "Taipei",
    "South Korea":          "Seoul",
    "Israel":               "Tel Aviv",
    "Japan":                "Tokyo",
    "Singapore":            "Singapore",
    "Turkey":               "Istanbul",
    "Malaysia":             "Kuala Lumpur",
    "United Arab Emirates": "Dubai",
    "Mexico":               "Guadalajara",
    "Canada":               "Toronto",
    "United States":        "New York",
    "Costa Rica":           "Costa Rica",
    "United Kingdom":       "London",
    "Denmark":              "Copenhagen",
    "Spain":                "Madrid",
    "Serbia":               "Belgrade",
    "Iceland":              "Reykjavik",
    "Portugal":             "Lisbon",
    "Belgium":              "Brussels",
    "Norway":               "Oslo",
    "Hungary":              "Budapest",
    "Bulgaria":             "Sofia",
    "Slovenia":             "Ljubljana",
    "Greece":               "Athens",
    "France":               "Paris",
    "Sweden":               "Stockholm",
    "Netherlands":          "Amsterdam",
    "Poland":               "Warsaw",
    "Germany":              "Frankfurt",
    "Ireland":              "Dublin",
    "Romania":              "Bucharest",
    "Czech Republic":       "Prague",
    "Switzerland":          "Zurich",
    "Slovakia":             "Bratislava",
    "Croatia":              "Zagreb",
    "Austria":              "Vienna",
    "Italy":                "Milan",
    "Luxembourg":           "Luxembourg",
    "Albania":              "Tirana",
    "Latvia":               "Riga",
    "Finland":              "Helsinki",
    "Moldova":              "Chisinau",
    "Colombia":             "Bogota",
    "Chile":                "Santiago",
    "Argentina":            "Buenos Aires",
    "Peru":                 "Lima",
    "Brazil":               "Sao Paulo",
    "New Zealand":          "Auckland",
    "Australia":            "Sydney",
    # Regions — use geographic centroid
    "North America":        "Chicago",
    "Europe":               "Frankfurt",
    "South America":        "Sao Paulo",
    "Oceania":              "Sydney",
}


# ──── HAVERSINE ──── #

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def sort_by_distance(names: list[str], user_lat: float, user_lon: float,
                     lookup: dict[str, str] | None = None) -> list[str]:
    """
    Return `names` sorted nearest → furthest from (user_lat, user_lon).
    `lookup` maps name → city key in CITY_COORDS (used for countries).
    Items with no known coordinates are appended alphabetically at the end.
    """
    known, unknown = [], []
    for name in names:
        city   = (lookup or {}).get(name, name)
        coords = CITY_COORDS.get(city)
        if coords:
            dist = haversine(user_lat, user_lon, coords[0], coords[1])
            known.append((dist, name))
        else:
            unknown.append(name)
    known.sort(key=lambda x: x[0])
    return [n for _, n in known] + sorted(unknown)


# ──── GEO RESULT ──── #

class GeoResult:
    __slots__ = ("ip", "city", "country", "isp", "lat", "lon")

    def __init__(self, ip="", city="", country="", isp="", lat=0.0, lon=0.0):
        self.ip      = ip
        self.city    = city
        self.country = country
        self.isp     = isp
        self.lat     = lat
        self.lon     = lon

    def location_str(self) -> str:
        parts = [p for p in (self.city, self.country) if p]
        return ", ".join(parts) if parts else "Unknown"


# ──── GEO WORKER ──── #

class GeoWorker(QObject):
    """
    Fetches public IP + geo info from ip-api.com.
    Free endpoint, no API key required.
    """
    result = pyqtSignal(object)   # GeoResult
    error  = pyqtSignal(str)

    def run(self):
        import requests
        try:
            data = requests.get(
                "http://ip-api.com/json/?fields=status,message,"
                "country,city,isp,lat,lon,query",
                timeout=8,
            ).json()
            if data.get("status") != "success":
                self.error.emit(data.get("message", "Geo lookup failed"))
                return
            self.result.emit(GeoResult(
                ip      = data.get("query",   ""),
                city    = data.get("city",    ""),
                country = data.get("country", ""),
                isp     = data.get("isp",     ""),
                lat     = float(data.get("lat", 0)),
                lon     = float(data.get("lon", 0)),
            ))
        except Exception as e:
            self.error.emit(str(e))


# ──── GEO MANAGER ──── #

class GeoManager(QObject):
    result = pyqtSignal(object)
    error  = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread: QThread | None = None
        self._worker: GeoWorker | None = None

    def fetch(self):
        if self._thread and self._thread.isRunning():
            return
        self._thread = QThread()
        self._worker = GeoWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result.connect(self.result)
        self._worker.error.connect(self.error)
        self._worker.result.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()
