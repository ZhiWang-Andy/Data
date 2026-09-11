WITH seller_order AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        SUM(CAST(oi.price AS DOUBLE)) AS item_revenue,
        SUM(CAST(oi.freight_value AS DOUBLE)) AS freight_value
    FROM order_items oi
    GROUP BY oi.seller_id, oi.order_id
), review_order AS (
    SELECT order_id, AVG(CAST(review_score AS DOUBLE)) AS review_score
    FROM reviews
    GROUP BY order_id
)
SELECT
    so.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT so.order_id) AS orders,
    ROUND(SUM(so.item_revenue), 2) AS item_revenue,
    ROUND(SUM(so.freight_value), 2) AS freight_value,
    ROUND(AVG(ro.review_score), 2) AS average_review_score
FROM seller_order so
LEFT JOIN sellers s ON so.seller_id = s.seller_id
LEFT JOIN review_order ro ON so.order_id = ro.order_id
GROUP BY so.seller_id, s.seller_city, s.seller_state
ORDER BY item_revenue DESC
