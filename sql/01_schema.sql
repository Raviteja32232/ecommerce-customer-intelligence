-- RAW TABLES --------------------------------------------------------------
DROP TABLE IF EXISTS customers; DROP TABLE IF EXISTS orders; DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS products;  DROP TABLE IF EXISTS payments; DROP TABLE IF EXISTS reviews;

CREATE TABLE customers   (customer_id TEXT PRIMARY KEY, state TEXT, signup_date TEXT);
CREATE TABLE products    (product_id TEXT PRIMARY KEY, category TEXT, price REAL);
CREATE TABLE orders      (order_id TEXT PRIMARY KEY, customer_id TEXT, order_date TEXT, delivered_date TEXT,
                          estimated_delivery_date TEXT, order_status TEXT,
                          FOREIGN KEY(customer_id) REFERENCES customers(customer_id));
CREATE TABLE order_items (order_id TEXT, item_seq INT, product_id TEXT, price REAL, freight REAL,
                          PRIMARY KEY(order_id,item_seq));
CREATE TABLE payments    (order_id TEXT, payment_type TEXT, payment_value REAL);
CREATE TABLE reviews     (order_id TEXT, review_score INT);

CREATE INDEX idx_orders_cust ON orders(customer_id);
CREATE INDEX idx_items_order ON order_items(order_id);
