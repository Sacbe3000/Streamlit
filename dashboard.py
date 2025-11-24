# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="ROSA Finance", layout="wide", page_icon="money_with_wings")
st.title("ROSA Financial Dashboard")
st.markdown("#### Your money, beautifully understood")

# Load data
csv_path = Path("ROSA_financial_transactions.csv").resolve()
if not csv_path.exists():
    st.error(f"CSV not found at:\n{csv_path}")
    st.stop()

@st.cache_data
def load_data():
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df = df.dropna(subset=['date', 'amount'])

    df['clean_desc'] = df['description'].astype(str).str.lower()
    df['clean_desc'] = df['clean_desc'].str.replace(r'[\W_]+', ' ', regex=True).str.strip()

    categories = {
        'Groceries': ['tesco','sainsbury','aldi','lidl','asda','morrisons','waitrose','food','supermarket'],
        'Transport': ['uber','tfl','train','tube','bus','petrol','fuel','shell','bp'],
        'Salary': ['salary','payroll','income','wage','payment from'],
        'Utilities': ['thames water','british gas','ee','vodafone','sky','virgin','council tax','rent'],
        'Entertainment': ['netflix','spotify','cinema','restaurant','pub','bar','cafe'],
        'Shopping': ['amazon','ebay','boots','primark','online purchase'],
        'Health': ['boots','pharmacy','doctor','hospital','superdrug'],
        'Travel': ['ryanair','easyjet','booking.com','hotel','eurostar'],
    }

    df['Category'] = 'Other'
    for cat, keywords in categories.items():
        pattern = '|'.join(keywords)
        df.loc[df['clean_desc'].str.contains(pattern, case=False, na=False), 'Category'] = cat

    # Signed amount: credits positive, debits negative
    df['signed_amount'] = df.apply(lambda x: -x['amount'] if x['type'] == 'debit' else x['amount'], axis=1)

    return df.sort_values('date').reset_index(drop=True)

df = load_data()
st.success(f"Loaded {len(df):,} transactions")

# ==================== SIDEBAR FILTERS ====================
with st.sidebar:
    st.header("Filters")
    types = st.multiselect("Transaction Type", options=df['type'].unique(), default=['debit', 'credit'])
    date_range = st.date_input(
        "Date Range",
        value=(df['date'].min().date(), df['date'].max().date()),
        min_value=df['date'].min().date(),
        max_value=df['date'].max().date()
    )

# ==================== APPLY FILTERS ====================
filtered = df[
    df['type'].isin(types) &
    (df['date'].dt.date >= date_range[0]) &
    (df['date'].dt.date <= date_range[1])
].copy()

# CRITICAL: Sort by date and recalculate cumulative net worth on filtered data only
filtered = filtered.sort_values('date').reset_index(drop=True)
filtered['cumulative'] = filtered['signed_amount'].cumsum()

# Optional: Make net worth start at zero (cleaner visual)
if len(filtered) > 0:
    filtered['cumulative'] = filtered['cumulative'] - filtered['cumulative'].iloc[0]

# ==================== METRICS ====================
income = filtered[filtered['type'] == 'credit']['amount'].sum()
expense = filtered[filtered['type'] == 'debit']['amount'].sum()
net = income - expense

col1, col2, col3, col4 = st.columns(4)
col1.metric("Income", f"${income:,.0f}")
col2.metric("Expenses", f"${expense:,.0f}")
col3.metric("Net Flow", f"${net:,.0f}", delta=f"{net:+,.0f}")
col4.metric("Transactions", f"{len(filtered):,}")

# ==================== TABS ====================
tab1, tab2, tab3 = st.tabs(["Overview", "Categories", "All Transactions"])

# ==================== OVERVIEW TAB (Beautiful as before!) ====================
with tab1:
    a1, a2 = st.columns(2)

    with a1:
        st.subheader("Net Worth over Time")
        fig_nw = go.Figure()
        fig_nw.add_trace(go.Scatter(
            x=filtered['date'],
            y=filtered['cumulative'],
            line=dict(color="#4ecdc4", width=4),
            fill='tozeroy',
            fillcolor="rgba(78, 205, 196, 0.3)",
            mode='lines',
            name="Net Worth"
        ))
        fig_nw.update_layout(
            height=400,
            margin=dict(t=40, l=10, r=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', title=None),
            hovermode="x unified"
        )
        st.plotly_chart(fig_nw, use_container_width=True)

    with a2:
        st.subheader("Monthly Cash Flow")
        monthly = filtered.set_index('date').resample('MS')['signed_amount'].sum().reset_index()
        fig_monthly = go.Figure(go.Bar(
            x=monthly['date'],
            y=monthly['signed_amount'],
            marker_color=monthly['signed_amount'].apply(lambda x: '#4ecdc4' if x >= 0 else '#ff6b6b'),
            text=monthly['signed_amount'].apply(lambda x: f"${x:,.0f}"),
            textposition="outside"
        ))
        fig_monthly.update_layout(
            height=400,
            margin=dict(t=40, l=10, r=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_tickangle=45,
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            hovermode="x"
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    b1, b2 = st.columns(2)

    with b1:
        st.subheader("By Transaction Type")
        pie_data = filtered['type'].value_counts().reset_index()
        pie_data.columns = ['type', 'count']
        pie_data['type'] = pie_data['type'].str.capitalize()

        fig_pie = px.pie(
            pie_data,
            names='type',
            color='type',
            color_discrete_map={'Credit': '#4ecdc4', 'Debit': '#ff6b6b'},
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            height=400,
            margin=dict(t=40, l=0, r=0, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with b2:
        st.subheader("Daily Cash Flow")
        daily = filtered.groupby('date')['signed_amount'].sum().reset_index()
        fig_wave = go.Figure(go.Scatter(
            x=daily['date'],
            y=daily['signed_amount'],
            fill='tozeroy',
            mode='lines',
            line=dict(color="#4ecdc4", width=2),
            fillcolor="rgba(78, 205, 196, 0.25)"
        ))
        fig_wave.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=1)
        fig_wave.update_layout(
            height=400,
            margin=dict(t=40, l=10, r=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, title=None),
            hovermode="x unified"
        )
        st.plotly_chart(fig_wave, use_container_width=True)

# ==================== CATEGORIES TAB ====================
with tab2:
    st.subheader("Spending Breakdown (Debits Only)")
    spending = filtered[filtered['type'] == 'debit'].groupby('Category')['amount'].sum().sort_values(ascending=True)
    if not spending.empty:
        fig_expense = px.bar(
            spending,
            x='amount',
            y=spending.index,
            orientation='h',
            color='amount',
            color_continuous_scale="Reds",
            text=spending.values
        )
        fig_expense.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_expense.update_layout(height=600, showlegend=False, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig_expense, use_container_width=True)
    else:
        st.info("No debit transactions in selected range.")

    st.subheader("Income Sources (Credits Only)")
    income_cat = filtered[filtered['type'] == 'credit'].groupby('Category')['amount'].sum().sort_values(ascending=True)
    if not income_cat.empty:
        fig_income = px.bar(
            income_cat,
            x='amount',
            y=income_cat.index,
            orientation='h',
            color='amount',
            color_continuous_scale="Greens",
            text=income_cat.values
        )
        fig_income.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_income.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_income, use_container_width=True)
    else:
        st.info("No credit transactions in selected range.")

# ==================== ALL TRANSACTIONS TAB ====================
with tab3:
    display_df = filtered[['date', 'amount', 'type', 'Category', 'description']].copy()
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
    display_df['type'] = display_df['type'].str.capitalize()
    display_df = display_df.sort_values('date', ascending=False)
    st.dataframe(display_df, use_container_width=True, height=700)

# Final touch
st.balloons()