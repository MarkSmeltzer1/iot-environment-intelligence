import pandas as pd
import plotly.express as px
import streamlit as st

from src.storage.queries import InfluxDBQueries
from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


logger = setup_logger("dashboard")


def load_dashboard_data(hours: int):
    """Load recent dashboard data from InfluxDB."""
    config = load_config()
    queries = InfluxDBQueries(config)

    try:
        latest = queries.get_latest_reading()
        trend = queries.get_temperature_trend(hours=hours)
        event_counts = queries.get_event_counts(hours=hours)
        anomaly_count = queries.get_anomaly_count(hours=hours)
        record_count = queries.get_record_count()
    finally:
        queries.close()

    return latest, trend, event_counts, anomaly_count, record_count


def main():
    st.set_page_config(
        page_title="IoT Environmental Intelligence",
        page_icon="",
        layout="wide",
    )

    st.title("IoT Environmental Intelligence")

    hours = st.sidebar.slider("Hours", min_value=1, max_value=72, value=24)
    refresh = st.sidebar.button("Refresh")

    try:
        latest, trend, event_counts, anomaly_count, record_count = load_dashboard_data(hours)
    except Exception as exc:
        logger.exception("Dashboard data load failed")
        st.warning("InfluxDB is not available yet. Start storage before using live dashboard views.")
        st.caption(str(exc))
        latest, trend, event_counts, anomaly_count, record_count = None, [], {}, 0, 0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Records", record_count)
    metric_cols[1].metric("Anomalies", anomaly_count)
    metric_cols[2].metric("Latest Temp", f"{latest['temperature_f']:.1f} F" if latest else "No data")
    metric_cols[3].metric("Device", latest["device_id"] if latest else "No data")

    st.subheader("Temperature Trend")
    if trend:
        trend_df = pd.DataFrame(trend)
        fig = px.line(trend_df, x="timestamp", y="temperature_f")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No temperature trend data available yet.")

    st.subheader("Event Counts")
    if event_counts:
        event_df = pd.DataFrame(
            [{"event_label": label, "count": count} for label, count in event_counts.items()]
        )
        fig = px.bar(event_df, x="event_label", y="count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No event data available yet.")

    if refresh:
        st.rerun()


if __name__ == "__main__":
    main()
