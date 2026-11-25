"""Gurgaon Real Estate Intelligence - Flask application."""
import os

from flask import Flask, jsonify, render_template, request

import services

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

PIPELINE_STEPS = [
    ("Data Gathering", "Listings for flats, independent houses and plots scraped into raw datasets."),
    ("Cleaning & Preprocessing", "Standardised prices, areas and text fields; removed duplicates and junk rows."),
    ("Feature Engineering", "Derived built-up area, luxury score, floor category and furnishing level."),
    ("EDA", "Univariate, multivariate and profiling analysis to understand distributions."),
    ("Outlier Treatment", "Removed unrealistic prices, areas and price-per-sqft values."),
    ("Missing Value Imputation", "Filled gaps in area, bedrooms, bathrooms and floor using related columns."),
    ("Feature Selection", "Kept the features that actually move price (multiple selection techniques)."),
    ("Model Selection", "Compared 11 regressors; tuned Random Forest on log-transformed price."),
    ("Data Visualization", "Geo map, word cloud and interactive charts for market exploration."),
    ("Recommender System", "Content-based apartment similarity: facilities, price/config and location."),
    ("Insights", "Ridge regression coefficients explain what drives property prices."),
]


@app.context_processor
def inject_globals():
    return {"endpoint": request.endpoint}


# ------------------------------------------------------------------ pages
@app.route("/")
def home():
    a = services.get("analytics")
    m = services.get("model")
    return render_template("home.html", summary=a.summary(), meta=m.meta,
                           top=a.top_sectors(6), opts=m.form_options())


@app.route("/predict")
def predict_page():
    m = services.get("model")
    return render_template("predict.html", opts=m.form_options(), meta=m.meta)


@app.route("/analytics")
def analytics_page():
    a = services.get("analytics")
    return render_template("analytics.html", sectors=a.sector_options())


@app.route("/recommender")
def recommender_page():
    r = services.get("recommender")
    return render_template("recommender.html", locations=r.locations, names=sorted(r.names))


@app.route("/insights")
def insights_page():
    return render_template("insights.html", ins=services.get("insights"),
                           meta=services.get("model").meta)


@app.route("/about")
def about_page():
    return render_template("about.html", steps=PIPELINE_STEPS, meta=services.get("model").meta)


# -------------------------------------------------------------------- API
@app.post("/api/predict")
def api_predict():
    payload = request.get_json(silent=True) or request.form.to_dict()
    m = services.get("model")
    frame, errors = m.validate(payload)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    result = m.predict(frame)
    result["comparables"] = m.comparables(frame)
    result["mae_cr"] = m.meta["mae_cr"]
    return jsonify({"ok": True, **result})


@app.get("/api/analytics")
def api_analytics():
    sector = request.args.get("sector", "overall").lower()
    return jsonify(services.get("analytics").payload(sector))


@app.get("/api/features")
def api_features():
    return jsonify(services.get("analytics").features)


@app.get("/api/recommend/nearby")
def api_nearby():
    loc = request.args.get("location", "")
    try:
        radius = max(0.5, min(float(request.args.get("radius", 5)), 50))
    except ValueError:
        radius = 5
    return jsonify({"results": services.get("recommender").nearby(loc, radius)})


@app.get("/api/recommend/similar")
def api_similar():
    name = request.args.get("name", "")
    r = services.get("recommender")
    detail = r.detail(name)
    if not detail:
        return jsonify({"ok": False, "error": "Apartment not found"}), 404
    return jsonify({"ok": True, "detail": detail, "similar": r.similar(name)})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# ----------------------------------------------------------------- errors
@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Not found"}), 404
    return render_template("error.html", code=404, msg="This page doesn't exist."), 404


@app.errorhandler(500)
def server_error(_):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Server error"}), 500
    return render_template("error.html", code=500, msg="Something went wrong on our side."), 500


if __name__ == "__main__":
    # Warm up heavy objects once so the first page load is fast.
    for name in ("model", "analytics", "recommender", "insights"):
        services.get(name)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
