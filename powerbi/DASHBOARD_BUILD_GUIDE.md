# Power BI Dashboard Build Guide (≈ 60–90 minutes)

A `.pbix` file can only be created in Power BI Desktop, so this guide gives you the exact pages, visuals and fields.
All data is pre-cleaned in `powerbi/data/`. DAX is in `DAX_measures.md`.

**Theme:** dark-blue `#1F4E79` primary, orange `#E07B00` accent, light-grey canvas `#F3F4F6`. Font: Segoe UI.
**Global slicers (sync across all pages):** Year, State (`dim_customer_360[state]`), Product Category.

## 1. Get data
Home → Get Data → Text/CSV → load all 10 files in `powerbi/data/` (Transform only to set Date types). Then build the relationships from `DAX_measures.md`.

## Page 1 — Executive Overview
| Visual | Fields |
|---|---|
| 5 KPI cards | Revenue, Orders, Customers, AOV, Revenue YoY % |
| Line + column chart | X: `dim_date[year_month]`; Columns: Revenue; Line: Revenue 3M Rolling Avg |
| Clustered bar | Revenue by `dim_product[category]` |
| Map / filled map | Revenue by `dim_customer_360[state]` |
| Donut | Orders by `fact_orders[payment_type]` |
| Pareto chart (column + line) | `v_pareto[decile]` / revenue share %, cumulative % line |

## Page 2 — Customer Segments (RFM & K-Means)
| Visual | Fields |
|---|---|
| Treemap | Group: `rfm_segment`, Values: Revenue |
| Bar | Customers by `rfm_segment` (sort by `Segment Order`) |
| Table | segment, Customers, Revenue, Segment Revenue Share %, avg recency, avg frequency |
| Scatter | X: `frequency`, Y: `monetary`, Legend: `kmeans_segment`, Size: `clv_12m` |
| Cards | Top 20% Revenue Share, Repeat Purchase Rate % |
| **Drill-through page** "Customer 360" | Fields: customer_id, state, segment, CLV, churn probability, orders list |

## Page 3 — Retention, CLV & Churn
| Visual | Fields |
|---|---|
| Matrix (heatmap) | Rows: `v_cohort_retention[cohort]`, Columns: `month_n` (0–12), Values: `retention_pct`; conditional format → background colour scale |
| Column chart | Customers by `risk_band` (High / Medium / Low / Already Lost) |
| Cards | At-Risk Customers, Revenue at Risk, Avg CLV per Customer |
| Table — **Win-back list** | customer_id, state, rfm_segment, clv_12m, churn_probability; filter `risk_band = High`; sort by `clv_12m` desc; Top N = 50 |
| Bar | Total CLV by `clv_tier` |

## Page 4 — Product & Operations
| Visual | Fields |
|---|---|
| Matrix | Category × Revenue, Units, Avg Review Score, Return Rate % (data bars) |
| Column chart | `Delay Bucket` vs Avg Review Score (**the headline insight**) |
| Cards | On-Time Delivery %, Avg Delivery Days, Return Rate % |
| Line | Avg Review Score by `year_month` |

## Polish checklist
- Add a title bar + navigation buttons (Insert → Buttons → Navigator → Page navigator)
- Add a "Key insight" text box on each page (see README)
- Add tooltips pages for segments; turn on drill-through for `customer_id`
- Export a PDF + screenshots into `/reports` for your portfolio / GitHub
