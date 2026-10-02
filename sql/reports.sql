-- (a) Exact result: total_orders=180, total_revenue=99860.20, avg_order_value=554.78
SELECT
    COUNT(*) AS total_orders,
    printf('%.2f', SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0))) AS total_revenue,
    printf('%.2f', AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0))) AS avg_order_value
FROM orders AS o
JOIN products AS p ON p.product_id = o.product_id;

-- (b) Exact result: (180, 165, 15); 15 orders have no rating yet.
SELECT
    COUNT(*) AS all_orders,
    COUNT(rating) AS rated_orders,
    COUNT(*) - COUNT(rating) AS unrated_orders
FROM orders;

-- (c1) Exact result: C045 | Vihaan. LEFT JOIN keeps customers with no matching order.
SELECT c.customer_id, c.name
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) = 0;

-- (c2) Independent confirmation: C045 | Vihaan.
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

-- (d) Exact result: Jaipur (19, 8, 42.1), Lucknow (49, 15, 30.6), Bangalore (33, 8, 24.2).
SELECT
    c.city,
    COUNT(*) AS total_orders,
    SUM(o.returned) AS returned_orders,
    ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) AS return_rate_pct
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;

-- (e1) Exact result: C043 Reyansh 12920.00; C026 Isha 8371.60; C008 Meera 4564.60;
-- C011 Arjun 4111.00; C042 Sanya 3785.00.
-- customer_id ASC is the deterministic tie-break when two customers have equal spend.
SELECT
    c.customer_id,
    c.name,
    printf('%.2f', SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0))) AS total_spend
FROM orders AS o
JOIN products AS p ON p.product_id = o.product_id
JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)) DESC,
         c.customer_id ASC
LIMIT 5;

-- (e2) Exact result: the same ranks 3–5: C008 Meera 4564.60; C011 Arjun 4111.00; C042 Sanya 3785.00.
SELECT
    c.customer_id,
    c.name,
    printf('%.2f', SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0))) AS total_spend
FROM orders AS o
JOIN products AS p ON p.product_id = o.product_id
JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)) DESC,
         c.customer_id ASC
LIMIT 3 OFFSET 2;

-- (f) Exact result: Haircare (54, 44956.10); Skincare (60, 27346.00);
-- Babycare (30, 16805.00); PersonalCare (36, 10753.10).
SELECT
    p.category,
    COUNT(*) AS order_count,
    printf('%.2f', SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0))) AS category_revenue
FROM orders AS o
JOIN products AS p ON p.product_id = o.product_id
JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY p.category
ORDER BY SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)) DESC;

-- (g) Exact result: 10 customers — C001 Aarav, C003 Aditi, C004 Ananya, C011 Arjun,
-- C021 Aryan, C030 Anika, C031 Aditya, C036 Aisha, C041 Ayaan, C044 Aria.
SELECT customer_id, name
FROM customers
WHERE name LIKE 'A%'
ORDER BY customer_id;

-- (h) Exact result: Ad, Organic, Referral, Social.
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;

-- (i) Exact result after the UPDATE: Gold=28, Silver=17. Run reports.sql once on a fresh schema.
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

UPDATE customers
SET loyalty_tier = CASE
    WHEN city_tier = 1 THEN 'Gold'
    ELSE 'Silver'
END;

SELECT loyalty_tier, COUNT(*) AS customer_count
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;
