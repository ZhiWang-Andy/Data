WITH anchor AS (
    SELECT MAX(order_purchase_timestamp) AS max_purchase_timestamp
    FROM fact_orders
    WHERE order_status = 'delivered'
), customer_metrics AS (
    SELECT
        f.customer_unique_id,
        DATEDIFF(a.max_purchase_timestamp, MAX(f.order_purchase_timestamp)) AS recency_days,
        COUNT(DISTINCT f.order_id) AS frequency,
        SUM(f.payment_value) AS monetary_value
    FROM fact_orders f
    CROSS JOIN anchor a
    WHERE f.order_status = 'delivered' AND f.customer_unique_id IS NOT NULL
    GROUP BY f.customer_unique_id, a.max_purchase_timestamp
), scored AS (
    SELECT
        *,
        6 - NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_value ASC) AS m_score
    FROM customer_metrics
)
SELECT
    *,
    CONCAT(CAST(r_score AS STRING), CAST(f_score AS STRING), CAST(m_score AS STRING)) AS rfm_code,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Promising'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        ELSE 'Needs Attention'
    END AS segment
FROM scored
