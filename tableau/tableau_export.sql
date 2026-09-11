SELECT
    order_date,
    orders,
    customers,
    revenue,
    average_order_value,
    freight_share,
    on_time_delivery_rate,
    average_delivery_days,
    average_review_score
FROM daily_sales_kpis
ORDER BY order_date;
