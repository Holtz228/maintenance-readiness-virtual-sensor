from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, TypedDict
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Streamlit starts the app from the repository root in most local runs, but this
# path guard keeps imports stable when the app is launched from a different shell context.
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


DashboardData = tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, Any],
]

PageRenderer = Callable[
    [
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        dict[str, Any],
    ],
    None,
]


class PageConfig(TypedDict):
    icon: str
    renderer: PageRenderer


# The app entry point only coordinates navigation and data loading.
# Business logic stays in src/, while each dashboard question is handled by a dedicated view.
PAGES: dict[str, PageConfig] = {
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


st.set_page_config(
    page_title="Maintenance Readiness",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_style()
px.defaults.template = PLOTLY_TEMPLATE


@st.cache_data(show_spinner=False)
def load_data() -> DashboardData:
    # The dashboard is intentionally read-only. It consumes validated pipeline outputs
    # instead of recalculating scores inside the UI, which keeps the app predictable
    # and makes the pipeline/test boundary explicit.
    required_files = [
        SENSOR_READINGS_PATH,
        SENSOR_PROFILE_PATH,
        VIRTUAL_SENSOR_PREDICTIONS_PATH,
        ASSET_HEALTH_PATH,
        MAINTENANCE_RECOMMENDATIONS_PATH,
    ]

    missing_files = [path for path in required_files if not path.exists()]
    if missing_files:
        missing_list = "\n".join(
            f"- {path.relative_to(PROJECT_ROOT)}" for path in missing_files
        )
        raise FileNotFoundError(
            "Processed files are missing. Run `python scripts/05_run_pipeline.py` first.\n"
            + missing_list
        )

    metrics: dict[str, Any] = {}
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
    # Query-parameter routing keeps the app simple and shareable without introducing
    # Streamlit multipage boilerplate or a separate routing framework.
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
        icon = page_config["icon"]
        active_class = "active" if active_page == page_name else ""
        href = f"?page={quote(page_name)}"

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


def render_missing_pipeline_outputs(error: FileNotFoundError) -> None:
    # A portfolio dashboard should fail with an actionable setup message, not with
    # a raw stack trace. This also makes the repository easier to run for reviewers.
    render_page_header(
        title="Pipeline Output Missing",
        subtitle="The dashboard needs processed files before it can render the decision views.",
        eyebrow="Setup Required",
    )
    st.error(str(error))
    st.code(
        "python scripts/05_run_pipeline.py\n"
        "streamlit run app/streamlit_app.py",
        language="powershell",
    )


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
        render_missing_pipeline_outputs(exc)
        return

    page_config = PAGES.get(active_page, PAGES["Home"])
    renderer = page_config["renderer"]

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