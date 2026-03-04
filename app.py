"""
Discovery Rigor Engine — Streamlit Entry Point

This file handles page routing only. No business logic lives here.
Each page in ui/ manages its own layout and calls the graph or store as needed.
"""

import streamlit as st

st.set_page_config(
    page_title="Discovery Rigor Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation
st.sidebar.title("Discovery Rigor Engine")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    options=["Home", "Assumption Map", "Script Review", "Synthesis"],
    index=0,
    key="sidebar_nav",
)

# Progress tracker — shows after a study is loaded
from ui.components import render_progress_tracker

render_progress_tracker(st.session_state.get("current_state"))

# Route to the selected page
if page == "Home":
    from ui.home import render
    render()
elif page == "Assumption Map":
    from ui.assumption_map import render
    render()
elif page == "Script Review":
    from ui.script_review import render
    render()
elif page == "Synthesis":
    from ui.synthesis import render
    render()
