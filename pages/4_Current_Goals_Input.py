import streamlit as st
from streamlit import session_state as ss
import pandas as pd

st.set_page_config(
    page_title="Live Data Input",
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

#   #   #   #   #   #   #   #
# Session State Management - 
if 'test_up' not in ss:
    ss.test_up = False

#   #   #   #   #   #   #   #

st.markdown(
    "<h1 style='text-align: center;'>Current Goals Input</h1>", 
    unsafe_allow_html=True
)

st.markdown("---")
st.subheader("Note -")
st.markdown(
    """
    1. Upload the actual data in the correct format(Template has been provided on the “Actual Data Input Tab” & make sure to drop the actuals column from that).
    2. Remember to click "Submit Excel" once the data has been uploaded.
    3. You can visualize the Final Goals and Growth Expectations in the “Results” tab.
    4. There is an options to test custom weights for Goal calculation.
    5. You can perform Volume Adjustment & tweak the Capping and Flooring as per client needs.
    """
)
st.markdown("---")

#To facilitate upload of excel file - 
uploaded_file2 = st.file_uploader("Choose an Excel file", type='xlsx')

if uploaded_file2 is not None:
    ss.test_up = True
    ss['test_file'] = uploaded_file2

if ss.test_up:
    data = pd.read_excel(ss['test_file'],sheet_name='Sheet1',converters={'NATION_GOAL':float})
    nation_goal_value = data.iloc[0,-1]
    data.drop(columns=['NATION_GOAL'],inplace=True)

    st.markdown(f"<h4 style='text-align: center;'>Nation Goal : {nation_goal_value}</h4>", unsafe_allow_html=True)
    st.write('Receved Data :')
    st.dataframe(data, use_container_width=True)
    st.markdown("---")
    st.markdown(f"<h4 style='text-align: left;'>Validations : </h4>", unsafe_allow_html=True)

    if (data.isnull().values.any()):
        print("Null Values Detected !")
    else:
        st.write("No Null Values found :smile:")
        st.write('---')
        st.subheader('Input File Stats - ')
        metrics = [m for m in ss['list_of_metrics']]
        values = [f"{data[m].sum():,.2f}" for m in ss['list_of_metrics']]
        national_growth_rate = (nation_goal_value / (data[ss['list_of_metrics'][0]].sum())) - 1
        # Create the 'Statistic' and 'Value' lists
        statistic = [
            'Total Number of Terrs',
            f"National Goal",
            'Metrics Received',
            f"National Growth Rate ({ss['list_of_metrics'][0]})"
        ] + metrics
        value = [
            len(data['Territory_Number'].unique()),
            f"{nation_goal_value:,.2f}",
            f"{ss['list_of_metrics']}",
            f"{national_growth_rate * 100:,.3f} %"
        ] + values
    
    st.dataframe(data = {'Statistic' : statistic,'Value' : value},width=500)


    if st.button("Submit Excel"):
        st.switch_page('pages/5_Current_Goals_Results.py')