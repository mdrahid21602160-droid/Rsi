import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(page_title="RSI(2) Quant Engine", page_icon="📈", layout="wide")

# --- TECHNICAL CALCULATIONS ---
def calculate_rsi_wilder(data, period=2):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def run_backtest_engine(ticker, target_pct, gap_type):
    try:
        # Fetch max history for 25-year goal
        df = yf.download(ticker, period="max", interval="1d", auto_adjust=True, progress=False)
        
        if df.empty or len(df) < 50:
            return None

        # Fix for Multi-Index headers in newer yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Signal Logic
        df['RSI2'] = calculate_rsi_wilder(df['Close'], 2)
        df['PrevLow'] = df['Low'].shift(1)
        df['PrevClose'] = df['Close'].shift(1)
        df = df.dropna(subset=['RSI2', 'PrevLow', 'PrevClose'])
        
        trades = []
        for i in range(len(df)):
            curr_open = df['Open'].iloc[i]
            curr_rsi = df['RSI2'].iloc[i]
            
            # Entry Logic: Toggle between Strict Gap and Standard Gap
            is_gap = curr_open < df['PrevLow'].iloc[i] if gap_type == "Strict (Prev Low)" else curr_open < df['PrevClose'].iloc[i]
            
            if is_gap and curr_rsi < 10:
                entry_price = curr_open
                target_price = entry_price * (1 + (target_pct / 100))
                
                # Exit Logic: 0.5% Target or Hard Exit at Close
                if df['High'].iloc[i] >= target_price:
                    exit_price = target_price
                    pct_change = target_pct
                else:
                    exit_price = df['Close'].iloc[i] # Hard Exit at Close
                    pct_change = ((exit_price - entry_price) / entry_price) * 100
                
                trades.append({
                    "Date": df.index[i],
                    "Entry": round(float(entry_price), 2),
                    "Exit": round(float(exit_price), 2),
                    "Return %": round(float(pct_change), 2)
                })
                
        return pd.DataFrame(trades)
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("Strategy Settings")
    profit_target = st.number_input("Profit Target (%)", value=0.5, step=0.1) #
    gap_mode = st.selectbox("Gap Down Definition", ["Strict (Prev Low)", "Standard (Prev Close)"])
    
    st.markdown("---")
    tickers = st.multiselect("Symbols", ["AMD", "NVDA", "TSLA", "META", "COIN", "AAPL"], default=["AMD", "NVDA"])

# --- MAIN UI ---
st.title("📈 RSI(2) Gap Strategy")
tab1, tab2 = st.tabs(["Live Scanner", "25-Year Backtest"])

with tab1:
    if st.button("Scan Now"):
        # Live scanning logic...
        st.write("Scanning current market for signals...")

with tab2:
    selected_ticker = st.selectbox("Select Ticker", tickers)
    if st.button("Run Full Backtest"):
        with st.spinner("Analyzing decades of data..."):
            df_results = run_backtest_engine(selected_ticker, profit_target, gap_mode)
            
            if df_results is not None and not df_results.empty:
                # Performance Metrics
                win_rate = (df_results['Return %'] > 0).mean() * 100
                total_ret = df_results['Return %'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Win Rate", f"{win_rate:.1f}%")
                c2.metric("Total Return", f"{total_ret:.1f}%")
                c3.metric("Trades", len(df_results))
                
                # Performance Chart
                df_results['Equity'] = df_results['Return %'].cumsum()
                st.line_chart(df_results.set_index('Date')['Equity'])
                st.dataframe(df_results, use_container_width=True)
            else:
                st.error("No trades found. Try switching 'Gap Down Definition' to 'Standard'.")