import pandas as pd
import plotly.express as px
import streamlit as st

from PIL import Image

staffing_data_q2 = pd.read_csv("healthcare_metrics_analysis/project_resources/daily_nurse_staffing_q2_2024_refined.csv")
staffing_data_q2 = staffing_data_q2[(staffing_data_q2["provider_name"] != "MILLER'S MERRY MANOR") & (staffing_data_q2["provider_name"] != "ST ANNS COMMUNITY")]
provider_data = pd.read_csv("healthcare_metrics_analysis/project_resources/provider_info_oct_2024_refined.csv")
facility_data = pd.read_csv("healthcare_metrics_analysis/project_resources/snf_qrp_provider_data_oct_2024_refined.csv")
state_averages = pd.read_csv("healthcare_metrics_analysis/project_resources/state_us_averages_oct_2024_refined.csv")

st.title("Healthcare Metrics Analysis")
st.write("Healthcare Metrics and Data Analytics Dashboard")

# Staffing Metrics
st.header("Staffing Metrics Overview")

st.subheader("Average Nursing Hours per Patient Day (NHPPD) by State")
state_averages_nhppd = state_averages[state_averages['state_or_nation'] != 'NATION'][['state_or_nation', 'total_nurse_staffing_hrs_per_resident_per_day']]
bar_chart_nhppd = state_averages_nhppd.set_index('state_or_nation').sort_values(by = 'total_nurse_staffing_hrs_per_resident_per_day', ascending = False)
st.bar_chart(
    data = bar_chart_nhppd,
    x_label = "State",
    y_label = "Average Nursing Hours per Patient Day"
)

st.subheader("Total Nursing Hours Worked by State (Q2 2024)")
total_nursing_hours_by_state = staffing_data_q2.groupby('state')['total_nurse_hrs'].sum().reset_index()
bar_chart_total_nursing_hours = total_nursing_hours_by_state.set_index('state').sort_values(by = 'total_nurse_hrs', ascending = False)
st.bar_chart(
    data = bar_chart_total_nursing_hours,
    x_label = "State",
    y_label = "Total Nursing Hours"
)

st.subheader("Total Nursing Hours Worked by Month (Q2 2024)")
total_nursing_hours_by_month = staffing_data_q2.groupby('month')['total_nurse_hrs'].sum().reset_index()
total_nursing_hours_by_month['month'] = pd.to_datetime(total_nursing_hours_by_month['month'], format = '%m').dt.month_name()
months_order = ['April', 'May', 'June'] # Orders months chronologically instead of alphabetically.
total_nursing_hours_by_month['month'] = pd.Categorical(total_nursing_hours_by_month['month'], categories = months_order, ordered = True)
bar_chart_total_nursing_hours_by_month = total_nursing_hours_by_month.set_index('month')
st.bar_chart(
    data = bar_chart_total_nursing_hours_by_month,
    x_label = "Month",
    y_label = "Total Nursing Hours"
)

st.subheader("Top 10 Providers by Nursing Hours (Q2 2024)")
total_nursing_hours_by_facility = staffing_data_q2.groupby('provider_name')['total_nurse_hrs'].sum().reset_index()
top_facilities_nursing_hours = total_nursing_hours_by_facility.sort_values(by = 'total_nurse_hrs', ascending = False).head(10)
bar_chart_top_facilities_nursing_hours = px.bar(
    top_facilities_nursing_hours,
    x = "total_nurse_hrs",
    y = "provider_name",
    barmode = "group",
    orientation = 'h',
    labels = {"total_nurse_hrs": "Total Nursing Hours", "provider_name": "Provider Name"},
    title = "Top 10 Providers by Nursing Hours (Q2 2024)"
)
st.plotly_chart(bar_chart_top_facilities_nursing_hours)

st.subheader("Nursing Hours Trend for Top 10 Providers (Q2 2024)")
top_10_providers_nursing_hours = top_facilities_nursing_hours['provider_name'].to_list()
staffing_hours_trend_top_providers = staffing_data_q2[staffing_data_q2['provider_name'].isin(top_10_providers_nursing_hours)]
staffing_hours_trend_top_providers['date'] = pd.to_datetime(staffing_data_q2[['month', 'day']].assign(year = 2024))
staffing_hours_trend_top_providers = staffing_hours_trend_top_providers.sort_values(by = ['provider_name', 'date'])
line_graph_staffing_hours_trend_top_10 = px.line(
    staffing_hours_trend_top_providers,
    x = 'date',
    y = 'total_nurse_hrs',
    color = 'provider_name',
    labels = {"date": "Date", "total_nurse_hrs": "Total Nursing Hours"},
    title = 'Nursing Hours Trend Top 10 Providers (Q2 2024)'
)
st.plotly_chart(line_graph_staffing_hours_trend_top_10)

st.subheader("Bottom 10 Providers by Nursing Hours (Q2 2024)")
bottom_facilities_nursing_hours = total_nursing_hours_by_facility.sort_values(by = 'total_nurse_hrs', ascending = True).head(10)
bar_chart_bottom_facilities_nursing_hours = px.bar(
    bottom_facilities_nursing_hours,
    x = "total_nurse_hrs",
    y = "provider_name",
    barmode = "group",
    orientation = 'h',
    labels = {"total_nurse_hrs": "Total Nursing Hours", "provider_name": "Provider Name"},
    title = "Bottom 10 Providers by Nursing Hours (Q2 2024)"
)
st.plotly_chart(bar_chart_bottom_facilities_nursing_hours)

st.subheader("Nursing Hours Trend for Bottom 10 Providers (Q2 2024)")
bottom_10_providers_nursing_hours = bottom_facilities_nursing_hours['provider_name'].to_list()
staffing_hours_trend_bottom_providers = staffing_data_q2[staffing_data_q2['provider_name'].isin(bottom_10_providers_nursing_hours)]
staffing_hours_trend_bottom_providers['date'] = pd.to_datetime(staffing_data_q2[['month', 'day']].assign(year = 2024))
staffing_hours_trend_bottom_providers = staffing_hours_trend_bottom_providers.sort_values(by = ['provider_name', 'date'])
line_graph_staffing_hours_trend_bottom_10 = px.line(
    staffing_hours_trend_bottom_providers,
    x = 'date',
    y = 'total_nurse_hrs',
    color = 'provider_name',
    labels = {"date": "Date", "total_nurse_hrs": "Total Nursing Hours"},
    title = 'Nursing Hours Trend Bottom 10 Providers (Q2 2024)'
)
st.plotly_chart(line_graph_staffing_hours_trend_bottom_10)

# Provider Metrics
st.header("Provider Metrics Overview")

st.subheader("Top 10 Providers by Bed Utilization Rate (Q2 2024)")
provider_staffing_df = pd.merge(staffing_data_q2, provider_data, on = ['provider_name'], how = 'left')
provider_staffing_df['bed_utilization_rate'] = provider_staffing_df['mds_census'] / provider_staffing_df['number_of_certified_beds'] * 100
average_bed_utilization_rate = provider_staffing_df.groupby('provider_name')['bed_utilization_rate'].mean().reset_index()
top_providers_bed_utilization_rates = average_bed_utilization_rate.sort_values(by = 'bed_utilization_rate', ascending = False).head(10)
bar_chart_top_providers_bed_utilization = px.bar(
    top_providers_bed_utilization_rates,
    x = "bed_utilization_rate",
    y = "provider_name",
    barmode = "group",
    orientation = 'h',
    labels = {"bed_utilization_rate": "Bed Utilization Rate (%)", "provider_name": "Provider Name"},
    title = "Top 10 Providers by Bed Utilization (Q2 2024)"
)
st.plotly_chart(bar_chart_top_providers_bed_utilization)

st.subheader("Bed Utilization Trend for Top 10 Providers (Q2 2024)")
top_10_providers_bed_utilization_rates = top_providers_bed_utilization_rates['provider_name'].to_list()
bed_utilization_trend_top_providers = provider_staffing_df[provider_staffing_df['provider_name'].isin(top_10_providers_bed_utilization_rates)]
bed_utilization_trend_top_providers['month'] = bed_utilization_trend_top_providers['month_x']
bed_utilization_trend_top_providers['date'] = pd.to_datetime(bed_utilization_trend_top_providers[['month', 'day']].assign(year = 2024))
bed_utilization_trend_top_providers = bed_utilization_trend_top_providers.sort_values(by = ['provider_name', 'date'])
line_graph_bed_utilization_trend_top_10 = px.line(
    bed_utilization_trend_top_providers,
    x = 'date',
    y = 'bed_utilization_rate',
    color = 'provider_name',
    labels = {"date": "Date", "bed_utilization_rate": "Bed Utilization Rate"},
    title = 'Bed Utilization Trend Top 10 Providers (Q2 2024)'
)
st.plotly_chart(line_graph_bed_utilization_trend_top_10)

st.subheader("Patient Count Trend for Top 10 Providers (Q2 2024)")
average_patient_count = provider_staffing_df.groupby('provider_name')['mds_census'].mean().reset_index()
top_providers_patient_count = average_patient_count.sort_values(by = 'mds_census', ascending = False).head(10)
top_10_providers_patient_count = top_providers_patient_count['provider_name'].to_list()
patient_count_trend_top_providers = provider_staffing_df[provider_staffing_df['provider_name'].isin(top_10_providers_patient_count)]
patient_count_trend_top_providers['month'] = patient_count_trend_top_providers['month_x']
patient_count_trend_top_providers['date'] = pd.to_datetime(patient_count_trend_top_providers[['month', 'day']].assign(year = 2024))
patient_count_trend_top_providers = patient_count_trend_top_providers.sort_values(by = ['provider_name', 'date'])
line_graph_bed_utilization_trend_top_10 = px.line(
    patient_count_trend_top_providers,
    x = 'date',
    y = 'mds_census',
    color = 'provider_name',
    labels = {"date": "Date", "mds_census": "Patient Count"},
    title = 'Patient Count Trend Top 10 Providers (Q2 2024)'
)
st.plotly_chart(line_graph_bed_utilization_trend_top_10)

st.subheader("Bottom 10 Providers by Bed Utilization Rate")
bottom_providers_bed_utilization_rates = average_bed_utilization_rate.sort_values(by = 'bed_utilization_rate', ascending = True).head(10)
bar_chart_bottom_providers_bed_utilization = px.bar(
    bottom_providers_bed_utilization_rates,
    x = "bed_utilization_rate",
    y = "provider_name",
    barmode = "group",
    orientation = 'h',
    labels = {"bed_utilization_rate": "Bed Utilization Rate (%)", "provider_name": "Provider Name"},
    title = "Bottom 10 Providers by Bed Utilization (Q2 2024)"
)
st.plotly_chart(bar_chart_bottom_providers_bed_utilization)

st.subheader("Bed Utilization Trend for Bottom 10 Providers (Q2 2024)")
bottom_10_providers_bed_utilization_rates = bottom_providers_bed_utilization_rates['provider_name'].to_list()
bed_utilization_trend_bottom_providers = provider_staffing_df[provider_staffing_df['provider_name'].isin(bottom_10_providers_bed_utilization_rates)]
bed_utilization_trend_bottom_providers['month'] = bed_utilization_trend_bottom_providers['month_x']
bed_utilization_trend_bottom_providers['date'] = pd.to_datetime(bed_utilization_trend_bottom_providers[['month', 'day']].assign(year = 2024))
bed_utilization_trend_bottom_providers = bed_utilization_trend_bottom_providers.sort_values(by = ['provider_name', 'date'])
line_graph_bed_utilization_trend_bottom_10 = px.line(
    bed_utilization_trend_bottom_providers,
    x = 'date',
    y = 'bed_utilization_rate',
    color = 'provider_name',
    labels = {"date": "Date", "bed_utilization_rate": "Bed Utilization Rate"},
    title = 'Bed Utilization Trend Bottom 10 Providers (Q2 2024)'
)
st.plotly_chart(line_graph_bed_utilization_trend_bottom_10)

st.subheader("Patient Count Trend for Bottom 10 Providers (Q2 2024)")
bottom_providers_patient_count = average_patient_count.sort_values(by = 'mds_census', ascending = True).head(10)
bottom_10_providers_patient_count = bottom_providers_patient_count['provider_name'].to_list()
patient_count_trend_bottom_providers = provider_staffing_df[provider_staffing_df['provider_name'].isin(bottom_10_providers_patient_count)]
patient_count_trend_bottom_providers['month'] = patient_count_trend_bottom_providers['month_x']
patient_count_trend_bottom_providers['date'] = pd.to_datetime(patient_count_trend_bottom_providers[['month', 'day']].assign(year = 2024))
patient_count_trend_bottom_providers = patient_count_trend_bottom_providers.sort_values(by = ['provider_name', 'date'])
line_graph_bed_utilization_trend_bottom_10 = px.line(
    patient_count_trend_bottom_providers,
    x = 'date',
    y = 'mds_census',
    color = 'provider_name',
    labels = {"date": "Date", "mds_census": "Patient Count"},
    title = 'Patient Count Trend Bottom 10 Providers (Q2 2024)'
)
st.plotly_chart(line_graph_bed_utilization_trend_bottom_10)

st.subheader("Top 10 Providers by Readmission Rate")
top_providers_readmission_rate = facility_data.sort_values(by = 'score', ascending = False).head(10)
bar_chart_top_providers_readmission_rate = px.bar(
    top_providers_readmission_rate,
    x = 'score',
    y = 'provider_name',
    barmode = 'group',
    orientation = 'h',
    labels = {'score': 'Readmission Rate (%)', 'provider_name': 'Provider Name'},
    title = 'Top 10 Providers by Readmission Rate'
)
st.plotly_chart(bar_chart_top_providers_readmission_rate)
