# DAX Measures

Create a blank table called `_Measures` (Home → Enter Data) and store all measures there.

## Data model (Model view)
Load every CSV in `powerbi/data/`. Create these relationships (all Many-to-One, single direction):

| From (many) | To (one) |
|---|---|
| `fact_orders[customer_id]` | `dim_customer_360[customer_id]` |
| `fact_orders[order_date]` | `dim_date[date_key]` |
| `fact_order_items[order_id]` | `fact_orders[order_id]` *(set cross-filter: Both)* |
| `fact_order_items[product_id]` | `dim_product[product_id]` |

Mark `dim_date` as the **Date table** (column `date_key`; set data type = Date). Set `order_date` and `date_key` to Date type.
Add a calculated column on `dim_customer_360` to order the segment legend:
```DAX
Segment Order =
SWITCH ( dim_customer_360[rfm_segment],
  "Champions",1, "Loyal",2, "New / Promising",3, "Needs Attention",4,
  "At Risk",5, "Cant Lose Them",6, "Hibernating / Lost",7 )
```

## Core KPIs
```DAX
Revenue = CALCULATE ( SUM ( fact_orders[revenue] ), fact_orders[order_status] <> "cancelled" )

Orders = CALCULATE ( DISTINCTCOUNT ( fact_orders[order_id] ), fact_orders[order_status] <> "cancelled" )

Customers = CALCULATE ( DISTINCTCOUNT ( fact_orders[customer_id] ), fact_orders[order_status] <> "cancelled" )

AOV = DIVIDE ( [Revenue], [Orders] )

Revenue per Customer = DIVIDE ( [Revenue], [Customers] )
```

## Time intelligence
```DAX
Revenue PY = CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( dim_date[date_key] ) )

Revenue YoY % = DIVIDE ( [Revenue] - [Revenue PY], [Revenue PY] )

Revenue MoM % =
VAR prev = CALCULATE ( [Revenue], DATEADD ( dim_date[date_key], -1, MONTH ) )
RETURN DIVIDE ( [Revenue] - prev, prev )

Revenue YTD = TOTALYTD ( [Revenue], dim_date[date_key] )

Revenue 3M Rolling Avg =
AVERAGEX ( DATESINPERIOD ( dim_date[date_key], MAX ( dim_date[date_key] ), -3, MONTH ), [Revenue] )
```

## Customer behaviour
```DAX
Repeat Customers =
COUNTROWS ( FILTER ( VALUES ( fact_orders[customer_id] ), CALCULATE ( [Orders] ) > 1 ) )

Repeat Purchase Rate % = DIVIDE ( [Repeat Customers], [Customers] )

New Customers =
COUNTROWS (
  FILTER ( VALUES ( fact_orders[customer_id] ),
    CALCULATE ( MIN ( fact_orders[order_date] ), ALL ( dim_date ) ) >= MIN ( dim_date[date_key] )
    && CALCULATE ( MIN ( fact_orders[order_date] ), ALL ( dim_date ) ) <= MAX ( dim_date[date_key] ) ) )

Retention Rate % =   -- customers active this month who were also active the previous month
VAR cur  = VALUES ( fact_orders[customer_id] )
VAR prev = CALCULATETABLE ( VALUES ( fact_orders[customer_id] ), DATEADD ( dim_date[date_key], -1, MONTH ) )
RETURN DIVIDE ( COUNTROWS ( INTERSECT ( cur, prev ) ), COUNTROWS ( prev ) )

Top 20% Revenue Share =
VAR t = DISTINCT ( SELECTCOLUMNS ( dim_customer_360, "id", dim_customer_360[customer_id], "r", [Revenue] ) )
VAR n = ROUNDUP ( COUNTROWS ( FILTER ( t, [r] > 0 ) ) * 0.2, 0 )
RETURN DIVIDE ( SUMX ( TOPN ( n, t, [r], DESC ), [r] ), SUMX ( t, [r] ) )
```

## Segments, CLV & churn (from Python outputs)
```DAX
Segment Revenue Share % =
DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALL ( dim_customer_360[rfm_segment] ) ) )

Predicted CLV 12M = SUM ( dim_customer_360[clv_12m] )

Avg CLV per Customer = AVERAGE ( dim_customer_360[clv_12m] )

Avg Churn Probability = AVERAGE ( dim_customer_360[churn_probability] )

At-Risk Customers =
CALCULATE ( DISTINCTCOUNT ( dim_customer_360[customer_id] ),
            dim_customer_360[risk_band] IN { "High", "Medium" } )

Revenue at Risk =    -- predicted 12M value of active customers likely to lapse
SUMX ( FILTER ( dim_customer_360, dim_customer_360[risk_band] IN { "High", "Medium" } ),
       dim_customer_360[clv_12m] * dim_customer_360[churn_probability] )
```

## Operations
```DAX
Avg Review Score = AVERAGE ( fact_orders[review_score] )

Avg Delivery Days = AVERAGE ( fact_orders[delivery_days] )

On-Time Delivery % =
DIVIDE ( CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[delay_days] <= 0, fact_orders[order_status] = "delivered" ),
         CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[order_status] = "delivered" ) )

Return Rate % = DIVIDE ( CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[order_status] = "returned" ), COUNTROWS ( fact_orders ) )

Delay Bucket =    -- calculated column on fact_orders
SWITCH ( TRUE (), fact_orders[delay_days] <= 0, "On time / early",
                  fact_orders[delay_days] <= 3, "1-3 days late",
                  fact_orders[delay_days] <= 6, "4-6 days late", "7+ days late" )
```
