from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import (  # noqa: E402
    ASSET_HEALTH_PATH,
    MAINTENANCE_RECOMMENDATIONS_PATH,
    SENSOR_PROFILE_PATH,
    SENSOR_READINGS_PATH,
    VIRTUAL_SENSOR_METRICS_PATH,
    VIRTUAL_SENSOR_PREDICTIONS_PATH,
)
from src.ui_style import (  # noqa: E402
    PLOTLY_TEMPLATE,
    apply_global_style,
    render_page_header,
    render_sidebar_brand,
    render_sidebar_section_label,
    render_sidebar_status,
)
from src.views.asset_health_view import render_asset_health  # noqa: E402
from src.views.data_model_quality_view import render_data_quality  # noqa: E402
from src.views.executive_overview_view import render_executive_overview  # noqa: E402
from src.views.home_view import render_home  # noqa: E402
from src.views.maintenance_planner_view import render_maintenance_planner  # noqa: E402
from src.views.virtual_sensor_monitor_view import render_virtual_sensor_monitor  # noqa: E402


st.set_page_config(
    page_title="Maintenance Readiness",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_style()
px.defaults.template = PLOTLY_TEMPLATE


PageRenderer = Callable[
    [pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict],
    None,
]


PAGES: dict[str, dict[str, str | PageRenderer]] = {
    "Home": {
        "icon": "🏠",
        "renderer": render_home,
    },
    "Executive Overview": {
        "icon": "📊",
        "renderer": render_executive_overview,
    },
    "Virtual Sensor Monitor": {
        "icon": "📡",
        "renderer": render_virtual_sensor_monitor,
    },
    "Asset Health": {
        "icon": "🛠️",
        "renderer": render_asset_health,
    },
    "Maintenance Planner": {
        "icon": "🧭",
        "renderer": render_maintenance_planner,
    },
    "Data & Model Quality": {
        "icon": "🧪",
        "renderer": render_data_quality,
    },
}


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    required_files = [
        SENSOR_READINGS_PATH,
        SENSOR_PROFILE_PATH,
        VIRTUAL_SENSOR_PREDICTIONS_PATH,
        ASSET_HEALTH_PATH,
        MAINTENANCE_RECOMMENDATIONS_PATH,
    ]

    missing = [path for path in required_files if not path.exists()]
    if missing:
        missing_list = "\n".join(f"- {path.relative_to(PROJECT_ROOT)}" for path in missing)
        raise FileNotFoundError(
            "Processed files are missing. Run `python scripts/05_run_pipeline.py` first.\n"
            + missing_list
        )

    metrics = {}
    if VIRTUAL_SENSOR_METRICS_PATH.exists():
        metrics = json.loads(VIRTUAL_SENSOR_METRICS_PATH.read_text(encoding="utf-8"))

    return (
        pd.read_parquet(SENSOR_READINGS_PATH),
        pd.read_parquet(SENSOR_PROFILE_PATH),
        pd.read_parquet(VIRTUAL_SENSOR_PREDICTIONS_PATH),
        pd.read_parquet(ASSET_HEALTH_PATH),
        pd.read_parquet(MAINTENANCE_RECOMMENDATIONS_PATH),
        metrics,
    )


def get_active_page_from_url() -> str:
    page_from_url = st.query_params.get("page", "Home")

    if isinstance(page_from_url, list):
        page_from_url = page_from_url[0] if page_from_url else "Home"

    if page_from_url not in PAGES:
        return "Home"

    return page_from_url


def initialize_session_state() -> None:
    st.session_state.active_page = get_active_page_from_url()


def render_sidebar_navigation() -> str:
    render_sidebar_brand(
        title="Maintenance Readiness",
        subtitle="Virtual Sensor Decision Support",
        logo_text="MR",
    )

    render_sidebar_section_label("Dashboard")

    active_page = st.session_state.active_page

    for page_name, page_config in PAGES.items():
        icon = str(page_config["icon"])
        active_class = "active" if active_page == page_name else ""
        href = f"?page={page_name.replace(' ', '%20').replace('&', '%26')}"

        st.sidebar.markdown(
            f"""
            <a class="sidebar-nav-link {active_class}" href="{href}" target="_self">
                <span class="sidebar-nav-icon">{icon}</span>
                <span>{page_name}</span>
            </a>
            """,
            unsafe_allow_html=True,
        )

    render_sidebar_section_label("Project Status")
    render_sidebar_status(
        title="MVP Build Phase",
        text="NASA C-MAPSS sensor data + virtual sensor fallback analytics",
    )

    return active_page


def render_active_view(active_page: str) -> None:
    try:
        (
            sensor_readings,
            sensor_profile,
            predictions,
            asset_health,
            recommendations,
            metrics,
        ) = load_data()
    except FileNotFoundError as exc:
        render_page_header(
            title="Pipeline Output Missing",
            subtitle="The dashboard needs processed files before it can render the decision views.",
            eyebrow="Setup Required",
        )
        st.error(str(exc))
        st.code(
            "python scripts/05_run_pipeline.py\n"
            "streamlit run app/streamlit_app.py",
            language="powershell",
        )
        return

    page_config = PAGES.get(active_page)
    if page_config is None:
        st.session_state.active_page = "Home"
        page_config = PAGES["Home"]

    renderer = page_config["renderer"]

    if not callable(renderer):
        st.error(f"No renderer configured for page: {active_page}")
        return

    renderer(
        sensor_readings,
        sensor_profile,
        predictions,
        asset_health,
        recommendations,
        metrics,
    )


def main() -> None:
    initialize_session_state()
    active_page = render_sidebar_navigation()
    render_active_view(active_page)


if __name__ == "__main__":
    main()