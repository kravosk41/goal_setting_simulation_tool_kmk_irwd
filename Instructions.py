import streamlit as st
from streamlit import session_state as ss

st.set_page_config(
    page_title="Goal Setting Simulation Tool",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon='📈'
)

def add_logo():
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] {
                background-image: url(https://kmkconsultinginc.com/wp-content/uploads/2020/12/KMK-Logo.png);
                background-repeat: no-repeat;
                padding-top: 120px;
                background-position: 20px 20px;
            }
            [data-testid="stSidebarNav"]::before {
                content: "Sections";
                margin-left: 20px;
                margin-top: 20px;
                font-size: 30px;
                position: relative;
                top: 100px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

add_logo()

st.markdown(
    "<h1 style='text-align: center;'>Instructions</h1>", 
    unsafe_allow_html=True
)

st.markdown("---")
st.markdown(
    """
    1. First item
    2. Second item
    3. Third item
    """
)