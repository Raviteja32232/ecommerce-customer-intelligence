-- Revenue counts only non-cancelled orders --------------------------------
DROP VIEW IF EXISTS v_monthly_revenue; DROP VIEW IF EXISTS v_repeat_rate; DROP VIEW IF EXISTS v_category_performance;
DROP VIEW IF EXISTS v_cohort_retention; DROP VIEW IF EXISTS v_delivery_vs_review; DROP VIEW IF EXISTS v_customer_base;
DROP VIEW IF EXISTS v_pareto;

-- 1. Monthly revenue, orders, AOV, MoM growth (window function)
CREATE VIEW v_monthly_revenue AS
WITH m AS (
  SELECT STRFTIME('%Y-%m',order_date) AS year_month,
         SUM(revenue) AS revenue, COUNT(*) AS orders, COUNT(DISTINCT customer_id) AS active_customers
  FROM fact_orders WHERE order_status <> 'cancelled' GROUP BY 1)
SELECT year_month, ROUND(revenue,0) AS revenue, orders, active_customers,
       ROUND(revenue*1.0/orders,0) AS aov,
       ROUND(100.0*(revenue - LAG(revenue) OVER (ORDER BY year_month)) / LAG(revenue) OVER (ORDER BY year_month),1) AS mom_growth_pct
FROM m;

-- 2. Repeat purchase rate
CREATE VIEW v_repeat_rate AS
WITH c AS (SELECT customer_id, COUNT(*) AS n FROM fact_orders WHERE order_status<>'cancelled' GROUP BY 1)
SELECT COUNT(*) AS customers,
       SUM(n>1) AS repeat_customers,
       ROUND(100.0*SUM(n>1)/COUNT(*),1) AS repeat_rate_pct
FROM c;

-- 3. Category performance
CREATE VIEW v_category_performance AS
SELECT pr.category, COUNT(DISTINCT i.order_id) AS orders, COUNT(*) AS units,
       ROUND(SUM(i.price),0) AS revenue,
       ROUND(AVG(r.review_score),2) AS avg_review
FROM order_items i
JOIN products pr ON pr.product_id=i.product_id
JOIN orders o ON o.order_id=i.order_id AND o.order_status<>'cancelled'
LEFT JOIN reviews r ON r.order_id=i.order_id
GROUP BY pr.category ORDER BY revenue DESC;

-- 4. Cohort retention: % of each signup-month cohort ordering in month N
CREATE VIEW v_cohort_retention AS
WITH first_o AS (SELECT customer_id, STRFTIME('%Y-%m',MIN(order_date)) AS cohort FROM fact_orders GROUP BY 1),
act AS (
  SELECT f.cohort,
         (CAST(STRFTIME('%Y',o.order_date) AS INT)-CAST(SUBSTR(f.cohort,1,4) AS INT))*12
         + CAST(STRFTIME('%m',o.order_date) AS INT)-CAST(SUBSTR(f.cohort,6,2) AS INT) AS month_n,
         o.customer_id
  FROM fact_orders o JOIN first_o f USING(customer_id) WHERE o.order_status<>'cancelled'),
sz AS (SELECT cohort, COUNT(*) AS cohort_size FROM first_o GROUP BY 1)
SELECT a.cohort, a.month_n, COUNT(DISTINCT a.customer_id) AS active, s.cohort_size,
       ROUND(100.0*COUNT(DISTINCT a.customer_id)/s.cohort_size,1) AS retention_pct
FROM act a JOIN sz s USING(cohort) GROUP BY a.cohort, a.month_n;

-- 5. Delivery delay vs satisfaction
CREATE VIEW v_delivery_vs_review AS
SELECT CASE WHEN delay_days<=0 THEN '1. On time / early'
            WHEN delay_days<=3 THEN '2. 1-3 days late'
            WHEN delay_days<=6 THEN '3. 4-6 days late' ELSE '4. 7+ days late' END AS delay_bucket,
       COUNT(*) AS orders, ROUND(AVG(review_score),2) AS avg_review
FROM fact_orders WHERE order_status='delivered' GROUP BY 1 ORDER BY 1;

-- 6. Customer base table that feeds Python (RFM inputs + extras)
CREATE VIEW v_customer_base AS
SELECT c.customer_id, c.state, c.signup_date,
       COUNT(f.order_id) AS frequency,
       ROUND(SUM(f.revenue),2) AS monetary,
       MIN(f.order_date) AS first_order, MAX(f.order_date) AS last_order,
       ROUND(AVG(f.review_score),2) AS avg_review,
       ROUND(AVG(f.delay_days),2)   AS avg_delay,
       SUM(f.order_status='returned') AS returns
FROM dim_customer c JOIN fact_orders f USING(customer_id)
WHERE f.order_status<>'cancelled' GROUP BY c.customer_id;

-- 7. Pareto: cumulative revenue share by customer decile
CREATE VIEW v_pareto AS
WITH r AS (SELECT customer_id, SUM(revenue) AS rev FROM fact_orders WHERE order_status<>'cancelled' GROUP BY 1),
d AS (SELECT rev, NTILE(10) OVER (ORDER BY rev DESC) AS decile FROM r)
SELECT decile, ROUND(SUM(rev),0) AS revenue,
       ROUND(100.0*SUM(rev)/(SELECT SUM(rev) FROM r),1) AS revenue_share_pct
FROM d GROUP BY decile ORDER BY decile;
