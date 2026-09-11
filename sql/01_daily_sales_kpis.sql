SELECT
    TO_DATE(order_purchase_timestamp) AS order_date,
    COUNT(*) AS orders,
    COUNT(DISTINCT customer_unique_id) AS customers,
    ROUND(SUM(payment_value), 2) AS revenue,
    ROUND(AVG(payment_value), 2) AS average_order_value,
    ROUND(SUM(freight_value), 2) AS freight_revenue,
    ROUND(SUM(freight_value) / NULLIF(SUM(item_revenue + freight_value), 0), 4) AS freight_share,
    ROUND(AVG(delivered_on_time), 4) AS on_time_delivery_rate,
    ROUND(AVG(delivery_days), 2) AS average_delivery_days,
    ROUND(AVG(review_score), 2) AS average_review_score
FROM fact_orders
WHERE order_status = 'delivered'
GROUP BY TO_DATE(order_purchase_timestamp)
ORDER BY order_date
