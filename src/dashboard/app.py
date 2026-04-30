import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

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
        sensor_trends = queries.get_sensor_trends(hours=hours)
        event_counts = queries.get_event_counts(hours=hours)
        anomaly_count = queries.get_anomaly_count(hours=hours)
        recent_anomalies = queries.get_recent_anomalies(hours=hours)
        record_count = queries.get_record_count()
    finally:
        queries.close()

    return latest, sensor_trends, event_counts, anomaly_count, recent_anomalies, record_count


def main():
    st.set_page_config(
        page_title="IoT Environmental Intelligence",
        page_icon="",
        layout="wide",
    )

    st.title("IoT Environmental Intelligence")

    hours = st.sidebar.slider("Hours", min_value=1, max_value=72, value=24)
    live_refresh = st.sidebar.toggle("Live refresh", value=True)
    refresh_seconds = st.sidebar.slider("Refresh seconds", min_value=5, max_value=60, value=10)
    refresh = st.sidebar.button("Refresh")

    if live_refresh and st_autorefresh:
        st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_live_refresh")

    try:
        latest, sensor_trends, event_counts, anomaly_count, recent_anomalies, record_count = load_dashboard_data(hours)
    except Exception as exc:
        logger.exception("Dashboard data load failed")
        st.warning("InfluxDB is not available yet. Start storage before using live dashboard views.")
        st.caption(str(exc))
        latest, sensor_trends, event_counts, anomaly_count, recent_anomalies, record_count = None, [], {}, 0, [], 0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Records", record_count)
    metric_cols[1].metric("Anomalies", anomaly_count)
    metric_cols[2].metric("Latest Temp", f"{latest['temperature_f']:.1f} F" if latest else "No data")
    metric_cols[3].metric("Device", latest["device_id"] if latest else "No data")

    st.subheader("Live Sensor Trends")
    if sensor_trends:
        trend_df = pd.DataFrame(sensor_trends)
        fig = px.line(
            trend_df,
            x="timestamp",
            y="value",
            color="sensor",
            facet_row="sensor",
            facet_row_spacing=0.06,
        )
        fig.update_yaxes(matches=None)
        fig.update_layout(height=720, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sensor trend data available yet.")

    st.subheader("Event Counts")
    if event_counts:
        event_df = pd.DataFrame(
            [{"event_label": label, "count": count} for label, count in event_counts.items()]
        )
        fig = px.bar(event_df, x="event_label", y="count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No event data available yet.")

    st.subheader("Anomaly Timeline")
    if recent_anomalies:
        anomalies_df = pd.DataFrame(recent_anomalies)
        fig = px.scatter(
            anomalies_df,
            x="timestamp",
            y="device_id",
            color="location",
            hover_data=["anomaly_flag"],
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(anomalies_df, use_container_width=True, hide_index=True)
    else:
        st.info("No anomalies detected in the selected time range.")

    if refresh:
        st.rerun()


if __name__ == "__main__":
    main()
