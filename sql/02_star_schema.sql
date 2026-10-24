-- STAR SCHEMA -------------------------------------------------------------
DROP TABLE IF EXISTS dim_customer; DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;     DROP TABLE IF EXISTS fact_orders;

CREATE TABLE dim_customer AS
SELECT customer_id, state, DATE(signup_date) AS signup_date FROM customers;

CREATE TABLE dim_product AS SELECT product_id, category, price AS list_price FROM products;

CREATE TABLE dim_date AS
WITH RECURSIVE d(dt) AS (
  SELECT DATE('2023-01-01') UNION ALL SELECT DATE(dt,'+1 day') FROM d WHERE dt < '2025-12-31')
SELECT dt AS date_key,
       CAST(STRFTIME('%Y',dt) AS INT) AS year,
       CAST(STRFTIME('%m',dt) AS INT) AS month,
       STRFTIME('%Y-%m',dt)           AS year_month,
       'Q' || ((CAST(STRFTIME('%m',dt) AS INT)+2)/3) AS quarter,
       STRFTIME('%w',dt)              AS weekday_num
FROM d;

-- one row per order, with revenue, items, review and delivery metrics
CREATE TABLE fact_orders AS
SELECT o.order_id, o.customer_id,
       DATE(o.order_date) AS order_date,
       o.order_status,
       COUNT(i.item_seq)                AS items,
       SUM(i.price)                     AS revenue,
       SUM(i.freight)                   AS freight,
       p.payment_type,
       r.review_score,
       CAST(JULIANDAY(o.delivered_date) - JULIANDAY(o.order_date) AS INT)             AS delivery_days,
       CAST(JULIANDAY(o.delivered_date) - JULIANDAY(o.estimated_delivery_date) AS INT) AS delay_days
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
LEFT JOIN payments p ON p.order_id = o.order_id
LEFT JOIN reviews  r ON r.order_id = o.order_id
GROUP BY o.order_id;

CREATE INDEX idx_fact_cust ON fact_orders(customer_id);
CREATE INDEX idx_fact_date ON fact_orders(order_date);
