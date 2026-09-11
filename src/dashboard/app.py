from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


def parse_known_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-root", type=Path, default=Path("data/lakehouse/gold"))
    args, _ = parser.parse_known_args()
    return args


@st.cache_data
def load_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def metric(value: float | int, currency: bool = False, percent: bool = False) -> str:
    if currency:
        return f"${value:,.2f}"
    if percent:
        return f"{100 * value:,.2f}%"
    return f"{value:,.0f}"


def main() -> None:
    args = parse_known_args()
    st.set_page_config(page_title="Olist Analytics Platform", layout="wide")
    st.title("Cloud E-Commerce Analytics & Experimentation")
    st.caption("Spark SQL • AWS lakehouse • A/B testing • data quality • BI semantic layer")

    daily_path = args.data_root / "daily_sales_kpis"
    if not daily_path.exists():
        st.warning("Gold tables not found. Run the Spark ETL pipeline first.")
        st.stop()

    daily = load_parquet(daily_path)
    daily["order_date"] = pd.to_datetime(daily["order_date"])
    min_date, max_date = daily["order_date"].min(), daily["order_date"].max()
    selected = st.sidebar.date_input(
        "Date range",
        value=(min_date.date(), max_date.date()),
    )
    if isinstance(selected, tuple) and len(selected) == 2:
        start, end = pd.Timestamp(selected[0]), pd.Timestamp(selected[1])
        daily = daily[daily["order_date"].between(start, end)]

    total_orders = int(daily["orders"].sum())
    revenue = float(daily["revenue"].sum())
    aov = revenue / total_orders if total_orders else 0.0
    on_time = float(
        (daily["on_time_delivery_rate"] * daily["orders"]).sum() / total_orders
    )

    cols = st.columns(4)
    cols[0].metric("Orders", metric(total_orders))
    cols[1].metric("Revenue", metric(revenue, currency=True))
    cols[2].metric("Average order value", metric(aov, currency=True))
    cols[3].metric("On-time delivery", metric(on_time, percent=True))

    st.plotly_chart(
        px.line(daily, x="order_date", y="revenue", title="Daily revenue"),
        use_container_width=True,
    )
    st.plotly_chart(
        px.line(
            daily,
            x="order_date",
            y=["average_review_score", "average_delivery_days"],
            title="Customer experience and delivery trend",
        ),
        use_container_width=True,
    )

    seller_path = args.data_root / "seller_performance"
    if seller_path.exists():
        sellers = load_parquet(seller_path).head(20)
        st.plotly_chart(
            px.bar(
                sellers,
                x="seller_id",
                y="item_revenue",
                hover_data=["average_review_score"],
                title="Top sellers by revenue",
            ),
            use_container_width=True,
        )

    result_path = args.data_root / "experiment_results" / "experiment_result.json"
    st.header("Experiment decision")
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        primary = result["primary_metric"]
        exp_cols = st.columns(4)
        exp_cols[0].metric("Decision", result["decision"])
        exp_cols[1].metric(
            "Absolute lift",
            metric(primary["absolute_lift"], percent=True),
        )
        exp_cols[2].metric("p-value", f"{primary['p_value']:.4f}")
        exp_cols[3].metric(
            "SRM detected",
            str(result["sample_ratio_mismatch"]["srm_detected"]),
        )
        st.json(result)
    else:
        st.info("Run the experiment module to populate this section.")


if __name__ == "__main__":
    main()
