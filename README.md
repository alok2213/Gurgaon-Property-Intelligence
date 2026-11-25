# Gurgaon Property Intelligence

An end-to-end data science project on the Gurgaon real-estate market, delivered as a Flask web app. It estimates property prices with machine learning, lets you explore market trends through interactive charts, and recommends similar apartments.

![Screenshot](docs/screenshot.png)

## Overview

Property prices in Gurgaon vary widely by sector, size, age and amenities, which makes it hard for a buyer or seller to know what a fair price looks like. This project covers the full workflow, from raw listings to a working tool:

1. Clean and engineer features from scraped property listings.
2. Train a regression model to predict price (in crore ₹).
3. Explain which features drive price.
4. Serve everything through a simple web interface.

## Features

| Page | URL | What it does |
|---|---|---|
| Overview | `/` | Quick estimate, dataset stats and the priciest sectors |
| Price estimator | `/predict` | Predicted price in Cr, a likely price range, price per sq ft and similar listings |
| Market analytics | `/analytics` | Sector map, area vs price, BHK box plot, flat vs house, bedroom mix, top sectors, amenities word cloud (with sector filter) |
| Find apartments | `/recommender` | Search by landmark and radius, or get similar-apartment recommendations |
| Price drivers | `/insights` | How much each feature moves the price, from a Ridge regression |
| How it works | `/about` | Pipeline steps and model metrics |

## Model performance

| Item | Value |
|---|---|
| Algorithm | Random Forest (500 trees) |
| Target | `log1p(price)` |
| Train / test split | 80 / 20, `random_state=42` |
| R² (held-out test set) | ~0.91 |
| Mean absolute error | ~0.49 Cr |
| Training rows | 3,554 listings (2,804 flats, 750 houses, 104 sectors) |

Eleven regressors were compared during model selection and Random Forest performed best after tuning. The price range shown in the app is the 10th to 90th percentile of the individual tree predictions.

The Ridge regression used on the Price drivers page reaches a cross-validated R² of about 0.85, so its coefficients are a reasonable guide to which features matter, though they explain rather than predict.

## Recommender system

Similar apartments are found with a content-based approach that blends three cosine-similarity scores:

- **Facilities:** TF-IDF on each apartment's top facilities (weight 30).
- **Price and configuration:** scaled price details per BHK type (weight 20).
- **Location:** scaled distances to nearby landmarks (weight 8).

The combined score is normalised to 0-100 for display. The landmark search filters apartments within a chosen radius (0.5 to 50 km).

## Project pipeline

1. Data gathering
2. Cleaning and preprocessing
3. Feature engineering (built-up area, luxury score, floor category, furnishing level)
4. Exploratory data analysis
5. Outlier treatment
6. Missing value imputation
7. Feature selection
8. Model selection
9. Data visualisation
10. Recommender system
11. Insights from linear models

## Getting started

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py                     # http://localhost:5000
```

The first start trains the model (about 20-30 seconds) and caches it in `artifacts/`. Later starts are fast. To retrain after changing the data, run:

```bash
python train.py
```

## API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/predict` | Returns predicted price, range, price per sq ft and comparable listings |
| GET | `/api/analytics?sector=<name>` | Chart data for one sector or `overall` |
| GET | `/api/features` | Amenity frequency data |
| GET | `/api/recommend/nearby?location=<name>&radius=<km>` | Apartments near a landmark |
| GET | `/api/recommend/similar?name=<apartment>` | Apartment details and similar apartments |
| GET | `/health` | Health check |

Example request:

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "property_type": "flat", "sector": "sector 36",
    "bedRoom": 3, "bathroom": 2, "balcony": "2",
    "agePossession": "New Property", "built_up_area": 1250,
    "servant_room": 0, "store_room": 0,
    "furnishing_type": "semifurnished",
    "luxury_category": "Medium", "floor_category": "Mid Floor"
  }'
```

## Project structure

```
gurgaon_app/
├── app.py              # Flask routes and JSON APIs
├── services.py         # Price model, analytics, insights and recommender
├── train.py            # Retrains the model and refreshes artifacts/
├── requirements.txt    # Python dependencies
├── data/
│   ├── model_data.csv      # Cleaned data used to train the price model
│   ├── viz_data.csv        # Data behind the analytics charts
│   ├── apartments.csv      # Apartment details for the recommender
│   └── feature_freq.json   # Amenity frequencies for the word cloud
├── artifacts/          # Cached model (created on first run)
├── templates/          # Jinja pages (home, predict, analytics, ...)
├── static/
│   ├── css/style.css   # Styles
│   └── js/             # Page scripts (predict, analytics, recommender)
└── docs/
    └── screenshot.png
```

## Tech stack

Python, Flask, scikit-learn, pandas, NumPy, Jinja2, Plotly.js, HTML, CSS and vanilla JavaScript.

## Dataset

Property listings for flats and independent houses in Gurgaon, collected by scraping and cleaned in the notebooks. After preprocessing, the model dataset has 3,554 rows and 13 columns: property type, sector, price, bedrooms, bathrooms, balconies, property age, built-up area, servant room, store room, furnishing type, luxury category and floor category. A separate set of 246 apartment records powers the recommender.

## Limitations

- Prices are estimates from listing data, not official valuations, and are not financial or legal advice.
- The data is a snapshot, so predictions drift as the market changes. Retrain with fresh data to keep them current.
- Sectors with few listings give less reliable estimates, and the model does not cover plots or commercial property.
- The model uses sector as a category, so it does not use exact latitude and longitude or distance to metro, schools or hospitals.
- The app needs an internet connection in the browser, because Plotly.js and fonts load from CDNs.
- Built as a learning and portfolio project, not for production use. Run it with a production WSGI server (for example Gunicorn) if you deploy it.

## License

Released under the MIT License. See [LICENSE](LICENSE).
