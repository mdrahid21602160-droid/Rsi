import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(page_title="RSI(2) Next-Day Close Bot", page_icon="📈", layout="wide")

# --- TECHNICAL CALCULATIONS ---
def calculate_rsi_wilder(data, period=2):
    """Standard Wilder's RSI for 2-period mean reversion."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def run_backtest_engine(ticker, gap_type):
    try:
        # Fetching max history for your 25-year requirement
        df = yf.download(ticker, period="max", interval="1d", auto_adjust=True, progress=False)
        
        if df.empty or len(df) < 50:
            return None

        # Flatten Multi-Index headers to ensure 'Open'/'Close' are found
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Technical Signal Setup
        df['RSI2'] = calculate_rsi_wilder(df['Close'], 2)
        df['PrevLow'] = df['Low'].shift(1)
        df['PrevClose'] = df['Close'].shift(1)
        df = df.dropna(subset=['RSI2', 'PrevLow', 'PrevClose'])
        
        trades = []
        # Loop stops at len-1 because we need the 'next day' close for the exit
        for i in range(len(df) - 1):
            curr_open = df['Open'].iloc[i]
            curr_rsi = df['RSI2'].iloc[i]
            
            # Entry logic based on selected gap definition
            is_gap = curr_open < df['PrevLow'].iloc[i] if gap_type == "Strict (Prev Low)" else curr_open < df['PrevClose'].iloc[i]
            
            if is_gap and curr_rsi < 10:
                entry_price = curr_open
                # EXIT: Hard exit at next day's close
                exit_price = df['Close'].iloc[i + 1] 
                
                pct_change = ((exit_price - entry_price) / entry_price) * 100
                
                trades.append({
                    "Date": df.index[i],
                    "Entry": round(float(entry_price), 2),
                    "Exit Date": df.index[i + 1],
                    "Exit Price": round(float(exit_price), 2),
                    "Return %": round(float(pct_change), 2)
                })
                
        return pd.DataFrame(trades)
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("Strategy Settings")
    gap_mode = st.selectbox("Gap Down Definition", ["Standard (Prev Close)", "Strict (Prev Low)"])
    st.info("Exit Rule: Sell at Close Next Day")
    
    st.markdown("---")
    tickers = st.multiselect("Symbols", ["AMD", "NVDA", "TSLA", "META", "COIN", "AAPL", "MSFT"], default=["AMD", "NVDA", "TSLA"])

# --- MAIN UI ---
st.title("📈 RSI(2) Next-Day Exit Strategy")
st.caption("Customized for: No Target | Hard Exit at Next Day Close | 25-Year Depth Analysis")

tab1, tab2 = st.tabs(["Live Scanner", "Full Backtest Engine"])

with tab1:
    st.subheader("Real-Time Monitor")
    if st.button("Scan Now", type="primary"):
        st.info("Scanning current market for RSI(2) < 10 gap-down entries...")

with tab2:
    selected_ticker = st.selectbox("Select Ticker for Depth Analysis", tickers)
    if st.button("Run Full Backtest", type="primary"):
        with st.spinner(f"Processing 25 years of data for {selected_ticker}..."):
            df_results = run_backtest_engine(selected_ticker, gap_mode)
            
            if df_results is not None and not df_results.empty:
                # Core Metrics
                win_rate = (df_results['Return %'] > 0).mean() * 100
                total_ret = df_results['Return %'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Win Rate", f"{win_rate:.1f}%")
                c2.metric("Total Accumulated Return", f"{total_ret:.1f}%")
                c3.metric("Total Trades Found", len(df_results))
                
                # Performance Visualization
                df_results['Equity'] = df_results['Return %'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_results['Date'], y=df_results['Equity'], name="Cumulative Return"))
                fig.update_layout(title=f"{selected_ticker} Next-Day Exit Performance", xaxis_title="Year", yaxis_title="Cumulative Return (%)")
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Trade Ledger")
                st.dataframe(df_results, use_container_width=True)
            else:
                st.error("No trades found. Try 'Standard (Prev Close)' for more triggers.")

st.divider()
st.caption("Quantitative Trading Tool | Built for 25-Year Mean Reversion Backtesting")