# E-commerce Customer Intelligence Platform
**SQL · Python · Power BI** — an end-to-end analytics pipeline that turns raw order data into customer segments, lifetime-value forecasts and churn risk, delivered through an interactive dashboard.

> **Data note:** this repo ships with a *synthetic* dataset (8,000 customers, 31K orders, 2023–2025, Olist-style schema) so it runs anywhere. To use real data (e.g. Olist or UCI Online Retail from Kaggle), drop CSVs with the same columns into `/data` and skip step 1. All figures below come from the synthetic data; replace them with your own after rerunning.

## Business questions answered
1. Who are our most valuable customers, and how concentrated is revenue?
2. Which customers are slipping away, and how much future revenue is at stake?
3. How do delivery delays affect satisfaction?
4. Which segments deserve which marketing action?

## Architecture
```
CSVs → SQLite (star schema + analytical views, SQL) → Python (RFM, K-Means, BG/NBD CLV, churn ML) → scored tables → Power BI (DAX, 4 pages)
```
| Layer | Files |
|---|---|
| SQL | `sql/01_schema.sql`, `02_star_schema.sql` (fact_orders + dim_customer/product/date), `03_analytical_views.sql` (CTEs, window functions: LAG, NTILE, cohort retention, Pareto) |
| Python | `01_generate_data` → `02_build_database` → `03_rfm_segmentation` → `04_clv_models` → `05_churn_model` → `06_export_for_powerbi` |
| Power BI | `powerbi/DAX_measures.md`, `DASHBOARD_BUILD_GUIDE.md`, `powerbi/data/*.csv` |

**Run it:** `pip install -r requirements.txt && ./python/run_all.sh`

## Results
| Metric | Value |
|---|---|
| Revenue (non-cancelled) | ₹88.0M across 31.3K orders, 7,882 customers; AOV ₹2,809 |
| Revenue growth | 2023 ₹21.1M → 2024 ₹32.2M (+53%) → 2025 ₹34.7M (+8%) — growth is flattening |
| Repeat purchase rate | 64.5% |
| Revenue concentration | Top 10% of customers = **43%** of revenue; top 20% = **62%** |
| Cohort retention | ~28% of a cohort orders again in month 1, ~16% in month 6 |
| Late delivery impact | Avg review: **4.42** on time → **3.81** (1–3d late) → **2.77** (4–6d) → **1.46** (7+d) |

### Segmentation (RFM + K-Means)
- **Champions** — 1,575 customers (20%) generate **43.5%** of lifetime revenue.
- **"Can't Lose Them"** — 952 high-frequency customers who have gone quiet (avg. 711 days since last order) still represent **19%** of lifetime revenue: the #1 win-back target.
- K-Means (k=4, log-scaled RFM) independently recovers VIP / Steady / Lapsing / Lost groups, cross-checking the rule-based segments.

### Customer lifetime value (BG/NBD + Gamma-Gamma, implemented with SciPy)
- Predicted 12-month revenue ≈ ₹16.9M; **top 20% of customers = 73.5%** of it.
- Validated on a hold-out: fit on data to Jun-2025, predicted Jul–Dec orders: predicted 4,022 vs actual 3,500 (**+14.9% over**), customer-level correlation 0.64. Decile-level predicted vs actual is well aligned at the top (2.97 vs 2.83 orders/customer in the top decile). The model slightly over-predicts the long tail; treat CLV as a ranking tool more than an exact forecast.

### Churn prediction (active customers only)
Population: customers who bought in the last 180 days. Target: no purchase in the next 180 days. Strict time split, no leakage.

| Model | ROC-AUC | Precision | Recall | F1 |
|---|---|---|---|---|
| **Logistic Regression** (used) | **0.744** | 0.738 | 0.645 | 0.688 |
| Gradient Boosting | 0.710 | 0.673 | 0.725 | 0.698 |

Recency and "recency relative to the customer's own purchase gap" are the strongest drivers. The simpler model won, so it is used for scoring. AUC 0.74 is a realistic, moderate result; the model is useful for prioritising outreach, not for certainty.

## Recommendations
1. **Win-back "Can't Lose Them" + High-risk customers:** rank by predicted CLV × churn probability (the Power BI "win-back list") and run personalised offers.
2. **Fix logistics:** orders delivered 4+ days late average 1.5–2.8 stars versus 4.4 on time; SLA penalties on slow carriers and proactive delay messaging protect repeat purchases.
3. **Protect Champions:** early access / loyalty perks; they are 20% of customers and 43% of revenue.
4. **Improve month-1 retention (28%):** a post-first-order nudge sequence (replenishment, cross-sell) is the cheapest lever.
5. **Re-accelerate acquisition:** growth slowed to +8% in 2025.

## Limitations
- Synthetic data: relationships (e.g. delay → review) are built in, so the real-data version will be noisier.
- BG/NBD assumes independent purchase and dropout processes and over-predicts the low-activity tail here.
- Churn labels depend on the 180-day horizon / active-window choice (parameters at the top of `05_churn_model.py`).

## Resume bullets
- Built an end-to-end customer analytics platform on **31K orders / 8K customers** using **SQL** (star schema, CTEs, window functions) and **Python** (pandas, scikit-learn, SciPy), automating the pipeline from raw CSVs to dashboard-ready tables.
- Segmented customers with **RFM + K-Means**, showing **Champions (20% of customers) drive 43% of revenue** and identifying a dormant high-value group worth **19%** of lifetime revenue for win-back.
- Implemented **BG/NBD + Gamma-Gamma CLV models** (validated on a 6-month hold-out) and a **churn model (ROC-AUC 0.74, time-based split)** to rank customers by revenue-at-risk.
- Designed a **4-page Power BI dashboard** with DAX (YoY, retention, CLV, revenue-at-risk), cohort heatmap and drill-through; quantified that **7+ day delivery delays cut review scores from 4.4 to 1.5**.
