let
    Source = Odbc.DataSource("dsn=Amazon Athena", [HierarchicalNavigation=true]),
    AwsDataCatalog = Source{[Name="AwsDataCatalog", Kind="Database"]}[Data],
    AnalyticsDatabase = AwsDataCatalog{[Name="olist_analytics_db", Kind="Schema"]}[Data],
    FactOrders = AnalyticsDatabase{[Name="fact_orders", Kind="Table"]}[Data],
    TypedColumns = Table.TransformColumnTypes(
        FactOrders,
        {
            {"order_purchase_timestamp", type datetime},
            {"payment_value", Currency.Type},
            {"item_revenue", Currency.Type},
            {"freight_value", Currency.Type},
            {"review_score", type number},
            {"delivered_on_time", Int64.Type}
        }
    ),
    PurchaseDate = Table.AddColumn(
        TypedColumns,
        "Order Purchase Date",
        each Date.From([order_purchase_timestamp]),
        type date
    )
in
    PurchaseDate
