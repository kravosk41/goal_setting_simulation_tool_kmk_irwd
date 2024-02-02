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
st.write("Please read the following instructions carefully :")
st.markdown(
    """
    1. Upload the input data in the correct format _(Template has been provided on the “Input Data Tab”)_.
    2. Remember to click "Submit Excel" once the data has been uploaded.
    3. Click on “Process Combinations” after entering weight ranges. If you re-enter the metric ranges, please click on “Process Combinations” again..
    4. Please make sure your system has enough memory if the total number of combinations is in the billions, as this will significantly slow down operations in the future!
    5. Do not forget to “Submit Combinations” before processing results.
    6. You can visualize the results in the “Processing Results” tab.
    7. You can also download the results in an excel format for your convenience.
    """
)