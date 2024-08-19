import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="Live Data Results",
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
if 'cw_inputs' not in ss:
    ss['cw_inputs'] = [0.0 for _ in range(ss['number_of_metrics'])]

if 'gr_metric' not in ss:
    ss['gr_metric'] = ss['list_of_metrics'][0]

if 'min_cap' not in ss:
    ss['min_cap'] = None

if 'max_cap' not in ss:
    ss['max_cap'] = None

if 'vol_adj' not in ss:
    ss['vol_adj'] = None

if 'fnc_process_flag' not in ss:
    ss.fnc_process_flag = False

#   #   #   #   #   #   #   #
# FUNCTION LIBRARY - #
#2. Objective_secondary: To get back weight , expected growth rate , goals
# Also Handles Volume Adjustment - 
def objective_secondary(*metric_weights):
    metric_weights = list(metric_weights)
    method_name = metric_weights[-1]
    metric_weights.pop(-1)
    comp_weights = {}
    #populating comp_weights -
    for weight_name,weight_value in zip(ss['list_of_metrics'],metric_weights):
        comp_weights[weight_name] = weight_value
    
    #populating comp_volumes -
    comp_vols = {}
    for x,y in comp_weights.items():
        comp_vols[x] = nation_goal_value * y

    work_df = data.copy() # This is in RAM for this page.
    computation_cols = ss['list_of_metrics']
    for col in computation_cols:
        work_df[str(col+'_w')] = (work_df[col] / work_df[col].sum()) * comp_vols[col]
    
    work_df[f'Final_Quota'] = sum(work_df[col + '_w'] for col in computation_cols)

    # Volume Adjustment - 
    vol_adj = ss['vol_adj'] or 0
    work_df['Final_Quota'] = (((work_df['Final_Quota'].mean()) - work_df['Final_Quota']) * vol_adj) + work_df['Final_Quota']

    # growth expectation number : 
    work_df[f'gr_ex'] = (work_df[f'Final_Quota'] / work_df[ss['gr_metric']]) - 1#.round(3)  # source from radio
    work_df = work_df[['Territory_Number',ss['gr_metric'],f'Final_Quota',f'gr_ex']]
    return(work_df)

#3. Gets base columns for flooring and capping calcuations - 
def get_fnc_columns(df):
    # create a new column with the adjusted 
    df['flag'] = (df['gr_ex'] > ss['max_cap']) | (df['gr_ex'] < ss['min_cap'])
    excluding_sum = df.loc[df['flag'] == False, 'Final_Quota'].sum()
    df['releif_cap_prc'] = (df['gr_ex'].clip(lower=ss['min_cap'], upper=ss['max_cap'])) + 1
    df['desired_goal_after_capping'] = df[ss['gr_metric']] * df['releif_cap_prc']
    df['excess_goal_after_capping'] = df['Final_Quota'] - df['desired_goal_after_capping']
    df['rlgnct'] = np.where(df['flag'], 0, (df['Final_Quota'] / excluding_sum)) #redistribute left goals to non capped terrs
    df['ganct'] = df['excess_goal_after_capping'].sum() * df['rlgnct']
    df['rag'] = df['desired_goal_after_capping'] + df['ganct']

    return (df)

#4. Does flooring and Capping in a loop - used 'get_fnc_columns' as a base function | Returns detailed dataframe 
def fnc_loop_util(args):
    # Get Base Data
    base1 = objective_secondary(*args) # TIE THIS TO FUNCITON INPUT LATER -
    
    # Get Base Data + Supporting columns for FNC -> FNC Algo Applied (1) here
    base2 = get_fnc_columns(base1)
    # Creating a Copy of Original Growth Expectation for Debugging as algo is likely to run multiple times:
    base2['gr_orig'] = base2['gr_ex']

    # Before Loop Starts Checking for Validity of new goals - 
    base2['gr_ex_test'] = (base2['rag'] / base2[ss['gr_metric']]) -1
    base2['flag_test'] = (base2['gr_ex_test'] > ss['max_cap']) | (base2['gr_ex_test'] < ss['min_cap'])

    #Checking -
    if base2[base2['flag_test']==True].shape[0] == 0:
        return(base2)
    else:
        counter = 1
        while(True):
            if counter >= 30:
                return(base2)
            else:
                base2['gr_ex'] = base2['gr_ex_test'].copy() # copying over the new growth rate expectations from the previous loop.
                base2 = get_fnc_columns(base2)
                base2['gr_ex_test'] = (base2['rag'] / base2[ss['gr_metric']]) -1
                base2['flag_test'] = (base2['gr_ex_test'] > ss['max_cap']) | (base2['gr_ex_test'] < ss['min_cap'])
                if base2[base2['flag_test']==True].shape[0] == 0:
                    return(base2)
                else:
                    counter += 1

#5. Util Function : Assits in Generating Values for all available Methods and concatinating them :
def util_5():
    for i in range(len(test_combs)):
        method_name = test_combs.loc[i]['method_num']
        df = fnc_loop_util(test_combs.loc[i])
        df = df[['Territory_Number','rag','gr_ex_test']]
        df.columns = ['Territory_Number',f'Final_Quota_{method_name}',f'gr_ex_{method_name}']

        if i == 0:
            result_df = df
        else : 
            result_df = pd.merge(result_df,df,on='Territory_Number',how='left')
        
    return(result_df)

#6. To Summarize Result DF - Util Function 
def util_6(df):
    # Drop the 'Territory_Number' column as it's not needed for the calculations
    df_numeric = df.drop('Territory_Number', axis=1)

    # Calculate MIN, MAX, and AVG for each column
    min_row = df_numeric.min().to_frame().T
    max_row = df_numeric.max().to_frame().T
    avg_row = df_numeric.mean().to_frame().T


    # Add the stat labels
    min_row['stat'] = 'MIN'
    max_row['stat'] = 'MAX'
    avg_row['stat'] = 'AVG'



    # Append the calculated rows to the original DataFrame
    df_result = pd.concat([df, max_row, avg_row, min_row], ignore_index=True)
    df_result = df_result[~df_result['stat'].isnull()]
    df_result = df_result[['stat'] + list(df_result.columns[1:-1])]
    return(df_result)


#   #   #   #   #   #   #   #

st.markdown(
    "<h1 style='text-align: center;'>Results</h1>", 
    unsafe_allow_html=True
)

if not ss.test_up:
    st.subheader('Did You upload your Data yet ?')
else:
    ###
    # Reading Data From Uploaded Excel
    data = pd.read_excel(ss['test_file'],sheet_name='Sheet1',converters={'NATION_GOAL':float})
    nation_goal_value = data.iloc[0,-1]
    data.drop(columns=['NATION_GOAL'],inplace=True)
    ###

    ###
    # Custom Input Section -
    custom_weights_input = []
    with st.expander('Custom Input'):
        ci1,ci2 = st.columns(2)
        for i in range(ss['number_of_metrics']):
            ci1.markdown(
                f"<h2 style = 'text-align: center;padding: 22px;'>{str(ss['list_of_metrics'][i])}</h2>",
                unsafe_allow_html=True
            )
            weight  = ci2.number_input(
                label=' ',
                key = f'custom weight for metric{i+1}',
                min_value=0.0,max_value=100.0,step=1.0,
                value = ss['cw_inputs'][i]*100
            )
            custom_weights_input.append(weight/100)
        # pass to session state - 
        ss['cw_inputs'] = custom_weights_input
        # Creating Datframe row :
        custom_row = {key: value for key, value in zip(ss['list_of_metrics'], ss['cw_inputs'])}
        custom_row['method_num'] = 'C1'

        if sum(ss['cw_inputs']) not in [0,1]:
            val = sum(ss['cw_inputs']) * 100
            st.warning(f'Your Weights Dont Add Up to 100% yet!  :  {val}')
    ###
    
    ###
    # fetching ranks from prev page:
    test_combs = ss['rankdf1'][ss['list_of_metrics']]
    if ss.MODE == 2:
        test_combs = pd.concat([test_combs, ss['rankdf2'][ss['list_of_metrics']]], ignore_index=True)
        # deduping out custom row & any repeated combinations-
        test_combs = test_combs.drop_duplicates(subset=ss['list_of_metrics'])
    test_combs.reset_index(inplace=True, drop=True)
    test_combs['method_num'] = 'M' + (test_combs.index + 1).astype(str)
    # Inserting Custom Input :
    if sum(ss['cw_inputs']) == 1:
        test_combs = pd.concat(
            [test_combs,
            pd.DataFrame([custom_row])],ignore_index=True
        )
    st.subheader('Methods to be Tested - ')
    # for styling -
    c_config = {key : st.column_config.NumberColumn(key,format = '%.2f%%') for key in ss['list_of_metrics']}
    c_config['method_num'] = 'Methodology'
    test_combs_style = test_combs.copy()
    for c in ss['list_of_metrics']:
        test_combs_style[c] = test_combs_style[c]*100
    st.dataframe(test_combs_style,use_container_width=True,hide_index=True,column_config=c_config)
    
    st.markdown('---')
    ###

    ###
    # UI AND BUTTON - #
    
    # Growth Rate Formula Picker
    c1,c2,c3,c4,c5 = st.columns(5)
    gr_metric = c1.radio('Pick a  Metric for growth rate calculation - ',ss['list_of_metrics'],horizontal=True,
                         index = ss['list_of_metrics'].index(ss['gr_metric'])
    )

    max_cap = c2.number_input('Enter Cap %')/ 100
    min_cap = c3.number_input('Enter Floor %')/ 100
    vol_adj = c4.number_input('Enter Volume Adjustment %') / 100
    st.markdown('---')

    if (max_cap != ss['max_cap']) | (min_cap != ss['min_cap']) | (vol_adj != ss['min_cap']):
        ss.fnc_process_flag = False

    c5.write('')
    c5.write('')
    if c5.button('PROCESS',use_container_width=True):

        max_cap = None if max_cap == 0.0 else max_cap
        min_cap = None if min_cap == 0.0 else min_cap
        vol_adj = None if vol_adj == 0.0 else vol_adj

        # Push to SS :
        ss['gr_metric'] = gr_metric
        ss['max_cap'] = max_cap
        ss['min_cap'] = min_cap
        ss['vol_adj'] = vol_adj

        ss.fnc_process_flag = True
    
    if ss.fnc_process_flag:
        # Function Call - 
        c6,c7 = st.columns(2)
        result_df = util_5()
        result_summary_df = util_6(result_df)

        # For highlighting outliers - THIS WILL HIGHLIGHT STUFF in NEGATIVE GROWTH RATE
        HL_cols = [f'gr_ex_{i}' for i in test_combs['method_num'].unique()]
        def highlight_sales(val):
            max_cap = ss['max_cap'] or 0
            min_cap = ss['min_cap'] or 0

            if (max_cap + min_cap == 0):
                return ''
            if val > max_cap*100 or val < min_cap*100:
                return 'background-color: yellow'  # Highlight in yellow
            return ''

        c_config2 = {key : st.column_config.NumberColumn(key,format = '%.3f%%') for key in HL_cols}
        c_config2['stat'] = st.column_config.Column(width='medium')
        #For Format Change :
        result_summary_df[HL_cols] = result_summary_df[HL_cols].apply(lambda x: x * 100)
        result_df[HL_cols] = result_df[HL_cols].apply(lambda x: x * 100)
        
        # Apply the highlight to the specified columns in check_condition_list
        #STYL_result_df = result_df.style.applymap(lambda x: highlight_sales(x) if pd.notnull(x) else '', subset=HL_cols)
        STYL_result_df = (result_df.style
                        .applymap(lambda x: highlight_sales(x) if pd.notnull(x) else '', subset=HL_cols)
                        .format({col: '{:.3f}%' for col in HL_cols if pd.api.types.is_numeric_dtype(result_df[col])}))  # Format only numeric columns as percentages



        st.subheader('Territory Level Goals - ')
        st.markdown('---')
        st.dataframe(
            result_summary_df
            ,use_container_width=True,hide_index=True,
            column_config=c_config2
        )
        st.dataframe(
            STYL_result_df,use_container_width=True,hide_index=True,
            column_config={'Territory_Number':st.column_config.Column(width='medium')}
        )
        st.markdown('---')
        # Reducing Table to render graph - 
        graph_df = result_df[
            ['Territory_Number']+[f'gr_ex_{i}' for i in test_combs['method_num'].unique()]
        ]
        graph_df['nat'] = ((nation_goal_value/data[ss['gr_metric']].sum())-1)*100

        ###
        # Graph 1 -#
        gr_cols = [col for col in graph_df.columns if col.startswith('gr_ex')] + ['nat']
        graph_df2 = graph_df[gr_cols].copy()
        for col in graph_df2:
            graph_df2[col] = graph_df2[col].sort_values(ignore_index=True)
        graph_df2 = graph_df2.reset_index(drop=True)
        fig = px.line(graph_df2, x=graph_df2.index, y=gr_cols, title='Sorted Growth Expectation Rate')
        fig.update_layout(
        xaxis_title='',yaxis_title='Growth Expectation',
        xaxis=dict(showticklabels=False)
        )
        c6.plotly_chart(fig, use_container_width=True)
        
        ###
        # Graph 2 Creation -
    
        fig = px.line(
            graph_df, 
            x='Territory_Number', 
            y=graph_df.columns[1:],
            labels={'value': 'Growth Expectation', 'variable': 'Methodology'}
        )
        fig.update_layout(
            title='Growth Expectation | Method Comparisons',
            xaxis_title='',yaxis_title='Growth Expectation',
            xaxis=dict(showticklabels=False)
        )
        c7.plotly_chart(fig,use_container_width=True)
        ###
        # Extra Graphs - 
        c8,c9 = st.columns(2)
        fig = px.box(graph_df, y=[f'gr_ex_{i}' for i in test_combs['method_num'].unique()],
             title="Distribution of Growth Rates by Method")
        fig.update_layout(xaxis_title = 'Methods',yaxis_title = 'Growth Distribution')
        c8.plotly_chart(fig)
        
        fig = px.bar(graph_df, x='Territory_Number', y=[f'gr_ex_{i}' for i in test_combs['method_num'].unique()],
                    barmode='group', title="Comparison of Growth Rates by Territory")
        fig.update_layout(xaxis_title = 'Territory',yaxis_title = 'Growth Rate (%)')
        c9.plotly_chart(fig,use_container_width=True)
        ###
        