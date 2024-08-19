import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import io
import datetime

st.set_page_config(
    page_title="Upload Raw Data",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon='📊'
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
if 'YEAR' not in ss:
    ss.YEAR = datetime.date.today().year
if 'YEAR2' not in ss:
    ss.YEAR2 = ss.YEAR
if 'QTR' not in ss:
    ss.QTR = 'Q1'
if 'QTR2' not in ss:
    ss.QTR2 = ss.QTR
if 'TYPE' not in ss:
    ss.TYPE = 'Quarterly'
if 'MODE' not in ss:
    ss.MODE = 1
if 'selected_option' not in ss:
    ss.selected_option = None
if 'ex_up' not in ss:
    ss.ex_up = False
if 'file' not in ss:
    ss.file = None
if 'download_format_button' not in ss:
    ss.download_format_button = False
if 'submit_1' not in ss:
    ss.submit_1 = False
if "list_of_metrics" not in ss:
    ss['list_of_metrics'] = None
if "number_of_metrics" not in ss:
    ss['number_of_metrics'] = None
#   #   #   #   #   #   #   #


st.markdown("<h1 style='text-align: center;'>Goal Setting Simulation Tool</h1>", unsafe_allow_html=True)
st.markdown('---')
c4,c5 = st.columns(2)
c4.markdown("<h4 style='text-align: left;'>Number of Data Periods to test on - </h4>",unsafe_allow_html=True)
ss.MODE = c5.selectbox(label='num_qtrs',options=[1,2],key='MODE_v',index=[1,2].index(ss.MODE),label_visibility='collapsed')
st.markdown('---')
st.markdown("<h4 style='text-align: left;'>Select the Goal Setting Simulation Model Time Period</h4>",unsafe_allow_html=True)

c1,c2,c3 = st.columns(3)
ss.TYPE = c1.selectbox(
    label='Type',options=['Quarterly','Trimesterly','Semesterly'],
    help='Select Anaysis Period Type',
    key='TYPE_v',
    index=['Quarterly','Trimesterly','Semesterly'].index(ss.TYPE)
)
with c2:
    if ss.TYPE == 'Quarterly':
       ss.QTR = st.selectbox(
           label='Quarter',options = ['Q1','Q2','Q3','Q4'],label_visibility='visible',help='Select Quarter',key='QTR_v',
           index = ['Q1','Q2','Q3','Q4'].index(f'Q{ss.QTR[1]}')
        )
    elif ss.TYPE == 'Trimesterly':
        ss.QTR= st.selectbox(
            label='Trimester',options = ['T1','T2','T3'],label_visibility='visible',help='Select Trimester',key='QTR_v',
            index = ['T1','T2','T3'].index(f'T{ss.QTR[1]}')
        )
    elif ss.TYPE == 'Semesterly':
        ss.QTR= st.selectbox(
            label='Semester',options = ['S1','S2'],label_visibility='visible',help='Select Semester',key='QTR_v',
            index = ['S1','S2'].index(f'S{ss.QTR[1]}')
        )
ss.YEAR = c3.selectbox(
    label='Year',options=[yr for yr in range(2020,2031)],help='Select Year',key='YEAR_v',
    index=[yr for yr in range(2020,2031)].index(ss.YEAR)
)

if ss.MODE == 2:
    with c2:
        if ss.TYPE == 'Quarterly':
            ss.QTR2 = st.selectbox(
                label='Quarter2',options = ['Q1','Q2','Q3','Q4'],label_visibility='collapsed',help='Select Quarter',key='QTR2_v',
                index = ['Q1','Q2','Q3','Q4'].index(f'Q{ss.QTR2[1]}')
            )
        elif ss.TYPE == 'Trimesterly':
            ss.QTR= st.selectbox(
                label='Trimester2',options = ['T1','T2','T3'],label_visibility='collapsed',help='Select Trimester',key='QTR2_v',
                index = ['T1','T2','T3'].index(f'T{ss.QTR2[1]}')
            )
        elif ss.TYPE == 'Semesterly':
            ss.QTR= st.selectbox(
                label='Semester2',options = ['S1','S2'],label_visibility='collapsed',help='Select Semester',key='QTR2_v',
                index = ['S1','S2'].index(f'S{ss.QTR2[1]}')
            )
    ss.YEAR2 = c3.selectbox(
        label='Year2',options=[yr for yr in range(2020,2031)],help='Select Year',key='YEAR2_v',label_visibility='collapsed',
        index=[yr for yr in range(2020,2031)].index(ss.YEAR2)
    )

st.markdown("---")
#To facilitate upload of excel file - 
uploaded_file = st.file_uploader("Choose an Excel file", type='xlsx')
st.markdown(
    f"<h5 style='text-align: center;'>Simulation Periods- : {ss.QTR}'{str(ss.YEAR)[-2:]}, and {ss.QTR2}'{str(ss.YEAR2)[-2:]}</h5>", 
    unsafe_allow_html=True
)
if uploaded_file is not None:
    ss.ex_up = True
    ss['file'] = uploaded_file

with st.expander("Download Input Data Template ☝️"):
    st.write("Enter the number of Weight Metrics you have in your project \
                followed by the their names, the download button will give you a blank excel to populate your data in !")

    options = list(range(1, 11))
    #ss.selected_option = st.selectbox('How Many Metrics Do you have ?', options)
    ss.selected_option = st.select_slider(label='How Many Metrics Do you have ?', options=[i for i in range(1,11)])
    if ss.selected_option > 0:
        list_of_weight_names = []
        for i in range(ss.selected_option):
            # Create a text input box for each metric
            weight_name = st.text_input(f'Metric {i+1}', '')
            list_of_weight_names.append(weight_name)
        
        #for download - 
        list_of_weight_names.insert(0, 'Territory_Number')
        list_of_weight_names.extend(['Actuals','NATION_GOAL'])
        excel_format_df = pd.DataFrame(columns = list_of_weight_names)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            excel_format_df.to_excel(writer, sheet_name='Sheet1',index=False)
            if ss.MODE ==2:
                excel_format_df.to_excel(writer, sheet_name='Sheet2',index=False)
        
        st.download_button("Download Input Data Template",
                help="Click this to download the format for the raw data excel you must upload",
                data=buffer,
                file_name="GST_input.xlsx",
                mime="application/vnd.ms-excel")
        
st.markdown("---")
if ss.ex_up:
    data = pd.read_excel(ss['file'],sheet_name='Sheet1',converters={'NATION_GOAL':float})
    nation_goal_value = data.iloc[0,-1]
    st.markdown(f"<h5 style='text-align: center;'>{ss.YEAR} {ss.QTR} National Level Goal : {nation_goal_value:,.2f}</h5>", unsafe_allow_html=True)
    data.drop(columns=['NATION_GOAL'],inplace=True)

    if ss.MODE==2:
        data2 = pd.read_excel(ss['file'],sheet_name='Sheet2',converters={'NATION_GOAL':float})
        nation_goal_value2 = data2.iloc[0,-1]
        st.markdown(f"<h5 style='text-align: center;'>{ss.YEAR2} {ss.QTR2} National Level Goal : {nation_goal_value2:,.2f}</h5>", unsafe_allow_html=True)
        data2.drop(columns=['NATION_GOAL'],inplace=True)


    #Number of metrics count here -
    list_of_metrics = list(set(data.columns) - {'Territory_Number','Actuals'})
    list_of_metrics.sort()
    number_of_metrics = len(list_of_metrics)

    ###################################################
    st.subheader("Received Raw Data:")
    st.dataframe(data,height= 180,width=800,hide_index=True,
                 column_config={'Actuals':f'{ss.YEAR} {ss.QTR} Actuals'})
    if ss.MODE==2:
        st.dataframe(data2,height= 180,width=800,hide_index=True,
                     column_config={'Actuals':f'{ss.YEAR2} {ss.QTR2} Actuals'})
    st.markdown("---")
    st.markdown(f"<h4 style='text-align: left;'>Validations : </h4>", unsafe_allow_html=True)
    
    if (data.isnull().values.any()):
        if ss.MODE==2:
            if (data2.isnull().values.any()):
                print("Null Values Detected !")
        print("Null Values Detected !")
    else:
        st.write("No Null Values found :smile:")
        st.write('---')
        st.subheader('Input File Stats - ')
        metrics = [m for m in list_of_metrics]
        values = [f"{data[m].sum():,.2f}" for m in list_of_metrics]
        if ss.MODE==2:
            values2 = [f"{data2[m].sum():,.2f}" for m in list_of_metrics]
        # Create the 'Statistic' and 'Value' lists
        statistic = [
            'Total Number of Terrs',
            f"{ss.QTR}'{str(ss.YEAR)[-2:]} National Goal",
            'Sum of Actuals',
            'Metrics Received',
            'Attainment'
        ] + metrics
        value = [
            len(data['Territory_Number'].unique()),
            f"{nation_goal_value:,.2f}",
            f"{data['Actuals'].sum():,.2f}",
            f"{list_of_metrics}",
            f"{(data['Actuals'].sum()/nation_goal_value)*100:.2f}%"
        ] + values
        if ss.MODE==2:
            value2 = [
                len(data2['Territory_Number'].unique()),
                f"{nation_goal_value2:,.2f}",
                f"{data2['Actuals'].sum():,.2f}",
                f"{list_of_metrics}",
                f"{(data2['Actuals'].sum()/nation_goal_value2)*100:.2f}%"
            ] + values2
        
        if ss.MODE==1:
            st.dataframe(data = {'Statistic' : statistic,'Value' : value},width=500)
        elif ss.MODE==2:
            st.dataframe(data = {'Statistic' : statistic,f'{ss.QTR}' : value,f'{ss.QTR2}': value2},width=700)
    st.markdown("---")

    if st.button("Submit Excel"):
        ss['list_of_metrics'] = list_of_metrics
        ss['number_of_metrics'] = number_of_metrics
        ss['nation_goal_value'] = nation_goal_value
        ss['excel_file_df'] = data
        if ss.MODE ==2 :
            ss['nation_goal_value2'] = nation_goal_value2
            ss['excel_file_df2'] = data2
        st.write(f"Submited Data ! | Metrics :{ss['list_of_metrics']} | Count :{ss['number_of_metrics']}") #print ss vars or local vars ?
        st.switch_page('pages/2_Simulation_Metrics.py')


#https://stackoverflow.com/questions/73251012/put-logo-and-title-above-on-top-of-page-navigation-in-sidebar-of-streamlit-multi