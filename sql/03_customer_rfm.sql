WITH customer_metrics AS (
    SELECT
        customer_unique_id,
        DATEDIFF(MAX(order_purchase_timestamp) OVER (), MAX(order_purchase_timestamp)) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(payment_value) AS monetary_value
    FROM fact_orders
    WHERE order_status = 'delivered' AND customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
), scored AS (
    SELECT
        *,
        6 - NTILE(5) OVER (ORDER BY recency_days ASC) AS r_score,
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
