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
import matplotlib.pyplot as plt
import statsmodels.api as sm
import plotly.express as px

st.set_page_config(
    page_title="GST-Processing",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon='🤞'
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

if 'start_filter' not in ss: #tracks button click status
    ss.start_filter = False
if 'pro_com' not in ss: #tracks if results were done processing or not
    ss.pro_com = False
if 'open_download_sec' not in ss: # IF results got printed - Give option to download
    ss.open_download_sec = False

# These are used in objective() | Territory Attainment Classifier 
# Define the boundaries of the bins
bins = [0, 97, 99.001, 101.001, 103, 999]
# Define the labels for the bins
labels = ['a', 'b', 'c', 'd', 'e']

# Functions -
# 1. objective - This is a helper function to calcuate metrics for a given list of weights 
# Input : N number of goal setting weights , Return Type Flag
# Output : Standard Deviation, MSE, Attainment Type Classifer (in dict form),
#          min, max and mean attainment | Territory Level Data for a given Combination of weights
def objective(*metric_weights,terr_flag=False):
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

    #corr numbers-
    corr_dict={}
    for col in computation_cols:
        cor_var_name = col + '_cor'
        corr_dict[cor_var_name] = (work_df[col].corr(work_df['Attainment'])**2)
    corr_dict['Goals_Accuracy'] = (work_df['Actuals'].corr(work_df['Final_Quota'])**2)

    return_list = [
        work_df['Attainment'].std(),
        Att_Cat_Counts,
        work_df['Attainment'].min(),
        work_df['Attainment'].max(),
        work_df['Attainment'].mean(),
        corr_dict
    ]
    # if terr_flag is true , return terr level data instead of
    if terr_flag==True:
        return work_df
    else:
        return(return_list)

# 2. process_1 - Controller Function | Happens on Button Press | Also calls objective()
# Also Formats the df into more user friendly format | For printing only !
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
    #comb_pd.to_parquet('comb_pd.parquet')
    
    def apply_objective(row):
        result = objective(*row)
        return(pd.Series(result))
    
    #Applying Objective Function - this will take time
    stqdm.pandas(desc="Applying Objective Function to Combinations")
    comb_pd[['Standard_Deviation','Att_Cat_Counts','Min_Att','Max_Att','Avg_Att','corr_dict']] = comb_pd.progress_apply(apply_objective,axis=1)

    #Adding Secondary Comparitive Metrics - 
    comb_pd1 = comb_pd.copy()
    comb_pd1[['CAT_A', 'CAT_B', 'CAT_C', 'CAT_D', 'CAT_E']] = comb_pd1['Att_Cat_Counts'].apply(lambda x: pd.Series([x['a'], x['b'], x['c'], x['d'], x['e']]))
    comb_pd1['Total'] = comb_pd1['CAT_B'] + comb_pd1['CAT_C'] + comb_pd1['CAT_D']
    comb_pd1 = comb_pd1.drop(columns='Att_Cat_Counts')

    #Pulling Correlation Metrics - 
    comb_pd1[[col+'_corr' for col in ss['list_of_metrics']]+['Goals_Accuracy']] = comb_pd1['corr_dict'].apply(pd.Series)
    comb_pd1 = comb_pd1.drop(columns='corr_dict')

    #Apply Ranking here TODO
    ### Adding Ranks ### -
    comb_pd1['Total_r'] = comb_pd1['Total'].rank(method='dense',ascending=False)
    comb_pd1['CAT_C_r'] = comb_pd1['CAT_C'].rank(method='dense',ascending=False)
    comb_pd1['Standard_Deviation_r'] = comb_pd1['Standard_Deviation'].rank(method='dense',ascending=True)
    comb_pd1['Goals_Accuracy_r'] = comb_pd1['Goals_Accuracy'].rank(method='dense',ascending=False)
    ### Adding Ranks for Metric Corr columns - ###
    for col in ss['list_of_metrics']:
        comb_pd1[col+'_abs_corr'] = comb_pd1[col+'_corr'].abs() #converting to abs
        comb_pd1[col+'_r'] = comb_pd1[col+'_abs_corr'].rank(method='dense', ascending=True)
    ### Base Formula ###
    #### Non Changing Fractions ####
    comb_pd1['WT_RANK'] = comb_pd1['Total_r']*0.3 + comb_pd1['CAT_C_r']*0.2 + comb_pd1['Standard_Deviation_r']*0.1 \
        + comb_pd1['Goals_Accuracy_r']*0.1
    #### Changing Fractions ####
    for metric in ss['list_of_metrics']:
        comb_pd1['WT_RANK'] += comb_pd1[metric+'_r'] * (0.3 / len(ss['list_of_metrics']))

    ### Dropping Redundant Columns ###
    comb_pd1.drop(columns=[c for c in comb_pd1.columns if c.endswith('_r') or c.endswith('_abs_corr')],inplace=True)

    ### Sorting on Final Weighted Rank ###
    comb_pd1['Final_Rank'] = comb_pd1['WT_RANK'].rank(method='first',ascending=True)
    comb_pd1= comb_pd1.sort_values('Final_Rank',ascending=True)
    comb_pd1.drop(columns='WT_RANK',inplace=True)

    #Store result
    ss['objective_df_pd'] = comb_pd1 
    ss['actual_combinations'] = comb_pd.shape[0]

    #Porting over calc work from res and vis functions -
    
    ss['style_df_main'] = ss['objective_df_pd'].copy() #Creating a Separate Copy Just for printing 
    #sorting it by required order - 
    #ss['style_df_main'].sort_values(by = ['Total','CAT_C','Standard_Deviation'],ascending=[False,False,True],ignore_index=True,inplace=True)
    #Applying Formatting Fixes -
    for col in ['Min_Att','Max_Att','Avg_Att']:
        ss['style_df_main'][col] = ss['style_df_main'][col].round(2)
        ss['style_df_main'][col] = ss['style_df_main'][col].apply(lambda x: f'{x} %')
    for col in ss['list_of_metrics']:
        ss['style_df_main'][col] = (ss['style_df_main'][col]*100).round(2)
        ss['style_df_main'][col] = ss['style_df_main'][col].apply(lambda x: f'{x} %')
    
    ss['style_df_main']['Standard_Deviation'] = ss['style_df_main']['Standard_Deviation'].round(3)
    #ss['style_df_main']['MSE'] = ss['style_df_main']['MSE'].round(3)

    #adding renamed columns to from legend - 
    ss['style_df_main'] = ss['style_df_main'].rename(columns={
        'CAT_A':'0% to 97%',
        'CAT_B':'97% to 99%',
        'CAT_C':'99% to 101%',
        'CAT_D':'101% to 103%',
        'CAT_E':'103% to ∞',
        'Total':'97% to 103%'
    })
    #### END OF FORMAT FIXES ###
    #Processing Complete -
    ss.pro_com = True

# 3. visuals_1 - To Encapsulate all graphical and plot work | Currently using Plotly.express charts
# Future TO DO | Explore @st.cache_data to make page switch processing faster.
def visuals_1():

    # Isolate top 5 and Prepare Data - 
    #new ranking method-
    top_five_df = ss['objective_df_pd'].head(5).copy()#This could be controlled by an argument in the future
    top_five_df.drop(columns='Final_Rank',inplace = True)
    top_five_df['Method'] = ['M' + str(i) for i in range(1, len(top_five_df) + 1)]
    #rname - 
    top_five_df = top_five_df.rename(columns={
        'CAT_A':'0% to 97%',
        'CAT_B':'97% to 99%',
        'CAT_C':'99% to 101%',
        'CAT_D':'101% to 103%',
        'CAT_E':'103% to ∞',
        'Total':'97% to 103%'
    })

    #Giving a name to the combination - 'M<n>'
    
    #Function to get back terr level data -
    def get_terr_level_df(row):
        df = objective(*row,terr_flag=True) #Passing True to get terr df instead of metrics
        return(df)
    
    #Fetching the terr level data for top 5 rows & storing in explict df names
    for i in range(len(top_five_df)):
        argument_row = top_five_df[['Method'] + ss['list_of_metrics']].iloc[i]
        #isolate just the weights from results
        new_terr_df_name = str(argument_row.iloc[0]) + '_terr_df' 
        #replaced space with _ to have valid df name
        globals()[new_terr_df_name] = get_terr_level_df(argument_row[1:])
        #passing arguments and storing in globals directly

    # End of Calculations 
    # Start Drawing -
    # c4,c5 = st.columns(2) #one for TOP 5 | other for group graph 1
    # c4.write("")
    st.subheader("__Top 5 Combinations -__")
    # for _ in range(5):  # Adjust the range for more or less space
    #     c4.write("")

    #c4.dataframe(top_five_df[['Comb_Name'] + ss['list_of_metrics']],hide_index=True) # limited view
    col_list2 = list(top_five_df.columns)
    col_list2 = [col_list2[-1]] + col_list2[:-1]
    #for column renaming-
    rename_dict1 = {'Standard_Deviation':'Std_Dev_Att','Method':'Methodology'}
    for metric in ss['list_of_metrics']:
        key = metric+'_corr'
        value = metric+'_Att_R²'
        rename_dict1[key] = value

    st.dataframe(top_five_df,hide_index = True,use_container_width=True,column_order=col_list2,
                 column_config=rename_dict1)
    with st.expander(':information_source: Info on Ranking Methodology  ↙️'):
        st.subheader('Weighted Rank Calcualtion')
        st.markdown("""
        The weighted rank is computed as follows:

        1. **Rank of # of Territories b/w 97%-103%**: Multiply by 0.3 and consider the range from high (H) to low (L).
        2. **Rank of # of Territories b/w 99%-101%**: Multiply by 0.2 and consider the range from high (H) to low (L).
        3. **Rank of Standard Deviation (Std Dev)**: Multiply by 0.1 and consider the range from low (L) to high (H).
        4. **Rank of Goal Accuracy**: Multiply by 0.1 and consider the range from high (H) to low (L).
        5. **Rank of each metric (divided by the total number of metrics)**: Multiply by 0.3 and consider the range from low (L) to high (H).

        The final weighted rank is a combination of these components, with the last part adjusted by a multiplier that is the reciprocal of 30%.
        
        _correlation values for the metrics are converted to absolute before ranking_
        """)
    #with c5:
    df_long = top_five_df[['Method','0% to 97%','97% to 99%','99% to 101%','101% to 103%','103% to ∞']]
    df_long = df_long.melt('Method', var_name='Category', value_name='Values')
    fig = px.bar(df_long, 
            x="Method", 
            y="Values", 
            color="Method",
            facet_col="Category",
            facet_col_wrap=5,
            text='Values',
            labels={"Values": "# Territories", "Category": "Category", "Method": "Method"},
            color_discrete_map ={'M1': '#7cb342','M2':'#23dedb','M3':'#4c57ba','M4':'#f57f17','M5':'#b71c1c'},
            title="Attainment Distribution Chart")

    fig.update_layout(showlegend=True)
    fig.update_layout(title_font_size=20,title_x=0.45, title_xref='paper')
    st.plotly_chart(fig,use_container_width=True)
    st.markdown("---")
    st.markdown("<h2 style='text-align: center;'>Fairness Testing and Goals Accuracy</h2>", unsafe_allow_html=True)
    #st.write('<style>div.row-widget.stRadio > div{flex-direction:row;justify-content: center;}</style>', unsafe_allow_html=True)
    split1,split2 = st.columns(2)
    with split1:
        comb_sel1 = st.radio('Y Axis -  :',top_five_df['Method'].unique(),key='rk1',horizontal=True)
        comb_sel1 = comb_sel1.replace(' ','_')
        metr_sel1 = st.radio('X Axis-',ss['list_of_metrics'],key='rk2',horizontal=True)
        fig = px.scatter(
            data_frame = globals()[comb_sel1+'_terr_df'],
            x = metr_sel1, #pick a metric
            y = 'Attainment',
            #color_discrete_sequence=['blue'],
            trendline='ols',
            trendline_color_override = 'orange',
            title=metr_sel1 + ' vs Attainment for ' + comb_sel1,
        )
        fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper')
        # For R Squared - 
        results = px.get_trendline_results(fig)
        r_squared = results.iloc[0]["px_fit_results"].rsquared
        fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
        if ss['simulation_dates'][ss['list_of_metrics'].index(metr_sel1)] != "":
            fig.add_annotation(x=0.5,y=-0.3,
                            text=f"Baseline Period for {metr_sel1} : {ss['simulation_dates'][ss['list_of_metrics'].index(metr_sel1)]}",
                            xref="paper",yref="paper",showarrow=False,font={'size':16})
        fig.update_layout(yaxis_title = 'Attainment (%)')
        st.plotly_chart(fig,use_container_width=True)
        #Chart 2-
        fig = px.scatter(
            data_frame = globals()[comb_sel1+'_terr_df'],
            x = 'Actuals', #pick a metric
            y = 'Final_Quota',
            #color_discrete_sequence=['cyan'],
            trendline='ols',
            trendline_color_override = 'orange',
            title='Goal Accuracy'
        )
        fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper',xaxis_title=ss.QTR +"'"+ str(ss.YEAR)[-2:] + ' Actuals',yaxis_title=ss.QTR +"'"+ str(ss.YEAR)[-2:] + ' Final Quota')
        # For R Squared - 
        results = px.get_trendline_results(fig)
        r_squared = results.iloc[0]["px_fit_results"].rsquared
        fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
        st.plotly_chart(fig,use_container_width=True)     
    with split2:
        comb_sel2 = st.radio('Y Axis -  :',top_five_df['Method'].unique(),key='rk3',horizontal=True,index=2)
        comb_sel2 = comb_sel2.replace(' ','_')
        metr_sel2 = st.radio('X Axis-',ss['list_of_metrics'],key='rk4',horizontal=True)
        fig = px.scatter(
            data_frame = globals()[comb_sel2+'_terr_df'],
            x = metr_sel2, #pick a metric
            y = 'Attainment',
            #color_discrete_sequence=['cyan'],
            trendline='ols',
            trendline_color_override = 'orange',
            title=metr_sel2 + ' vs Attainment for ' + comb_sel2
        )
        fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper')
        # For R Squared - 
        results = px.get_trendline_results(fig)
        r_squared = results.iloc[0]["px_fit_results"].rsquared
        fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
        if ss['simulation_dates'][ss['list_of_metrics'].index(metr_sel2)] != "":
            fig.add_annotation(x=0.5,y=-0.3,
                            text=f"Baseline Period for {metr_sel2} : {ss['simulation_dates'][ss['list_of_metrics'].index(metr_sel2)]}",
                            xref="paper",yref="paper",showarrow=False,font={'size':16})
        fig.update_layout(yaxis_title = 'Attainment (%)')
        st.plotly_chart(fig,use_container_width=True)
        #Chart 2-
        fig = px.scatter(
            data_frame = globals()[comb_sel2+'_terr_df'],
            x = 'Actuals', #pick a metric
            y = 'Final_Quota',
            #color_discrete_sequence=['cyan'],
            trendline='ols',
            trendline_color_override = 'orange',
            title='Goal Accuracy'
        )
        fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper',xaxis_title=ss.QTR +"'"+ str(ss.YEAR)[-2:] + ' Actuals',yaxis_title=ss.QTR +"'"+ str(ss.YEAR)[-2:] + ' Final Quota')
        # For R Squared - 
        results = px.get_trendline_results(fig)
        r_squared = results.iloc[0]["px_fit_results"].rsquared
        fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
        st.plotly_chart(fig,use_container_width=True) 

    
                     
#4. show_res_1 - Controller Function | Happens After Processing already complete 
# Calls visuals_1 when required 
def show_res_1():
    #If results are calculated show the following -
    st.markdown("<h2 style='text-align: center;'>Result -</h2>", unsafe_allow_html=True)
    ph1,ph2,ph3 = st.columns([1,6,1])
    col_list = list(ss['style_df_main'].columns)
    col_list = [col_list[-1]] + col_list[:-1]

    #for column renaming-
    rename_dict1 = {'Standard_Deviation':'Std_Dev_Att','Final_Rank':'Final Rank'}
    for metric in ss['list_of_metrics']:
        key = metric+'_corr'
        value = metric+'_Att_R²'
        rename_dict1[key] = value

    st.dataframe(ss['style_df_main'],height= 220,use_container_width=True,hide_index=True,column_order=col_list,
                 column_config=rename_dict1) #This is calc in process_1
    with st.expander("Get Help on Column Names ☝️"):
        st.markdown("""
        ### Legend
        | Column Name | Value |
        | --- | --- |
        | CAT_A | 0% to 97% |
        | CAT_B | 97% to 99% |
        | CAT_C | 99% to 101% |
        | CAT_D | 101% to 103% |
        | CAT_E | 103% to ∞ |
        | Total | B + C + D |
        """,unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<h2 style='text-align: center;'>Result Visualization</h2>", unsafe_allow_html=True)
    visuals_1() #call graph maker

    #Once Results are done being printed Set Download Section to True ?

#MAIN START :  Main Control Section #####
st.markdown("<h1 style='text-align: center;'>Processing Combinations</h1>", unsafe_allow_html=True)
if ss.pro_com == False:
    st.info('Ensure That you Submitted Combinations', icon="⚠️")
c1,c2,c3 = st.columns([5,5,1])
if c2.button("Start Processing"):
    ss.start_filter = True


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
        writer.close()

        c5.download_button(
            label="Download Excel worksheet",
            data=buffer,
            file_name="GST_objective.xlsx",
            mime="application/vnd.ms-excel"
        )