import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import plotly.express as px

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
#   #   #   #   #   #   #   #

#1. Objective : To get back metrics for a combination of weights
def objective(*metric_weights):
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
    
    work_df[f'Final_Quota_{method_name}'] = sum(work_df[col + '_w'] for col in computation_cols)
    # growth expectation number : 
    work_df[f'gr_ex_{method_name}'] = work_df[f'Final_Quota_{method_name}'] / work_df[ss['gr_metric']] # source from radio
    work_df = work_df[['Territory_Number',f'gr_ex_{method_name}',f'Final_Quota_{method_name}']]
    
    return(work_df)

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
    st.dataframe(test_combs,use_container_width=True,hide_index=True,column_config={'method_num':'Methodology'})
    ###

    ###
    # Growth Rate Formula Picker
    c1,c2,c3 = st.columns([1,1,1])
    gr_metric = c2.radio('Pick a  Metric for growth rate calculation - ',ss['list_of_metrics'],horizontal=True,
                         index = ss['list_of_metrics'].index(ss['gr_metric'])
    )
    # Push to session state :
    ss['gr_metric'] = gr_metric

    ###

    ###
    # Function Call - 
    result_df = pd.DataFrame()
    for i in range(len(test_combs)):
        df = objective(*test_combs.loc[i])

        if i == 0:
            result_df = df
        else : 
            result_df = pd.merge(result_df,df,on='Territory_Number',how='left')
    # Reducing Table to render graph - 
    graph_df = result_df[
        ['Territory_Number']+[f'gr_ex_{i}' for i in test_combs['method_num'].unique()]
    ]
    st.subheader('Territory Level Goals - ')
    st.dataframe(result_df,use_container_width=True,hide_index=True)
    ###

    #### Graph 2 ####
    st.markdown('---')
    gr_cols = [col for col in graph_df.columns if col.startswith('gr_ex')]
    graph_df2 = graph_df[gr_cols].copy()
    for col in graph_df2:
        graph_df2[col] = graph_df2[col].sort_values(ignore_index=True)
    graph_df2 = graph_df2.reset_index(drop=True)
    fig = px.line(graph_df2, x=graph_df2.index, y=gr_cols, title='Sorted Growth Expectation Rate Growth Expectation Ratest')
    fig.update_layout(
    xaxis_title='',yaxis_title='Growth Expectation',
    xaxis=dict(showticklabels=False)
    )
    st.plotly_chart(fig, use_container_width=True)
    ###

    ###
    # Graph 1 Creation -
    st.markdown('---')
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
    st.plotly_chart(fig,use_container_width=True)
    st.markdown('---')
    ###














