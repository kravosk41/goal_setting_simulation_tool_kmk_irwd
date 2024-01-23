import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import polars as pl
from decimal import Decimal
import numpy as np
import time
import itertools
from stqdm import stqdm
import io

st.set_page_config(
    page_title="GST-Processing",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon='🤞'
)# add icon later

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

st.markdown("<h1 style='text-align: center;'>Processing Combinations</h1>", unsafe_allow_html=True)
st.markdown("<h6 style='text-align: center;'>Ensure That you Submitted Combinations</h6>",unsafe_allow_html=True)


if 'start_filter' not in ss: #tracks button click status
    ss.start_filter = False
if 'pro_com' not in ss: #tracks if results were done processing or not
    ss.pro_com = False
if 'open_download_sec' not in ss: # IF results got printed - Give option to download
    ss.open_download_sec = False

c1,c2,c3 = st.columns([5,5,1])
if c2.button("Start Processing"):
    ss.start_filter = True

st.markdown("---")

def process_1():
    comb_pd = pd.DataFrame()
    chunk_size = 1000000
    rows_processed = 0
    combinations = itertools.product(*ss['items_list'])
    progress_bar = st.progress(0,text = "Finding Combinations of weights that sum up to 100%...")

    while True:
        chunk = list(itertools.islice(combinations, chunk_size))
        rows_processed += len(chunk)

        if not chunk:
            break
        
        chunk_df = pd.DataFrame(chunk,columns = ss['list_of_metrics'])
        chunk_df = chunk_df[chunk_df.sum(axis=1)==1]
        comb_pd = pd.concat([comb_pd,chunk_df])
        progress_bar.progress(rows_processed/ss['comb_counter'])
    
    progress_bar.empty()

    if comb_pd.shape[0] == 0: #This means that there are no combinations that sum up to 100
        ss.pro_com = False
        st.write("There were no combinations that sum up to 100% ! 🙁 ")
        st.markdown("__(Try again with some different constraints, you might be really close)__")
        return #exiting out of process_1()
    
    #saving result - May not be necessary :
    comb_pd.to_parquet('comb_pd.parquet')

    # Define the boundaries of the bins
    bins = [0, 97, 99.001, 101.001, 103, 999]

    # Define the labels for the bins
    labels = ['a', 'b', 'c', 'd', 'e']


    def objective(*metric_weights):
        comp_weights = {}
        #populating comp_weights -
        for weight_name,weight_value in zip(ss['list_of_metrics'],metric_weights):
            comp_weights[weight_name] = weight_value
        
        #populating comp_volumes -
        comp_vols = {}
        for x,y in comp_weights.items():
            comp_vols[x] = ss['nation_goal_value'] * y
        
        work_df = ss['excel_file_df'].copy()
        computation_cols = ss['list_of_metrics']
        for col in computation_cols:
            work_df[str(col+'_w')] = (work_df[col] / work_df[col].sum()) * comp_vols[col]
        
        work_df['Final_Quota'] = sum(work_df[col + '_w'] for col in computation_cols)
        work_df['Attainment'] = (work_df['Actuals'] / work_df['Final_Quota']) * 100

        work_df['Att_Classifier'] = pd.cut(work_df['Attainment'], bins=bins, labels=labels)
        
        Att_Cat_Counts = work_df['Att_Classifier'].value_counts().to_dict()
        Att_Cat_Counts = dict(sorted(Att_Cat_Counts.items(), key=lambda item: item[0]))

        return_list = [
            work_df['Attainment'].std(),
            ((work_df['Attainment'] - 100)**2).sum()/work_df.shape[0],
            Att_Cat_Counts,
            work_df['Attainment'].min(),
            work_df['Attainment'].max(),
            work_df['Attainment'].mean()
        ]

        #For QC Inspection
        objective.work_df = work_df

        return(return_list)
    
    def apply_objective(row):
        result = objective(*row)
        return(pd.Series(result))
    
    #Applying Objective Function - this will take time
    stqdm.pandas(desc="Applying Objective Function to Combinations")
    comb_pd[['Standard_Deviation', 'MSE','Att_Cat_Counts','Min_Att','Max_Att','Avg_Att']] = comb_pd.progress_apply(apply_objective,axis=1)

    #Adding Secondary Comparitive Metrics - 
    comb_pd1 = comb_pd.copy()
    comb_pd1[['CAT_A', 'CAT_B', 'CAT_C', 'CAT_D', 'CAT_E']] = comb_pd['Att_Cat_Counts'].apply(lambda x: pd.Series([x['a'], x['b'], x['c'], x['d'], x['e']]))
    comb_pd1['Total'] = comb_pd1['CAT_B'] + comb_pd1['CAT_C'] + comb_pd1['CAT_D']
    comb_pd1 = comb_pd1.drop(columns='Att_Cat_Counts')
    
    #Store result
    ss['objective_df_pd'] = comb_pd1 
    ss['actual_combinations'] = comb_pd.shape[0]

    #Processing Complete -
    ss.pro_com = True

def show_res_1():
    #If results are calculated show the following -
    
    #Removed Polars Sorting API - Not needed for now , Manually Sorting and keeping top 5
    st.subheader("Objective Result - ")
    # st.dataframe(ss['objective_df_pd'],height= 180,hide_index=True)
    ss['style_df_main'] = ss['objective_df_pd'].copy() #Creating a Separate Copy Just for printing 
    #Applying Formatting Fixes -
    for col in ['Min_Att','Max_Att','Avg_Att']:
        ss['style_df_main'][col] = ss['style_df_main'][col].round(2)
        ss['style_df_main'][col] = ss['style_df_main'][col].apply(lambda x: f'{x} %')
    for col in ss['list_of_metrics']:
        ss['style_df_main'][col] = (ss['style_df_main'][col]*100).round(2)
        ss['style_df_main'][col] = ss['style_df_main'][col].apply(lambda x: f'{x} %')
    
    ss['style_df_main']['Standard_Deviation'] = ss['style_df_main']['Standard_Deviation'].round(3)
    ss['style_df_main']['MSE'] = ss['style_df_main']['MSE'].round(3)
    #### END OF FORMAT FIXES ###
    st.dataframe(ss['style_df_main'],height= 180,hide_index=True)
    with st.expander("Get Help on Column Names ☝️"):
        st.markdown("""
        ### Legend
        | Column Name | Value |
        | --- | --- |
        | CAT_A | 0% to 97% |
        | CAT_B | 97% to 99% |
        | CAT_C | 99% to 100% |
        | CAT_D | 100% to 103% |
        | CAT_E | 103% to ∞ |
        | Total | B + C + D |
        """)


#After showing full data
#sort data by multiple columns and show top five [std LH, total and cat_c HL]    
#If button is pressed -

if ss.start_filter:
    
    #check if combinations are submited & uploaded  AND if results have already been processed or not
    if 'submit_2' in ss and (ss.submit_2 and ss.items_list) and ss.pro_com == False:

        #Start Processing Data
        process_1()

        #Check if you actually got valid results to show results for 
        if ss.pro_com:
            #Then Show Results
            show_res_1()
            #Open Downloads Section -
            ss.open_download_sec = True

    #when calculation has already been done - 
    elif ('submit_2' in ss) and (ss.submit_2 and ss.items_list) and ss.pro_com:

        #Just Show Results -
        show_res_1()

        #Open Downloads Section -
        ss.open_download_sec = True
    
    else:
        st.write("Did you submit your combinations ?")

    
    
#Downloads Section - #FUTURE TO DO : Explore ss.cache_data, there seems to be a delay for this to populate
if ss.open_download_sec and ss.pro_com:

    st.markdown("---")
    c4,c5 = st.columns(2)
    c4.subheader("View Results in Excel -")

    buffer = io.BytesIO()
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet.
        ss['objective_df_pd'].to_excel(writer, sheet_name='Sheet1',index=False)
        # Close the Pandas Excel writer and output the Excel file to the buffer
        #writer.close()

        c5.download_button(
            label="Download Excel worksheet",
            data=buffer,
            file_name="GST_objective.xlsx",
            mime="application/vnd.ms-excel"
        )