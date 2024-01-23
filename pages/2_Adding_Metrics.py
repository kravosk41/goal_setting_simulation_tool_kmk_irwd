import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from decimal import Decimal
import numpy as np

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


if 'gen_rag' not in ss:
    ss.gen_rag = False
if 'metric_df' not in ss:
    ss['metric_df'] = None #you can set this to pd.DataFrame(), but in the change detection only keep - ss['metric_df'].equals(summary_df)

if 'number_of_metrics' not in ss:
    pass
elif 'range_constraints_list' not in ss:
    #ss['range_constraints_list'] = None
    ss['range_constraints_list'] = [[0.0, 0.0, 0.0] for _ in range(ss['number_of_metrics'])]

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


st.markdown("<h1 style='text-align: center;'>Goal Setting Weight Ranges</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: left;'>Please Enter Minimum , Maximum and Increment values for your weights \
            that you would like to test in your exercise</h4>",unsafe_allow_html=True)
st.write("Please Make Sure to pick ranges judicously!")

st.markdown("---")

# If excel is uploaded and submitted
if ss.ex_up and ss.list_of_metrics:

    #SECTION 1 - User Inputs the metric constraints - 

    col1, col2, col3, col4 = st.columns(4,gap='medium')
    col1.subheader("Metric Name")
    col2.subheader("Min")
    col3.subheader("Max")
    col4.subheader("Increment")


    range_constraints_list = []
    
    for i in range(ss['number_of_metrics']):
        col1.markdown(f"<h1 style='text-align: center; padding: 17px;'>{str(ss['list_of_metrics'][i])}</h1>", unsafe_allow_html=True)
        min_value = col2.number_input(label=' ',key = f'Min Value for Metric {i+1}', min_value=0.0, max_value=100.0, step=1.0,value=ss['range_constraints_list'][i][0]*100)
        max_value = col3.number_input(label=' ',key = f'Max Value for Metric {i+1}', min_value=0.0, max_value=100.0, step=1.0,value=ss['range_constraints_list'][i][1]*100)
        increment_value = col4.number_input(label=' ',key = f'Increment {i+1} ', min_value=0.0, max_value=10.0, step=1.0,value=ss['range_constraints_list'][i][2]*100)
        
        # Add the user input to the list of metrics and range constraints
        range_constraints_list.append([min_value/100, max_value/100, increment_value/100])

    st.markdown("---")


    #SECTION 2 - Show the user a summary of what they have entered -

    st.markdown("<h3 style='text-align: center;'>Input Summary Stats - </h3>", unsafe_allow_html=True)
    summary_df = pd.DataFrame(range_constraints_list, columns=['Min', 'Max', 'Increment'])
    summary_df.insert(0, 'Metric Name', ss['list_of_metrics'])

    c1,c2,c3 = st.columns([2,3,2])
    c2.dataframe(summary_df,hide_index=True,width=960)

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
        else:
            #Code To Create Range -
            items_list = []
            for weight,constraints in zip(ss['list_of_metrics'],ss['range_constraints_list']):
                weight_range_var = "{}_range".format(weight)
                rf = abs(Decimal(str(constraints[2])).as_tuple().exponent) #Round Off Value
                
                globals()[weight_range_var] = np.round(
                    np.arange(
                        constraints[0],
                        constraints[1],
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
            
            st.warning('Please note: You must submit your inputs before you start processing results')
            st.write("Number of Possible % Values for each range : ",str(len_list))
            st.write("Total Possible Combinations Pre 100% Sum Constraint : ",f'{comb_counter:,}')
            st.write("**Note For User**: If the total number of combinations is in the billions please make sure your system has enough memory ")
            st.write("_This will cause future  Operations to take significant time!_")
            

            st.markdown("---")

            if st.button("Submit Combinations"):
                ss.submit_2 = True
                ss['items_list'] = items_list
                ss['comb_counter'] = comb_counter
                st.write(f"{comb_counter:,} combinations ready to filter and process !")
                ss.start_filter = False #to prevent auto rerun of submission of new numbers !
                ss.pro_com = False # To make sure process reruns if already run before