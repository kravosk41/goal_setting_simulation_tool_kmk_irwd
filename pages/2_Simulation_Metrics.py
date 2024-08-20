import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from decimal import Decimal
import numpy as np
import plotly.express as px
import io
import datetime

st.set_page_config(
    page_title="GST-Constraints",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon='🛠️'
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
e = 0.0000001 # epsilon
if 'gen_rag' not in ss:
    ss.gen_rag = False
if 'metric_df' not in ss:
    ss['metric_df'] = None #you can set this to pd.DataFrame(), but in the change detection only keep - ss['metric_df'].equals(summary_df)
if ss.number_of_metrics != None and 'range_constraints_list' not in ss:
    ss['range_constraints_list'] = [[0.0, 0.0, 0.0] for _ in range(ss['number_of_metrics'])]
if ss.number_of_metrics != None and  'simulation_dates' not in ss:
    ss['simulation_dates'] = ["" for _ in range(ss['number_of_metrics'])]
if ss.number_of_metrics != None and  'simulation_dates2' not in ss:
    ss['simulation_dates2'] = ["" for _ in range(ss['number_of_metrics'])]
if 'items_list' not in ss:
    ss['items_list'] = None
if 'submit_2' not in ss:
    ss.submit_2 = False
if 'start_filter' not in ss: #tracks button click status
    ss.start_filter = False
if 'ex_up' not in ss:
    ss.ex_up = False
if 'pro_com' not in ss: #tracks if results were done processing or not
    ss.pro_com = False
#   #   #   #   #   #   #   #

st.markdown("<h1 style='text-align: center;'>Goal Setting Simulation Weight Ranges</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: left;'>Please Enter Minimum , Maximum and Increment values for your weights \
            that you would like to test in your exercise</h4>",unsafe_allow_html=True)
st.write("Please Make Sure to pick ranges judicously!")
st.markdown("---")

# If excel is uploaded and submitted
if ss.ex_up and ss.list_of_metrics:
    st.subheader('Metric vs Metric Correlation-')
    if ss.MODE == 1:
        g1,g2,g3 = st.columns([1,5,1])
        with g2:
            #add graph here -
            metr_sel_1 = st.radio('Pick First Metric (a)',ss['list_of_metrics'],horizontal=True)
            metr_sel_2 = st.radio('Pick Second Metric (a)',ss['list_of_metrics'],horizontal=True,index=1)

            #graph number 2- 
            fig  = px.scatter(
                data_frame = ss['excel_file_df'],
                x = metr_sel_1, #pick a metric
                y = metr_sel_2,
                #color_discrete_sequence=['cyan'],
                trendline='ols',
                trendline_color_override = 'orange',
                title = metr_sel_1 + ' vs ' +metr_sel_2
            )
            # For R Squared - 
            results = px.get_trendline_results(fig)
            r_squared = results.iloc[0]["px_fit_results"].rsquared
            fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
            fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper')
            st.plotly_chart(fig,use_container_width=True)
    if ss.MODE == 2:
        g1,g2,g3,g4 = st.columns([1,4,4,1])
        with g2:
            #add graph here -
            metr_sel_1 = st.radio('Pick First Metric (a)',ss['list_of_metrics'],horizontal=True)
            metr_sel_2 = st.radio('Pick Second Metric (a)',ss['list_of_metrics'],horizontal=True,index=1)

            #graph number 2- 
            fig  = px.scatter(
                data_frame = ss['excel_file_df'],
                x = metr_sel_1, #pick a metric
                y = metr_sel_2,
                #color_discrete_sequence=['cyan'],
                trendline='ols',
                trendline_color_override = 'orange',
                title = metr_sel_1 + ' vs ' +metr_sel_2
            )
            # For R Squared - 
            results = px.get_trendline_results(fig)
            r_squared = results.iloc[0]["px_fit_results"].rsquared
            fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
            fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper')
            st.plotly_chart(fig,use_container_width=True)
        with g3:
            #add graph here -
            metr_sel_12 = st.radio('Pick First Metric (b)',ss['list_of_metrics'],horizontal=True)
            metr_sel_22 = st.radio('Pick Second Metric (b)',ss['list_of_metrics'],horizontal=True,index=1)

            #graph number 2- 
            fig2  = px.scatter(
                data_frame = ss['excel_file_df2'],
                x = metr_sel_12, #pick a metric
                y = metr_sel_22,
                #color_discrete_sequence=['cyan'],
                trendline='ols',
                trendline_color_override = 'orange',
                title = metr_sel_12 + ' vs ' +metr_sel_22
            )
            # For R Squared - 
            results2 = px.get_trendline_results(fig2)
            r_squared2 = results2.iloc[0]["px_fit_results"].rsquared
            fig2.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared2:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
            fig2.update_layout(title_font_size=20,title_x=0.35, title_xref='paper')
            st.plotly_chart(fig2,use_container_width=True)
        
    #Download Excel Correlation :
    corr_res = ss['excel_file_df'][ss['list_of_metrics']].corr()
    if ss.MODE == 2:
        corr_res2 = ss['excel_file_df2'][ss['list_of_metrics']].corr()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        corr_res.to_excel(writer, sheet_name='Sheet1',index=False)
        if ss.MODE == 2:
            corr_res2.to_excel(writer, sheet_name='Sheet2',index=False)
    st.download_button("Download Correlation Data",data=buffer,file_name="GST_corr.xlsx",
    help='Click this to get correlation numbers between all metrics [using pd.corr()]',mime="application/vnd.ms-excel")
    st.markdown('---')

# If excel is uploaded and submitted
if ss.ex_up and ss.list_of_metrics:

    #SECTION 1 - User Inputs the metric constraints - 
    range_constraints_list = []
    simulation_dates = []
    simulation_dates2 = []
    
    if ss.MODE == 2:
        col1, col2, col3, col4, col5, col6 = st.columns([2,1,1,1,1,1],gap='medium')
        col1.markdown("<h3 style='text-align: center;'>Metric Name</h3>", unsafe_allow_html=True)
        col2.markdown("<h3 style='text-align: center;'>Min %</h3>", unsafe_allow_html=True)
        col3.markdown("<h3 style='text-align: center;'>Max %</h3>", unsafe_allow_html=True)
        col4.markdown("<h3 style='text-align: center;'>Increment %</h3>", unsafe_allow_html=True)
        col5.markdown("<h3 style='text-align: center;'>Time Period</h3>", unsafe_allow_html=True)
        col6.markdown("<h3 style='text-align: center;'>Time Period2</h3>", unsafe_allow_html=True)
    else:
        col1, col2, col3, col4, col5 = st.columns([2,1,1,1,1],gap='medium')
        col1.markdown("<h3 style='text-align: center;'>Metric Name</h3>", unsafe_allow_html=True)
        col2.markdown("<h3 style='text-align: center;'>Min %</h3>", unsafe_allow_html=True)
        col3.markdown("<h3 style='text-align: center;'>Max %</h3>", unsafe_allow_html=True)
        col4.markdown("<h3 style='text-align: center;'>Increment %</h3>", unsafe_allow_html=True)
        col5.markdown("<h3 style='text-align: center;'>Time Period</h3>", unsafe_allow_html=True)

    
    if ss.MODE == 2:
        for i in range(ss['number_of_metrics']):
            col1.markdown(f"<h1 style='text-align: center; padding: 17px;'>{str(ss['list_of_metrics'][i])}</h1>", unsafe_allow_html=True)
            min_value = col2.number_input(label=' ',key = f'Min Value for Metric {i+1}', min_value=0.0, max_value=100.0, step=1.0,value=ss['range_constraints_list'][i][0]*100)
            max_value = col3.number_input(label=' ',key = f'Max Value for Metric {i+1}', min_value=0.0, max_value=100.0, step=1.0,value=ss['range_constraints_list'][i][1]*100)
            increment_value = col4.number_input(label=' ',key = f'Increment {i+1} ', min_value=0.0, max_value=10.0, step=1.0,value=ss['range_constraints_list'][i][2]*100)
            if (ss['simulation_dates'][i] == ""): #if default value then
                sim_date = col5.text_input(label=' ',key=f'Date {i+1}',placeholder='(mm/dd/yy) - (mm/dd/yy)')
            else:
                sim_date = col5.text_input(label=' ',key=f'Date {i+1}',value=ss['simulation_dates'][i])
            if (ss['simulation_dates2'][i] == ""): #if default value then
                sim_date2 = col6.text_input(label=' ',key=f'Date2 {i+1}',placeholder='(mm/dd/yy) - (mm/dd/yy)')
            else:
                sim_date2 = col6.text_input(label=' ',key=f'Date2 {i+1}',value=ss['simulation_dates2'][i])
            
            # Add the user input to the list of metrics and range constraints
            range_constraints_list.append([min_value/100, max_value/100, increment_value/100])
            simulation_dates.append(sim_date)
            simulation_dates2.append(sim_date2)
    
    else:
        for i in range(ss['number_of_metrics']):
            col1.markdown(f"<h1 style='text-align: center; padding: 17px;'>{str(ss['list_of_metrics'][i])}</h1>", unsafe_allow_html=True)
            min_value = col2.number_input(label=' ',key = f'Min Value for Metric {i+1}', min_value=0.0, max_value=100.0, step=1.0,value=ss['range_constraints_list'][i][0]*100)
            max_value = col3.number_input(label=' ',key = f'Max Value for Metric {i+1}', min_value=0.0, max_value=100.0, step=1.0,value=ss['range_constraints_list'][i][1]*100)
            increment_value = col4.number_input(label=' ',key = f'Increment {i+1} ', min_value=0.0, max_value=10.0, step=1.0,value=ss['range_constraints_list'][i][2]*100)
            if (ss['simulation_dates'][i] == ""): #if default value then
                sim_date = col5.text_input(label=' ',key=f'Date {i+1}',placeholder='(mm/dd/yy) - (mm/dd/yy)')
            else:
                sim_date = col5.text_input(label=' ',key=f'Date {i+1}',value=ss['simulation_dates'][i])
            
            # Add the user input to the list of metrics and range constraints
            range_constraints_list.append([min_value/100, max_value/100, increment_value/100])
            simulation_dates.append(sim_date)

    # adding footnotes
    st.markdown("---")
    foot_note_string = "1. If you want to fix the value of a metric, the Minimum will be the fixed value and Maximum would be (Minimum value+0.0001) with Increment value as 1%. <br> \
        For eg: One of the metric is PR13 and you want to exclude that metric, i.e it should have 0% weight, the Minimum value will be 0%, Maximum value will be 0.0001% and Increment value would be 1%.<br> \
        2. The Time Period field is optional. It is for display purposes. <br> \
        3. The sum of Minimum value for all metrics should be less than 100% and sum of Maximum value for all metrics should be greater than 100%. Kindly ensure that the Minimum and Maximum values are selected appropriately "
    st.markdown("""<style>.foot_note {font-size: 0.8em;font-style: italic;margin-left: 20px; font-weight: lighter;}</style>""",unsafe_allow_html=True)
    st.markdown('<p class="foot_note">'+foot_note_string+'</p>',unsafe_allow_html=True)
    st.markdown("---")
    #SECTION 2 - Show the user a summary of what they have entered -

    st.markdown("<h3 style='text-align: center;'>Input Summary Stats - </h3>", unsafe_allow_html=True)
    summary_df = pd.DataFrame(range_constraints_list, columns=['Min', 'Max', 'Increment'])
    summary_df.insert(0, 'Metric Name', ss['list_of_metrics'])
    #styling df - 
    summary_df_styled = summary_df.copy()
    for col in ['Min', 'Max', 'Increment']:
        summary_df_styled[col] = summary_df_styled[col].apply(lambda x: f'{x*100} %')
        summary_df_styled[col] = summary_df_styled[col].round(2)
        

    s1 = dict(selector='th', props=[('text-align', 'center')])
    s2 = dict(selector='td', props=[('text-align', 'center')])
    table = summary_df_styled.style.set_table_styles([s1,s2]).hide(axis=0).to_html()
    centered_table = f'<div style="display: flex; justify-content: center;">{table}</div>'  

    st.write(centered_table, unsafe_allow_html=True)

    st.markdown("---")
    # Adding A Button to Create Numpy Arrays - Potentially Costly Option | Therefore making it deliberate instead of auto
    if st.button("Process Combinations",help="This operation will trigger the creation of numpy arrays and generate all possible combinations"):
        ss.gen_rag = True
        ss['metric_df'] = summary_df
        ss['range_constraints_list'] = range_constraints_list

    #To Detect Change
    if ss['metric_df'] is not None and not ss['metric_df'].equals(summary_df):
        ss.gen_rag = False
    
    # Add a clause here to set gen_rag to false if there was a change in summary_df
    if ss.gen_rag:
        
        #Error Detection | QC here |
        if ((0 in ss['metric_df']['Max'].unique()) or (0 in ss['metric_df']['Increment'].unique())): #If 0 as max value or increment
            st.write("You have 0 in your constraints !")
        elif ss['metric_df'].duplicated('Metric Name').any(): #Duplicate Metric Name
            st.write("Duplicate Metric Name Found!")
        elif (ss['metric_df']['Max'].sum() < 1.0) or (ss['metric_df']['Min'].sum() > 1.0):
            st.write(f"No Combination Will Equate to 100%! Max Sum : {ss['metric_df']['Max'].sum()*100} Min Sum : {ss['metric_df']['Min'].sum()*100}")
        else:
            #Code To Create Range -
            items_list = []
            for weight,constraints in zip(ss['list_of_metrics'],ss['range_constraints_list']):
                weight_range_var = "{}_range".format(weight)
                rf = abs(Decimal(str(constraints[2])).as_tuple().exponent) #Round Off Value
                
                globals()[weight_range_var] = np.round(
                    np.arange(
                        constraints[0],
                        constraints[1]+e,
                        constraints[2],
                    ),
                    rf
                )
                items_list.append(globals()[weight_range_var])
            #This Section Should Print Statistics Before Brute Force :
            len_list = []
            comb_counter = 1
            for item in items_list:
                comb_counter *= len(item)
                len_list.append(len(item))
            
            st.warning('Please note: You must submit your inputs before you start processing results',icon='👋')
            #st.write("Number of Possible % Values for each range : ",str(len_list))
            st.write("Total Possible Combinations Pre 100% Sum Constraint : ",f'{comb_counter:,}')
            if comb_counter >= 1_000_000_000:
                st.error("Too many possible combinations, reconsider metric ranges ? ",icon='🚨')
                st.info("**Note For User**: If the total number of combinations is in the billions please make sure your system has enough memory \
                        \n_This will cause future  Operations to take significant time!_ ",icon='ℹ️')
        
            

            st.markdown("---")

            if st.button("Submit Combinations"):
                ss.submit_2 = True
                ss['items_list'] = items_list
                ss['comb_counter'] = comb_counter
                ss['simulation_dates']= simulation_dates
                ss['simulation_dates2']= simulation_dates2
                st.write(f"{comb_counter:,} combinations ready to filter and process !")
                ss.start_filter = False #to prevent auto rerun of submission of new numbers !
                ss.pro_com = False # To make sure process reruns if already run before
                st.switch_page('pages/3_Processing_Results.py')