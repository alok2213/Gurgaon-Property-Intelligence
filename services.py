"""
Data + ML services for the Gurgaon Real Estate app.

Everything the notebooks do (model pipeline, analytics, linear-model insights,
content based recommender) is wrapped here so Flask routes stay thin.
"""
from __future__ import annotations

import ast
import json
import pickle
import re
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ART_DIR = BASE_DIR / "artifacts"
ART_DIR.mkdir(exist_ok=True)

FURNISHING_MAP = {0.0: "unfurnished", 1.0: "semifurnished", 2.0: "furnished"}

NUM_COLS = ["bedRoom", "bathroom", "built_up_area", "servant room", "store room"]
ORD_COLS = ["property_type", "sector", "balcony", "agePossession",
            "furnishing_type", "luxury_category", "floor_category"]
OHE_COLS = ["sector", "agePossession"]
FEATURE_ORDER = ["property_type", "sector", "bedRoom", "bathroom", "balcony",
                 "agePossession", "built_up_area", "servant room", "store room",
                 "furnishing_type", "luxury_category", "floor_category"]

_lock = threading.Lock()


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def pretty_sector(s: str) -> str:
    return s.title() if not s.startswith("sector") else "Sector " + s.split()[-1]


def _sector_sort_key(s: str):
    m = re.match(r"sector (\d+)", s)
    return (0, int(m.group(1)), s) if m else (1, 0, s)


def _clean(obj):
    """Make numpy / NaN values JSON safe."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if (np.isnan(obj) or np.isinf(obj)) else float(obj)
    return obj


# --------------------------------------------------------------------------
# 1. Price prediction model
# --------------------------------------------------------------------------
def _load_model_frame() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "model_data.csv")
    df["furnishing_type"] = df["furnishing_type"].replace(FURNISHING_MAP)
    df["balcony"] = df["balcony"].astype(str)
    return df


def _build_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_COLS),
            ("cat", OrdinalEncoder(), ORD_COLS),
            ("cat1", OneHotEncoder(drop="first", sparse_output=False), OHE_COLS),
        ],
        remainder="passthrough",
    )
    return Pipeline([
        ("preprocessor", pre),
        ("regressor", RandomForestRegressor(n_estimators=500, n_jobs=-1, random_state=42)),
    ])


def train_model(verbose: bool = True) -> dict:
    """Train the final model from the notebook (RandomForest on log1p(price))."""
    df = _load_model_frame()
    X = df.drop(columns=["price"])[FEATURE_ORDER]
    y = np.log1p(df["price"])

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    probe = _build_pipeline().fit(X_tr, y_tr)
    pred = probe.predict(X_te)
    r2 = float(r2_score(y_te, pred))
    mae = float(mean_absolute_error(np.expm1(y_te), np.expm1(pred)))

    pipe = _build_pipeline().fit(X, y)
    meta = {
        "sklearn": sklearn.__version__,
        "rows": int(len(df)),
        "r2": round(r2, 4),
        "mae_cr": round(mae, 3),
        "trained_at": datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    with open(ART_DIR / "pipeline.pkl", "wb") as f:
        pickle.dump(pipe, f)
    (ART_DIR / "meta.json").write_text(json.dumps(meta))
    if verbose:
        print(f"[train] R2={r2:.3f}  MAE={mae:.3f} Cr  rows={len(df)}")
    return meta


class PriceModel:
    def __init__(self):
        self.df = _load_model_frame()
        self.pipe, self.meta = self._load_or_train()
        self.sectors = sorted(self.df["sector"].unique(), key=_sector_sort_key)

    def _load_or_train(self):
        pkl, meta_p = ART_DIR / "pipeline.pkl", ART_DIR / "meta.json"
        if pkl.exists() and meta_p.exists():
            try:
                meta = json.loads(meta_p.read_text())
                if meta.get("sklearn") == sklearn.__version__:
                    with open(pkl, "rb") as f:
                        return pickle.load(f), meta
            except Exception as exc:  # corrupted / incompatible pickle
                print("[model] reload failed, retraining:", exc)
        print("[model] training model (first run, takes ~20s)...")
        meta = train_model()
        with open(pkl, "rb") as f:
            return pickle.load(f), meta

    # ---- options for the form ------------------------------------------
    def form_options(self) -> dict:
        return {
            "sectors": [{"value": s, "label": pretty_sector(s)} for s in self.sectors],
            "balcony": ["0", "1", "2", "3", "3+"],
            "age": ["New Property", "Relatively New", "Moderately Old",
                    "Old Property", "Under Construction"],
        }

    # ---- inference -----------------------------------------------------
    def validate(self, p: dict) -> tuple[pd.DataFrame, list[str]]:
        errors = []
        opts = self.form_options()
        row = {}
        row["property_type"] = str(p.get("property_type", "")).lower()
        if row["property_type"] not in ("flat", "house"):
            errors.append("Select a valid property type.")
        row["sector"] = str(p.get("sector", "")).lower()
        if row["sector"] not in self.sectors:
            errors.append("Select a valid sector.")
        row["balcony"] = str(p.get("balcony", ""))
        if row["balcony"] not in opts["balcony"]:
            errors.append("Select a valid balcony count.")
        row["agePossession"] = str(p.get("agePossession", ""))
        if row["agePossession"] not in opts["age"]:
            errors.append("Select a valid property age.")
        row["furnishing_type"] = str(p.get("furnishing_type", "")).lower()
        if row["furnishing_type"] not in FURNISHING_MAP.values():
            errors.append("Select a valid furnishing type.")
        row["luxury_category"] = str(p.get("luxury_category", ""))
        if row["luxury_category"] not in ("Low", "Medium", "High"):
            errors.append("Select a valid luxury category.")
        row["floor_category"] = str(p.get("floor_category", ""))
        if row["floor_category"] not in ("Low Floor", "Mid Floor", "High Floor"):
            errors.append("Select a valid floor category.")

        def num(key, label, lo, hi, as_int=True):
            try:
                v = float(p.get(key))
            except (TypeError, ValueError):
                errors.append(f"{label} must be a number.")
                return 0
            if not lo <= v <= hi:
                errors.append(f"{label} must be between {lo} and {hi}.")
            return int(v) if as_int else v

        row["bedRoom"] = num("bedRoom", "Bedrooms", 1, 12)
        row["bathroom"] = num("bathroom", "Bathrooms", 1, 12)
        row["built_up_area"] = num("built_up_area", "Built-up area", 100, 15000, False)
        row["servant room"] = 1 if str(p.get("servant_room", "0")) in ("1", "true", "True") else 0
        row["store room"] = 1 if str(p.get("store_room", "0")) in ("1", "true", "True") else 0
        return pd.DataFrame([row])[FEATURE_ORDER], errors

    def predict(self, frame: pd.DataFrame) -> dict:
        pre = self.pipe.named_steps["preprocessor"]
        rf = self.pipe.named_steps["regressor"]
        Xt = pre.transform(frame)
        tree_preds = np.expm1(np.array([t.predict(Xt)[0] for t in rf.estimators_]))
        point = float(np.expm1(self.pipe.predict(frame)[0]))
        low, high = np.percentile(tree_preds, [10, 90])
        low, high = min(low, point), max(high, point)
        area = float(frame["built_up_area"].iloc[0])
        return {
            "price_cr": round(point, 2),
            "low_cr": round(float(low), 2),
            "high_cr": round(float(high), 2),
            "price_per_sqft": int(round(point * 1e7 / area)) if area else None,
            "confidence_spread_pct": round(float((high - low) / point * 100 / 2), 1),
        }

    def comparables(self, frame: pd.DataFrame, n: int = 5) -> list[dict]:
        r = frame.iloc[0]
        d = self.df
        pool = d[(d["sector"] == r["sector"]) & (d["property_type"] == r["property_type"])]
        same_bhk = pool[pool["bedRoom"] == r["bedRoom"]]
        if len(same_bhk) >= 3:
            pool = same_bhk
        if len(pool) < 3:
            pool = d[(d["property_type"] == r["property_type"]) & (d["bedRoom"] == r["bedRoom"])]
        pool = pool.assign(_diff=(pool["built_up_area"] - r["built_up_area"]).abs()).nsmallest(n, "_diff")
        return [{
            "sector": pretty_sector(x.sector),
            "type": x.property_type.title(),
            "bhk": int(x.bedRoom),
            "area": int(x.built_up_area),
            "price_cr": round(float(x.price), 2),
            "age": x.agePossession,
        } for x in pool.itertuples()]


# --------------------------------------------------------------------------
# 2. Analytics (visualisation module)
# --------------------------------------------------------------------------
class Analytics:
    def __init__(self):
        df = pd.read_csv(DATA_DIR / "viz_data.csv")
        df["sector_label"] = df["sector"].map(pretty_sector)
        self.df = df
        self.sectors = sorted(df["sector"].unique(), key=_sector_sort_key)
        self.features = json.loads((DATA_DIR / "feature_freq.json").read_text())

    def sector_options(self):
        return [{"value": s, "label": pretty_sector(s)} for s in self.sectors]

    def summary(self) -> dict:
        d = self.df
        return {
            "listings": int(len(d)),
            "sectors": int(d["sector"].nunique()),
            "avg_price": round(float(d["price"].mean()), 2),
            "median_price": round(float(d["price"].median()), 2),
            "avg_ppsf": int(d["price_per_sqft"].mean()),
        }

    def top_sectors(self, n: int = 10) -> list[dict]:
        g = (self.df.groupby("sector_label")
             .agg(ppsf=("price_per_sqft", "mean"), price=("price", "mean"), n=("price", "size"))
             .query("n >= 8").sort_values("ppsf", ascending=False).head(n))
        return [{"sector": i, "ppsf": int(r.ppsf), "price": round(r.price, 2), "n": int(r.n)}
                for i, r in g.iterrows()]

    def payload(self, sector: str = "overall") -> dict:
        d = self.df
        sub = d if sector == "overall" else d[d["sector"] == sector]
        if sub.empty:
            sub = d
            sector = "overall"

        g = (d.groupby("sector_label")
             .agg(price=("price", "mean"), ppsf=("price_per_sqft", "mean"),
                  area=("built_up_area", "mean"), lat=("latitude", "mean"),
                  lon=("longitude", "mean"), n=("price", "size")).reset_index())
        map_pts = [{"sector": r.sector_label, "price": round(r.price, 2), "ppsf": int(r.ppsf),
                    "area": int(r.area), "lat": r.lat, "lon": r.lon, "n": int(r.n)}
                   for r in g.itertuples()]

        sc = sub.sample(min(len(sub), 1500), random_state=1)
        scatter = {
            "x": sc["built_up_area"].round(0).tolist(), "y": sc["price"].tolist(),
            "bhk": sc["bedRoom"].tolist(), "sector": sc["sector_label"].tolist(),
        }
        box = {str(b): sub[sub["bedRoom"] == b]["price"].tolist()
               for b in sorted(sub["bedRoom"].unique()) if b <= 4}
        pie = sub["bedRoom"].value_counts().sort_index()
        pie = {"labels": [f"{int(k)} BHK" for k in pie.index], "values": pie.tolist()}
        dist = {t: sub[sub["property_type"] == t]["price"].clip(upper=sub["price"].quantile(0.99)).tolist()
                for t in ("flat", "house")}
        by_type = sub["property_type"].value_counts().to_dict()

        kpi = {
            "listings": int(len(sub)),
            "avg_price": round(float(sub["price"].mean()), 2),
            "median_price": round(float(sub["price"].median()), 2),
            "avg_ppsf": int(sub["price_per_sqft"].mean()),
            "avg_area": int(sub["built_up_area"].mean()),
            "flats": int(by_type.get("flat", 0)),
            "houses": int(by_type.get("house", 0)),
        }
        return _clean({
            "sector": sector, "kpi": kpi, "map": map_pts, "scatter": scatter,
            "box": box, "pie": pie, "dist": dist, "top_sectors": self.top_sectors(15),
        })


# --------------------------------------------------------------------------
# 3. Insights (Ridge regression coefficients on standardised features)
# --------------------------------------------------------------------------
LABELS = {
    "bedRoom": ("Bedrooms", "per extra bedroom"),
    "bathroom": ("Bathrooms", "per extra bathroom"),
    "built_up_area": ("Built-up area", "per extra 100 sq.ft."),
    "servant room": ("Servant room", "if available"),
    "furnishing_type": ("Furnishing level", "per step up (unfurnished → semi → full)"),
    "luxury_category": ("Luxury level", "per step up (Low → Medium → High)"),
    "property_type": ("House (vs flat)", "house instead of flat"),
    "agePossession_old": ("Old property", "vs. new property"),
    "agePossession_under construction": ("Under construction", "vs. new property"),
}
UNIT_SCALE = {"built_up_area": 100}


def build_insights() -> dict:
    df = pd.read_csv(DATA_DIR / "model_data.csv").drop(columns=["store room", "floor_category", "balcony"])
    df["agePossession"] = df["agePossession"].replace({
        "Relatively New": "new", "Moderately Old": "old", "New Property": "new",
        "Old Property": "old", "Under Construction": "under construction"})
    df["property_type"] = df["property_type"].replace({"flat": 0, "house": 1}).astype(int)
    df["luxury_category"] = df["luxury_category"].replace({"Low": 0, "Medium": 1, "High": 2}).astype(int)
    new_df = pd.get_dummies(df, columns=["sector", "agePossession"], drop_first=True)
    X = new_df.drop(columns=["price"]).astype(float)
    y = np.log1p(new_df["price"])

    scaler = StandardScaler()
    Xs = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)
    cv_r2 = cross_val_score(LinearRegression(), Xs, y,
                            cv=KFold(10, shuffle=True, random_state=42), scoring="r2").mean()
    ridge = Ridge(alpha=0.0001).fit(Xs, y)

    rows = []
    for col, coef, std in zip(X.columns, ridge.coef_, scaler.scale_):
        if col not in LABELS:
            continue
        per_unit = coef / std * UNIT_SCALE.get(col, 1)
        rows.append({
            "key": col, "label": LABELS[col][0], "unit": LABELS[col][1],
            "std_coef": round(float(coef), 4),
            "pct_per_unit": round(float(np.expm1(per_unit) * 100), 1),
        })
    rows.sort(key=lambda r: abs(r["std_coef"]), reverse=True)
    return {"features": rows, "cv_r2": round(float(cv_r2), 3), "n": int(len(df))}


# --------------------------------------------------------------------------
# 4. Recommender
# --------------------------------------------------------------------------
def _parse_price_details(detail_str: str) -> dict:
    try:
        details = ast.literal_eval(detail_str)
    except Exception:
        try:
            details = json.loads(detail_str.replace("'", '"'))
        except Exception:
            return {}
    out = {}
    for bhk, det in details.items():
        out[f"building type_{bhk}"] = det.get("building_type")
        parts = det.get("area", "").split("-")
        try:
            lo = float(parts[0].replace(",", "").replace(" sq.ft.", "").strip())
            hi = float(parts[-1].replace(",", "").replace(" sq.ft.", "").strip())
            out[f"area low {bhk}"], out[f"area high {bhk}"] = lo, hi
        except Exception:
            out[f"area low {bhk}"] = out[f"area high {bhk}"] = None
        pr = det.get("price-range", "").split("-")
        if len(pr) == 2:
            try:
                lo = float(pr[0].replace("₹", "").replace(" Cr", "").replace(" L", "").strip())
                hi = float(pr[1].replace("₹", "").replace(" Cr", "").replace(" L", "").strip())
                if "L" in pr[0]:
                    lo /= 100
                if "L" in pr[1]:
                    hi /= 100
                out[f"price low {bhk}"], out[f"price high {bhk}"] = lo, hi
            except Exception:
                out[f"price low {bhk}"] = out[f"price high {bhk}"] = None
    return out


def _distance_m(s):
    try:
        v = float(s.split()[0].replace(",", ""))
    except Exception:
        return None
    low = s.lower()
    if "km" in low:
        return v * 1000
    if "meter" in low:
        return v
    return None


class Recommender:
    CONFIGS = ["1 BHK", "2 BHK", "3 BHK", "4 BHK", "5 BHK", "6 BHK", "1 RK", "Land"]

    def __init__(self):
        df = pd.read_csv(DATA_DIR / "apartments.csv").drop(22).reset_index(drop=True)
        self.df = df
        self.names = df["PropertyName"].tolist()
        self.idx = {n: i for i, n in enumerate(self.names)}

        df["fac_list"] = df["TopFacilities"].apply(lambda s: re.findall(r"'(.*?)'", s))
        df["loc_dict"] = df["LocationAdvantages"].apply(ast.literal_eval)
        df["price_dict"] = df["PriceDetails"].apply(lambda s: ast.literal_eval(s) if isinstance(s, str) else {})

        # (1) facilities similarity
        tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        m = tfidf.fit_transform(df["fac_list"].apply(" ".join))
        sim1 = cosine_similarity(m)

        # (2) price / configuration similarity
        rows = []
        for _, r in df.iterrows():
            f = _parse_price_details(r["PriceDetails"])
            row = {}
            for c in self.CONFIGS:
                for k in ("building type", "area low", "area high", "price low", "price high"):
                    row[f"{k}_{c}"] = f.get(f"{k}_{c}")
            rows.append(row)
        pdf = pd.DataFrame(rows, index=df["PropertyName"])
        pdf["building type_Land"] = pdf["building type_Land"].replace({"": "Land"})
        cats = pdf.select_dtypes(include=["object", "string"]).columns.tolist()
        pdf = pd.get_dummies(pdf, columns=cats, drop_first=True).astype(float).fillna(0)
        sim2 = cosine_similarity(StandardScaler().fit_transform(pdf))

        # (3) location similarity
        loc = pd.DataFrame([{k: _distance_m(v) for k, v in d.items()} for d in df["loc_dict"]],
                           index=df["PropertyName"])
        self.loc_df = loc.copy()
        loc = loc.fillna(54000)
        sim3 = cosine_similarity(StandardScaler().fit_transform(loc))

        self.sim = 30 * sim1 + 20 * sim2 + 8 * sim3
        self.max_score = 58.0

        counts = self.loc_df.notna().sum().sort_values(ascending=False)
        self.locations = sorted(counts[counts >= 2].index.tolist())

    # ---- helpers --------------------------------------------------------
    @staticmethod
    def _sector(subname: str) -> str:
        m = re.search(r"in (.+?),\s*Gurgaon", subname or "")
        return m.group(1) if m else ""

    def _brief(self, i: int) -> dict:
        r = self.df.iloc[i]
        cfg = r["price_dict"]
        lows, highs = [], []
        for v in cfg.values():
            pr = v.get("price-range", "")
            lows.append(pr)
        return {
            "name": r["PropertyName"],
            "sub": r["PropertySubName"],
            "area": self._sector(r["PropertySubName"]),
            "configs": list(cfg.keys()),
            "price_hint": next((p for p in lows if p), ""),
            "facilities": r["fac_list"][:4],
            "link": r["Link"],
        }

    # ---- public API ------------------------------------------------------
    def nearby(self, location: str, radius_km: float) -> list[dict]:
        if location not in self.loc_df.columns:
            return []
        col = self.loc_df[location].dropna()
        col = col[col <= radius_km * 1000].sort_values()
        out = []
        for name, meters in col.items():
            b = self._brief(self.idx[name])
            b["distance_m"] = int(meters)
            b["distance_txt"] = f"{meters/1000:.1f} km" if meters >= 1000 else f"{int(meters)} m"
            out.append(b)
        return out

    def detail(self, name: str) -> dict | None:
        if name not in self.idx:
            return None
        i = self.idx[name]
        r = self.df.iloc[i]
        d = self._brief(i)
        d["facilities"] = r["fac_list"]
        d["prices"] = [{"config": k, "type": v.get("building_type", ""),
                        "area": v.get("area", ""), "price": v.get("price-range", "")}
                       for k, v in r["price_dict"].items()]
        d["nearby"] = [{"place": k, "dist": v} for k, v in list(r["loc_dict"].items())[:8]]
        return d

    def similar(self, name: str, n: int = 6) -> list[dict]:
        if name not in self.idx:
            return []
        i = self.idx[name]
        order = np.argsort(-self.sim[i])
        out = []
        for j in order:
            if j == i:
                continue
            b = self._brief(int(j))
            b["score"] = int(max(0, min(100, round(self.sim[i][j] / self.max_score * 100))))
            out.append(b)
            if len(out) == n:
                break
        return out


# --------------------------------------------------------------------------
# lazy singletons
# --------------------------------------------------------------------------
_cache: dict = {}


def get(name: str):
    with _lock:
        if name not in _cache:
            _cache[name] = {
                "model": PriceModel, "analytics": Analytics,
                "recommender": Recommender, "insights": build_insights,
            }[name]()
        return _cache[name]
