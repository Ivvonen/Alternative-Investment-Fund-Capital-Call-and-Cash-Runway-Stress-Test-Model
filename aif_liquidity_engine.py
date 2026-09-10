import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

class AIFLiquidityEngine:
    def __init__(self, total_committed_capital, current_cash, credit_line_max, quarterly_expenses):
        self.total_commit = total_committed_capital
        self.cash = current_cash
        self.credit_max = credit_line_max
        self.expenses = quarterly_expenses
        self.unfunded_capital = total_committed_capital - current_cash
        
    def simulate_funding_runway(self, capital_call_amount, lp_default_rate=0.20, quarters_to_simulate=4):
        current_cash_pool = self.cash
        available_credit = self.credit_max
        unfunded_pool = self.unfunded_capital
        
        simulation_log = []
        breached = False
        breach_quarter = None
        
        for q in range(1, quarters_to_simulate + 1):
            requested_cash = min(capital_call_amount, unfunded_pool)
            actual_cash_received = requested_cash * (1 - lp_default_rate)
            unfunded_pool -= requested_cash
            
            current_cash_pool += actual_cash_received
            current_cash_pool -= self.expenses
            
            if current_cash_pool < 0:
                deficit = abs(current_cash_pool)
                if available_credit >= deficit:
                    available_credit -= deficit
                    current_cash_pool = 0.0
                else:
                    current_cash_pool = 0.0
                    available_credit = 0.0
                    breached = True
                    if breach_quarter is None:
                        breach_quarter = q
            
            total_liquidity_left = current_cash_pool + available_credit
            
            simulation_log.append({
                "Quarter": f"Q{q}",
                "Capital Called": requested_cash,
                "Cash Received": actual_cash_received,
                "Cash Cushion": current_cash_pool,
                "Available Credit": available_credit,
                "Total Liquidity": total_liquidity_left,
                "Status": "BREACHED" if total_liquidity_left <= 0 else "SAFE"
            })
            
        return pd.DataFrame(simulation_log), breached, breach_quarter

# --- STREAMLIT FRONT-END ---
st.set_page_config(page_title="AIFMD Liquidity Engine", layout="wide")
st.subheader("Alternative Investment Fund (AIF) Capital Call and Cash Runway Stress Test Model")
st.markdown("Assess structural funding liquidity risks for illiquid Alternative Investment Funds (PE/Private Debt) under CSSF Circular 18/698 directives.")

# Sidebar Parameters
st.sidebar.header("Fund Structural Inputs")
total_aum = st.sidebar.number_input("Total Committed Capital (€)", value=100000000, step=10000000)
cash_init = st.sidebar.number_input("Initial Cash Position (€)", value=10000000, step=1000000)
credit_facility = st.sidebar.number_input("Subscription Credit Line Max (€)", value=20000000, step=1000000)
fixed_expenses = st.sidebar.number_input("Quarterly Operational/Deal Expenses (€)", value=12000000, step=500000)

st.sidebar.header("Macro Shock Scenario")
call_per_quarter = st.sidebar.slider("Planned Capital Call per Quarter (€)", 5000000, 30000000, 15000000, step=1000000)
default_rate_slider = st.sidebar.slider("Limited Partner (LP) Default Rate (%)", 0, 60, 25) / 100

# Execute Engine Calculation
engine = AIFLiquidityEngine(total_aum, cash_init, credit_facility, fixed_expenses)
df_results, is_breached, q_breach = engine.simulate_funding_runway(call_per_quarter, default_rate_slider)

# Display KPI Analytics Cards
col1, col2, col3 = st.columns(3)
col1.metric("Unfunded LP Capital Pool", f"€{engine.unfunded_capital:,.2f}")
col2.metric("Total Stressed Capital Loss", f"€{df_results['Capital Called'].sum() * default_rate_slider:,.2f}")

if is_breached:
    col3.error(f"Technical Default Status: BREACHED in {df_results.loc[df_results['Status']=='BREACHED', 'Quarter'].iloc[0]}")
else:
    col3.success("Technical Default Status: COMPLIANT (Liquidity Intact)")

st.markdown("---")
chart_col, data_col = st.columns([2, 1])

with chart_col:
    st.subheader("Liquidity Runway & Credit Exhaustion Timeline")
    fig = go.Figure()
    
    # Layer liquidity components visually
    fig.add_trace(go.Bar(x=df_results['Quarter'], y=df_results['Cash Cushion'], name='Cash Cushion', marker_color='#2ca02c'))
    fig.add_trace(go.Bar(x=df_results['Quarter'], y=df_results['Available Credit'], name='Available Subscription Credit', marker_color='#1f77b4'))
    fig.add_trace(go.Scatter(x=df_results['Quarter'], y=df_results['Total Liquidity'], name='Total Available Liquidity', line=dict(color='red', width=3, dash='dash')))
    
    fig.update_layout(barmode='stack', xaxis_title="Projection Horizon", yaxis_title="Available Funds (€)", margin=dict(l=20, r=20, t=20, b=20), height=380)
    st.plotly_chart(fig, use_container_width=True)

with data_col:
    st.subheader("Regulatory Run Log")
    st.markdown("Quarter-by-quarter breakdown of capital calls and liquidity retention:")
    
    for index, row in df_results.iterrows():
        status_color = "🔴" if row['Status'] == "BREACHED" else "🟢"
        st.write(f"**{row['Quarter']} Run Details:**")
        st.write(f"- Received: `€{row['Cash Received']:,.0f}` | Total Liquidity Left: `€{row['Total Liquidity']:,.0f}` {status_color}")
        st.markdown("---")
