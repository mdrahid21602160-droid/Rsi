import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(page_title="RSI(2) Custom Bot", page_icon="📈", layout="wide")

# --- TECHNICAL CALCULATIONS ---
def calculate_rsi_wilder(data, period=2):
    """Standard Wilder's Smoothing for RSI(2)."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def run_backtest_engine(ticker, rsi_limit, gap_type):
    try:
        # Fetching max history for 25-year analysis
        df = yf.download(ticker, period="max", interval="1d", auto_adjust=True, progress=False)
        
        if df.empty or len(df) < 50:
            return None

        # Flatten headers for compatibility
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # TECHNICAL SETUP: RSI(2) calculated on the LOW price
        df['RSI2_Low'] = calculate_rsi_wilder(df['Low'], 2)
        df['PrevLow'] = df['Low'].shift(1)
        df['PrevClose'] = df['Close'].shift(1)
        df = df.dropna(subset=['RSI2_Low', 'PrevLow', 'PrevClose'])
        
        trades = []
        for i in range(len(df) - 1):
            curr_open = df['Open'].iloc[i]
            curr_close = df['Close'].iloc[i]
            curr_rsi_low = df['RSI2_Low'].iloc[i]
            
            # Entry logic: Gap Down + Adjustable RSI(2) Low Threshold
            is_gap = curr_open < df['PrevLow'].iloc[i] if gap_type == "Strict (Prev Low)" else curr_open < df['PrevClose'].iloc[i]
            
            if is_gap and curr_rsi_low < rsi_limit:
                entry_price = curr_open
                
                # EXIT RULE 1: Sell at close of CURRENT candle if in profit
                if curr_close > entry_price:
                    exit_price = curr_close
                    exit_date = df.index[i]
                else:
                    # EXIT RULE 2: Hard exit at close of NEXT candle
                    exit_price = df['Close'].iloc[i + 1]
                    exit_date = df.index[i + 1]
                
                pct_change = ((exit_price - entry_price) / entry_price) * 100
                
                trades.append({
                    "Date": df.index[i],
                    "Entry": round(float(entry_price), 2),
                    "RSI(2) Low": round(float(curr_rsi_low), 2),
                    "Exit Date": exit_date,
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
    # Dynamic RSI Adjustment
    rsi_input = st.slider("RSI(2) Low Threshold", min_value=2, max_value=15, value=10)
    gap_mode = st.selectbox("Gap Down Definition", ["Standard (Prev Close)", "Strict (Prev Low)"])
    
    st.info(f"Entry: Gap Down + RSI(2) Low < {rsi_input}")
    st.info("Exit: Close Today (if profit) or Close Tomorrow (Hard Exit)")
    
    st.markdown("---")
    tickers = st.multiselect("Symbols", ["AMD", "NVDA", "TSLA", "META", "COIN", "AAPL", "MSFT", "SMCI"], default=["AMD", "NVDA", "TSLA"])

# --- MAIN UI ---
st.title("📈 RSI(2) Custom Strategy Bot")
st.caption(f"25-Year Depth Analysis | RSI(2) Low < {rsi_input} | Time-Based Hard Exit")

tab1, tab2 = st.tabs(["Live Scanner", "Full Backtest Engine"])

with tab1:
    st.subheader("Live Monitor")
    if st.button("Scan Now", type="primary"):
        st.info(f"Scanning for gap-downs where RSI(2) of Low is currently below {rsi_input}...")

with tab2:
    selected_ticker = st.selectbox("Select Ticker for Analysis", tickers)
    if st.button("Run Full Backtest", type="primary"):
        with st.spinner(f"Analyzing historical performance for {selected_ticker}..."):
            df_results = run_backtest_engine(selected_ticker, rsi_input, gap_mode)
            
            if df_results is not None and not df_results.empty:
                win_rate = (df_results['Return %'] > 0).mean() * 100
                total_ret = df_results['Return %'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Win Rate", f"{win_rate:.1f}%")
                c2.metric("Total Return", f"{total_ret:.1f}%")
                c3.metric("Trades Found", len(df_results))
                
                df_results['Equity'] = df_results['Return %'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_results['Date'], y=df_results['Equity'], name="Cumulative Return"))
                fig.update_layout(title=f"{selected_ticker} Performance (RSI < {rsi_input})", xaxis_title="Year", yaxis_title="Return (%)")
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Trade Ledger")
                st.dataframe(df_results, use_container_width=True)
            else:
                st.error(f"No trades found with RSI < {rsi_input}. Try a higher threshold.")

st.divider()
st.caption("Quantitative Trading Tool | Built for High-Beta Mean Reversion Analysis")