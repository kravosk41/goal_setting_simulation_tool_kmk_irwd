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
#   #   #   #   #   #   #   #
# Session State Management - 
if 'start_filter' not in ss: #tracks button click status
    ss.start_filter = False
if 'pro_com' not in ss: #tracks if results were done processing or not
    ss.pro_com = False
# to prevent reruns ?:
if ss.pro_com == False:
    ss.start_filter = False
if 'open_download_sec' not in ss: # IF results got printed - Give option to download
    ss.open_download_sec = False
if 'custom_weights_input' not in ss:
    ss['custom_weights_input'] = [0.0 for _ in range(ss['number_of_metrics'])]
#   #   #   #   #   #   #   #

# These are used in objective() | Territory Attainment Classifier 
# Define the boundaries of the bins
bins = [0, 97, 99.001, 101.001, 103, 999]
# Define the labels for the bins
labels = ['a', 'b', 'c', 'd', 'e']

#1. Objective : To get back metrics for a combination of weights
def objective(*metric_weights,terr_flag=False,mode_flag=1):
    comp_weights = {}
    #populating comp_weights -
    for weight_name,weight_value in zip(ss['list_of_metrics'],metric_weights):
        comp_weights[weight_name] = weight_value
    
    #populating comp_volumes -
    comp_vols = {}
    if mode_flag == 1:
        for x,y in comp_weights.items():
            comp_vols[x] = ss['nation_goal_value'] * y
    elif mode_flag == 2:
        for x,y in comp_weights.items():
            comp_vols[x] = ss['nation_goal_value2'] * y 
    
    if mode_flag == 1:
        work_df = ss['excel_file_df'].copy()
    elif mode_flag == 2:
        work_df = ss['excel_file_df2'].copy()
    else:
        print('INVALID PARAM')
        return
    
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
    
#2. Process : Pass Objective to all possible combinations | and store valid result
def process_data(mode):
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
        return #exiting out of process_data()
	
    def apply_objective(row,fl):
        result = objective(*row,False,mode_flag=fl)
        return(pd.Series(result))
	
	#Applying Objective Function - this will take time
    stqdm.pandas(desc=f"Applying Objective Function to Combinations with data {mode}")
    comb_pd[['Standard_Deviation','Att_Cat_Counts','Min_Att','Max_Att','Avg_Att','corr_dict']] = comb_pd.progress_apply(apply_objective,axis=1,args=(mode,))

    #Adding Secondary Comparitive Metrics - 
    comb_pd1 = comb_pd.copy()
    comb_pd1[['CAT_A', 'CAT_B', 'CAT_C', 'CAT_D', 'CAT_E']] = comb_pd1['Att_Cat_Counts'].apply(lambda x: pd.Series([x['a'], x['b'], x['c'], x['d'], x['e']]))
    comb_pd1['Total'] = comb_pd1['CAT_B'] + comb_pd1['CAT_C'] + comb_pd1['CAT_D']
    comb_pd1 = comb_pd1.drop(columns='Att_Cat_Counts')
	
    #Pulling Correlation Metrics - 
    comb_pd1[[col+'_corr' for col in ss['list_of_metrics']]+['Goals_Accuracy']] = comb_pd1['corr_dict'].apply(pd.Series)
    comb_pd1 = comb_pd1.drop(columns='corr_dict')
	
	#Ranking viablity of obtained methods.
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

    #Store result - OLD | Now instead of storing we return the result.
    #ss['objective_df_pd'] = comb_pd1 
    
    return(comb_pd1)

#3. Style : converts the resultant dataframe into a user friendly format
#Stylizing Objective Dataframe
def style(df):    
    #Applying Formatting Fixes -
    for col in ['Min_Att','Max_Att','Avg_Att']:
        df[col] = df[col].round(2)
        df[col] = df[col].apply(lambda x: f'{x} %')
    for col in ss['list_of_metrics']:
        df[col] = (df[col]*100).round(2)
        df[col] = df[col].apply(lambda x: f'{x} %')
    
    df['Standard_Deviation'] = df['Standard_Deviation'].round(3)

    #adding renamed columns to from legend - 
    df = df.rename(columns={
        'CAT_A':'≤ 97%','CAT_B':'97% to 99%',
        'CAT_C':'99% to 101%','CAT_D':'101% to 103%',
        'CAT_E':'> 103%','Total':'97% to 103%'
    })
    return(df)

#4. Result : Shows Stylzed version of objective dataframe 
def result(mode,style_df):
 
    def printer(df):
        col_list = list(df.columns)
        col_list = [col_list[-1]] + col_list[:-1]
        #for column renaming-
        rename_dict1 = {'Standard_Deviation':'Std_Dev_Att','Final_Rank':'Final Rank'}
        for metric in ss['list_of_metrics']:
            key = metric+'_corr'
            value = metric+'_Att_R²'
            rename_dict1[key] = value
        st.dataframe(
            df,height= 220,
            use_container_width=True,
            hide_index=True,
            column_order=col_list,
            column_config=rename_dict1
        )
        return

    if mode == 1:
        df_head_label = f'{ss.QTR} {ss.YEAR}'
    else:
        df_head_label = f'{ss.QTR2} {ss.YEAR2}'

    st.markdown(f"<h3 style='text-align: left;'>{df_head_label} -</h3>", unsafe_allow_html=True)
    printer(style_df)

#5. Result's Parent : calls result(1), or (2) 
def result_main():
    st.markdown("<h2 style='text-align: center;'>Results -</h2>", unsafe_allow_html=True)
    result(1,style(ss['objdf1'].copy()))
    if ss.MODE == 2:
        result(2,style(ss['objdf2'].copy()))
    
    with st.expander("Get Help on Column Names ☝️"):
        l1,l2,l3 = st.columns([1,5,1])
        l2.markdown("""
        ### Legend
        | Column Name | Definition | Ideal Value | 
        | --- | --- | --- |
        | Final Rank | Weighted Rank calculated to decide the best Goal Setting Methodology | Lower the Final Rank, better the methodology |
        | Std_Dev_Att | It is the variance of Attainment across Territories. | Lower the Std_Dev_Att, better the methodology |
        | Min_Att | Minimum Attainment amongst territories |  |
        | Max_Att | Maximum Attainment amongst territories |  |
        | Avg_Att | Average Attainment amongst territories |  |
        | <= 97% | # territories with attainment <=97% | At 100% National Attainment, lower the # of territories in this range, better the methodology |
        | 97% to 99% | # territories with attainment b/w 97% and 99% | At 100% National Attainment, # of territories should be greater than # of territories falling in 0% to 97% range |
        | 99% to 101% | # territories with attainment b/w 99% and 101% | At 100% National Attainment, Maximum # of territories should fall in this category |
        | 101% to 103% | # territories with attainment b/w 101% and 103% | At 100% National Attainment, # of territories should be greater than # of territories falling in 103% to infinite range |
        | > 103% | # territories with attainment >103% | At 100% National Attainment, lower the # of territories in this range, better the methodology |
        | Metric_Att_R² | Checks the relation b/w Attainment vs Baseline Metrics | Lower the Metric_Att_R2, better the methodology |
        | Goals_Accuracy | Checks the relation b/w Actuals vs Simulated Goals | Higher the Goals vs Actuals correlation, better the methodology |
        """,unsafe_allow_html=True)
    st.markdown('---')

#6. Custom Weight Input : Prints a Section to Store Custom weights for experimentaiton
def input():
    st.markdown("<h2 style='text-align: center;'>Enter a Custom Combination of Weights</h2>", unsafe_allow_html=True)
    custom_weights_input = []
    with st.expander("Custom Weights Input - "):
        ci1,ci2 = st.columns(2)
        for i in range(ss['number_of_metrics']):
            ci1.markdown(
                f"<h2 style = 'text-align: center;padding: 22px;'>{str(ss['list_of_metrics'][i])}</h2>"
                , unsafe_allow_html=True
            )
            weight  = ci2.number_input(
                label=' ',
                key = f'custom weight for metric{i+1}',
                min_value=0.0,max_value=100.0,step=1.0,
                value = ss['custom_weights_input'][i]*100
            )
            custom_weights_input.append(weight/100)
    
        # pass to session state - 
        ss['custom_weights_input'] = custom_weights_input
        if sum(ss['custom_weights_input']) not in [0,1]:
            val = sum(ss['custom_weights_input']) * 100
            st.warning(f'Your Weights Dont Add Up to 100% yet!  :  {val}')

        #Processing Data 
        data = {ss['list_of_metrics'][i] : ss['custom_weights_input'][i] for i in range(ss['number_of_metrics'])}
        def get_full_df(mode):
            df = pd.DataFrame(data, index=[0])
            row = objective(*df.loc[0],False,mode_flag=mode)
            df[['Standard_Deviation','Att_Cat_Counts','Min_Att','Max_Att','Avg_Att','corr_dict']] = pd.Series(row)
            df.drop(columns=['Att_Cat_Counts','corr_dict'],inplace=True) # dropping these because they flow with nulls here
            df[['CAT_A','CAT_B','CAT_C','CAT_D','CAT_E']] = pd.Series(row[1])
            df['Total'] = df['CAT_B'] + df['CAT_C'] + df['CAT_D']
            df[[col+'_corr' for col in ss['list_of_metrics']]+['Goals_Accuracy']] = pd.Series(row[5])

            return (df)
        
        ss['custom_df1'] = get_full_df(1)
        if ss.MODE == 2:
            ss['custom_df2'] = get_full_df(2)
    
#7. Data Processing 2 : Filters and Prepares Data for Visualization | Picks top N records and combines with custom input
def process_data_vis(mode,n):
    objective_df = ss[f'objdf{mode}'] #pick data -
    top_rank_df = objective_df.head(n).copy() #Isolate Top n(2) contenders 
    top_rank_df.drop(columns='Final_Rank',inplace = True) # Replacing this with a method number so dropping
    top_rank_df['Method'] = ['M' + str(i) for i in range(1, len(top_rank_df) + 1)] #Giving a name to the combination - 'M<n>'

    #getting custom input row:
    if sum(ss['custom_weights_input']) == 1:
        cr = ss[f'custom_df{mode}']
        cr[['Method']] = ['C1'] #custom 1
        top_rank_df = pd.concat([top_rank_df, cr], sort=False)

    #top_rank_df.reset_index(inplace=True)


    # Populating terr level data for each combination -
    # two choices | list / dict of dfs ? or populate all in globals - would be tricky to manage for mode = 2
    rank_terr_dfs =[]
    for i in range(len(top_rank_df)):
        argument = top_rank_df[ss['list_of_metrics']].iloc[i]
        rank_terr_dfs.append(objective(*argument,terr_flag=True,mode_flag=mode))
    
    return(top_rank_df,rank_terr_dfs)

# Data Visualization : Renders all the needed graphs and plots
#8. TOP N combinations + Custom Combination
def visuals(mode,n):
    if mode == 1:
        label_text = f'{ss.QTR} {ss.YEAR}'
    elif mode == 2:
        label_text = f'{ss.QTR2} {ss.YEAR2}'
    
    st.subheader(f"__Top {n} Combinations ({label_text})-__")
    col_list = list(ss[f'rankdf{mode}'].columns)
    col_list = [col_list[-1]] + col_list[:-1]
    #for column renaming-
    df= style(ss[f'rankdf{mode}'].copy())
    rename_dict = {'Standard_Deviation':'Std_Dev_Att','Method':'Methodology'}
    for metric in ss['list_of_metrics']:
        key = metric+'_corr'
        value = metric+'_Att_R²'
        rename_dict[key] = value
    st.dataframe(df,hide_index = True,use_container_width=True,column_order=col_list,column_config=rename_dict)

#8.1 Attainment Distribution Chart
def visuals2(mode,n):
    if sum(ss['custom_weights_input']) == 1:
        n = n+1
    if mode == 1:
        label_text = f'{ss.QTR} {ss.YEAR}'
    elif mode == 2:
        label_text = f'{ss.QTR2} {ss.YEAR2}'

    df = ss[f'rankdf{mode}'].copy()
    df = df.rename(columns={'CAT_A':'≤ 97%','CAT_B':'97% to 99%','CAT_C':'99% to 101%','CAT_D':'101% to 103%','CAT_E':'> 103%','Total':'97% to 103%'})
    df_long = df[['Method','≤ 97%','97% to 99%','99% to 101%','101% to 103%','> 103%']]
    df_long = df_long.melt('Method', var_name='Category', value_name='Values')

    fig = px.bar(df_long, 
        x="Method", 
        y="Values", 
        color="Method",
        facet_col="Category",
        facet_col_wrap=5, # this will remain 5
        text='Values',
        labels={"Values": "# Territories", "Category": "Category", "Method": "Method"},
        title=f"Attainment Distribution Chart ({label_text})"
    )
    fig.update_layout(showlegend=True)
    fig.update_layout(title_font_size=20,title_x=0.45, title_xref='paper')
    st.plotly_chart(fig,use_container_width=True)
    st.markdown("---")

#8.2 Fairness Testing and Goals Accuracy
def visuals3(mode,n):
    df = ss[f'rankdf{mode}'].copy()
    st.markdown('---')
    if mode == 1:
        label_text = f'{ss.QTR} {ss.YEAR}'
    elif mode == 2:
        label_text = f'{ss.QTR2} {ss.YEAR2}'
    st.markdown(f"<h3 style='text-align: center;'>Data Source : {label_text}</h3>", unsafe_allow_html=True)
    split1,split2 = st.columns(2)
    with split1:
        comb_list = list(df['Method'].unique())
        comb_sel1 = st.radio('Y Axis -  :',df['Method'].unique(),key=f'rk1{mode}',horizontal=True)
        metr_sel1 = st.radio('X Axis-',ss['list_of_metrics'],key=f'rk2{mode}',horizontal=True)
        comb_number = comb_list.index(comb_sel1)
        fig = px.scatter(
            data_frame = ss[f'rankdf{mode}_terrs'][comb_number], 
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
            data_frame = ss[f'rankdf{mode}_terrs'][comb_number],
            x = 'Actuals', #pick a metric
            y = 'Final_Quota',
            #color_discrete_sequence=['cyan'],
            trendline='ols',
            trendline_color_override = 'orange',
            title='Goal Accuracy'
        )
        if mode == 1:
            x_label_text = f"{ss.QTR}'{str(ss.YEAR)[-2:]} Actuals" 
            y_label_text = f"{ss.QTR}'{str(ss.YEAR)[-2:]} Simulated Quota"
        elif mode == 2:
            x_label_text = f"{ss.QTR2}'{str(ss.YEAR2)[-2:]} Actuals"
            y_label_text = f"{ss.QTR2}'{str(ss.YEAR2)[-2:]} Simulated Quota"
        fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper',xaxis_title=x_label_text ,yaxis_title=y_label_text)
        # For R Squared - 
        results = px.get_trendline_results(fig)
        r_squared = results.iloc[0]["px_fit_results"].rsquared
        fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
        st.plotly_chart(fig,use_container_width=True)
    
    with split2: 
        comb_list = list(df['Method'].unique())
        comb_sel2 = st.radio('Y Axis -  :',df['Method'].unique(),key=f'rk3{mode}',horizontal=True,index=1)
        metr_sel2 = st.radio('X Axis-',ss['list_of_metrics'],key=f'rk4{mode}',horizontal=True)
        comb_number = comb_list.index(comb_sel2)
        fig = px.scatter(
            data_frame = ss[f'rankdf{mode}_terrs'][comb_number],
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
            data_frame = ss[f'rankdf{mode}_terrs'][comb_number],
            x = 'Actuals', #pick a metric
            y = 'Final_Quota',
            #color_discrete_sequence=['cyan'],
            trendline='ols',
            trendline_color_override = 'orange',
            title='Goal Accuracy'
        )
        fig.update_layout(title_font_size=20,title_x=0.35, title_xref='paper',xaxis_title=x_label_text,yaxis_title=y_label_text)
        # For R Squared - 
        results = px.get_trendline_results(fig)
        r_squared = results.iloc[0]["px_fit_results"].rsquared
        fig.add_annotation(x=0.95,y=0.95,text=f"R²: {r_squared:.5f}",showarrow=False,font={'size':25,'color':'black'},xref="paper",yref="paper",align="right",bgcolor="#ff7f0e")
        st.plotly_chart(fig,use_container_width=True) 

#9. visual's parent : calls visuals(1) or (2)
def visuals_main():
    st.markdown('---')
    st.markdown("<h2 style='text-align: center;'>Result Visualization</h2>", unsafe_allow_html=True)
    visuals(1,2)
    if ss.MODE == 2:
        visuals(2,2)
    with st.expander(':information_source: Info on Ranking Methodology  ↙️'):
        st.subheader('Weighted Rank Calcualtion')
        st.markdown("""
        The weighted rank is computed as follows:

        1. **Rank of # of Territories b/w 97%-103%**: Multiply by 0.3 and consider the range from high (H) to low (L).
        2. **Rank of # of Territories b/w 99%-101%**: Multiply by 0.2 and consider the range from high (H) to low (L).
        3. **Rank of Standard Deviation (Std Dev)**: Multiply by 0.1 and consider the range from low (L) to high (H).
        4. **Rank of Goal Accuracy**: Multiply by 0.1 and consider the range from high (H) to low (L).
        5. **Rank of Metric vs Att R² value , (divided by the total number of metrics)**: Multiply by 0.3 and consider the range from low (L) to high (H).

        The final weighted rank is a combination of these components, with the last part adjusted by a multiplier that is the reciprocal of 30%.
        """)

    visuals2(1,2)
    if ss.MODE == 2:
        visuals2(2,2)

    st.markdown("<h2 style='text-align: center;'>Fairness Testing and Goals Accuracy</h2>", unsafe_allow_html=True)
    visuals3(1,2)
    if ss.MODE == 2:
        visuals3(2,2)

#MAIN START :
st.markdown("<h1 style='text-align: center;'>Processing Combinations</h1>", unsafe_allow_html=True)
if ss.pro_com == False:
    st.info('Ensure That you Submitted Combinations', icon="⚠️")
c1,c2,c3 = st.columns([5,5,1])
if c2.button("Start Processing"):
    ss.start_filter = True

if ss.start_filter:
    #1. check if combinations are submited & uploaded  AND if results have already been processed or not
    if 'submit_2' in ss and (ss.submit_2 and ss.items_list) and ss.pro_com == False:

        #start processing data-
        ss['objdf1'] = process_data(1)
        if ss.MODE == 2:
            ss['objdf2'] = process_data(2)
            if (~ss['objdf1'].empty) & (~ss['objdf2'].empty):
                ss.pro_com = True
        elif (~ss['objdf1'].empty):
            ss.pro_com = True
        
        #Check if you actually got valid results to show results for 
        if ss.pro_com:
            result_main()

            # Then Ask for Custom Input
            input()

            # Then Filter out top ranking methods and store for graphs
            ss['rankdf1'],ss['rankdf1_terrs'] = process_data_vis(1,2)
            if ss.MODE == 2:
                ss['rankdf2'],ss['rankdf2_terrs'] = process_data_vis(2,2)

            #print graphs-
            visuals_main()

            
    #2. when calculation has already been done -
    elif ('submit_2' in ss) and (ss.submit_2 and ss.items_list) and ss.pro_com:
        #Just Show Results -
        result_main()
        # Then Ask for Custom Input
        input()

        # Then Filter out top ranking methods and store for graphs
        ss['rankdf1'],ss['rankdf1_terrs'] = process_data_vis(1,2)
        if ss.MODE == 2:
            ss['rankdf2'],ss['rankdf2_terrs'] = process_data_vis(2,2)

        #print graphs-
        visuals_main()

# DONE ! :) # WOOO HOOO