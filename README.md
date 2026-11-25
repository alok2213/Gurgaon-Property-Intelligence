# Gurgaon Property Intelligence (Flask)

Professional web frontend for the Gurgaon real-estate data science project.

## Pages
| Page | URL | What it does |
|---|---|---|
| Overview | `/` | Hero + quick estimate, dataset stats, priciest sectors |
| Price estimator | `/predict` | Random Forest price in Cr, likely range, similar listings |
| Market analytics | `/analytics` | Sector map, area-vs-price, BHK box plot, flat vs house, bedroom mix, top sectors, amenities cloud (sector filter) |
| Find apartments | `/recommender` | Search by landmark + radius, and similar-apartment recommender |
| Price drivers | `/insights` | Ridge-regression effect of each feature on price |
| How it works | `/about` | Pipeline steps and model metrics |

## Run
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                      # http://localhost:5000
```
First start trains the model (~20-30 s) and caches it in `artifacts/`. Later starts are fast.
Retrain after changing data: `python train.py`.

## Structure
```
app.py            Flask routes + JSON APIs
services.py       Model, analytics, insights, recommender (notebook logic)
train.py          Retrain model
data/             CSVs used by the app (copied from your Datasets / notebooks)
templates/        Jinja pages      static/css, static/js   Styling and charts
```
Charts use Plotly.js and fonts load from CDNs, so the browser needs internet.
