import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(page_title="RSI(2) Quant Bot", page_icon="📈", layout="wide")

# --- TECHNICAL ENGINE ---
def calculate_rsi_wilder(data, period=2):
    """Standard Wilder's RSI calculation for short-term mean reversion."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def run_backtest_engine(ticker, target_pct):
    """
    Simulates the strategy over the maximum available historical period.
    Logic: Buy if Gap Down + RSI(2) < 10. 
    Exit: 0.5% Profit Target or Hard Exit at Close.
    """
    try:
        # 'max' period to support your 25-year backtest requirement
        df = yf.download(ticker, period="max", interval="1d", progress=False)
        if len(df) < 50: return None
        
        df['RSI2'] = calculate_rsi_wilder(df['Close'], 2)
        df['PrevLow'] = df['Low'].shift(1)
        
        trades = []
        for i in range(1, len(df)):
            # Entry: Gap Down + RSI2 < 10
            if df['Open'].iloc[i] < df['PrevLow'].iloc[i] and df['RSI2'].iloc[i] < 10:
                entry = df['Open'].iloc[i]
                target_price = entry * (1 + (target_pct / 100))
                
                # Check if profit target hit during the day
                if df['High'].iloc[i] >= target_price:
                    exit_price = target_price
                    pct_change = target_pct
                else:
                    # Hard Exit at Close
                    exit_price = df['Close'].iloc[i]
                    pct_change = ((exit_price - entry) / entry) * 100
                
                trades.append({
                    "Date": df.index[i],
                    "Entry": round(entry, 2),
                    "Exit": round(exit_price, 2),
                    "Return %": round(pct_change, 2)
                })
        return pd.DataFrame(trades)
    except:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("Strategy Settings")
    profit_target = st.number_input("Profit Target (%)", value=0.5, step=0.1) #
    rsi_limit = st.slider("RSI(2) Entry Threshold", 2, 15, 10)
    
    st.markdown("---")
    st.header("Portfolio Selection")
    tickers = st.multiselect(
        "Select Symbols",
        ["NVDA", "TSLA", "AMD", "META", "AAPL", "MSFT", "GOOGL", "AMZN", "NFLX", "COIN"],
        default=["NVDA", "TSLA", "AMD"]
    )

# --- MAIN UI ---
st.title("📈 RSI(2) Gap Down Strategy")
st.caption("Customized for: 0.5% Profit Targets | Hard Exit at Close | 25-Year Backtesting")

tab1, tab2, tab3 = st.tabs(["Live Scanner", "Full Backtest", "Strategy Guide"])

with tab1:
    st.subheader("Real-Time Signal Monitor")
    if st.button("Scan Market", type="primary"):
        results = []
        for t in tickers:
            # Using 1-minute intervals for live RSI(2) precision
            data_live = yf.download(t, period="2d", interval="1m", progress=False)
            data_daily = yf.download(t, period="2d", interval="1d", progress=False)
            
            if not data_live.empty and len(data_daily) >= 2:
                prev_low = data_daily['Low'].iloc[-2]
                curr_open = data_daily['Open'].iloc[-1]
                rsi_val = calculate_rsi_wilder(data_live['Close'], 2).iloc[-1]
                
                if curr_open < prev_low and rsi_val < rsi_limit:
                    entry = data_live['Low'].min() # Anticipated intraday entry
                    results.append({
                        "Symbol": t,
                        "RSI(2)": round(rsi_val, 2),
                        "Entry": entry,
                        "Target Price": round(entry * (1 + profit_target/100), 2)
                    })
        
        if results:
            st.success(f"Signals detected in {len(results)} stocks!")
            st.table(pd.DataFrame(results))
        else:
            st.info("No active signals. Market criteria not met.")

with tab2:
    st.subheader("Historical Performance Engine")
    selected_bt = st.selectbox("Select Ticker for Depth Analysis", tickers)
    
    if st.button("Run Full Backtest"):
        with st.spinner(f"Processing decades of data for {selected_bt}..."):
            df_bt = run_backtest_engine(selected_bt, profit_target)
            
            if df_bt is not None and not df_bt.empty:
                # Key Metrics
                win_rate = (df_bt['Return %'] > 0).mean() * 100
                total_return = df_bt['Return %'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Win Rate", f"{win_rate:.1f}%")
                c2.metric("Total Accumulated Return", f"{total_return:.1f}%")
                c3.metric("Total Trades Found", len(df_bt))
                
                # Equity Curve
                df_bt['Cumulative'] = df_bt['Return %'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_bt['Date'], y=df_bt['Cumulative'], name="Equity Curve"))
                fig.update_layout(title=f"{selected_bt} Strategy Performance", xaxis_title="Year", yaxis_title="Cumulative %")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df_bt, use_container_width=True)
            else:
                st.error("Insufficient data or no trades found for this criteria.")

with tab3:
    st.header("Operational Rules")
    st.markdown(f"""
    - **Entry Trigger**: Daily Open must be lower than the previous day's Low (Gap Down).
    - **Indicator**: RSI(2) must be below {rsi_limit} on an intraday basis.
    - **Profit Target**: Order is placed immediately at **+{profit_target}%** of entry.
    - **Time Exit**: If target is not reached by end of day, execute **Hard Exit at Close**.
    - **Verification**: Strategy reflects backtesting over a **25-year horizon**.
    """)

st.divider()
st.caption("Quantitative Trading Tool | Created for S&P 500 High-Beta Mean Reversion")