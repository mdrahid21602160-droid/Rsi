import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
st.set_page_config(page_title="RSI(2) Strategy Bot", page_icon="⚡", layout="wide")

st.title("⚡ RSI(2) Mean Reversion Bot")
st.markdown("### Strategy: Gap Down + RSI(2) Extreme Oversold")
st.info("Logic: Buy on intraday weakness. Exit at 0.5% profit target or Hard Exit at Close.")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("Strategy Parameters")
    rsi_threshold = st.slider("RSI(2) Threshold", 2, 15, 10)
    # Updated to match your preferred profit target
    profit_target_pct = st.number_input("Profit Target (%)", value=0.5, step=0.1) 
    
    st.markdown("---")
    st.header("Universe Selection")
    tickers = st.multiselect(
        "Active Symbols",
        ["NVDA", "TSLA", "AMD", "META", "COIN", "NET", "DDOG", "CRWD", "SHOP", "SMCI"],
        default=["NVDA", "TSLA", "AMD"]
    )
    
    st.markdown("---")
    st.caption("Customized for: Hard Exit at Close & % Profit Targets")

# --- TECHNICAL CALCULATIONS ---
def calculate_rsi_wilder(data, period=2):
    """Uses Wilder's Smoothing for more accurate RSI(2) signals."""
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_signals(ticker_list, rsi_limit, target_pct):
    signals = []
    for ticker in ticker_list:
        try:
            # Fetch daily for gap context and intraday for entry
            df_daily = yf.download(ticker, period="2d", progress=False)
            df_5m = yf.download(ticker, period="1d", interval="5m", progress=False)
            
            if len(df_daily) < 2 or df_5m.empty: continue
            
            prev_low = df_daily['Low'].iloc[-2]
            current_open = df_daily['Open'].iloc[-1]
            
            # 1. Gap Down Check
            is_gap = current_open < prev_low
            
            # 2. RSI(2) Check
            rsi_series = calculate_rsi_wilder(df_5m['Close'], 2)
            current_rsi = rsi_series.iloc[-1]
            
            if is_gap and current_rsi <= rsi_limit:
                entry_price = df_5m['Low'].iloc[-1]
                target_price = entry_price * (1 + (target_pct / 100))
                
                signals.append({
                    "Ticker": ticker,
                    "RSI(2)": round(current_rsi, 2),
                    "Entry Price": round(entry_price, 2),
                    "Target (0.5%)": round(target_price, 2), # Applied % target
                    "Action": "BUY"
                })
        except Exception:
            continue
    return signals

# --- TABS ---
tab1, tab2 = st.tabs(["Scanner", "Execution Logic"])

with tab1:
    if st.button("Run Live Scan", type="primary"):
        with st.spinner("Analyzing market data..."):
            found_signals = get_signals(tickers, rsi_threshold, profit_target_pct)
            
            if found_signals:
                st.success(f"Found {len(found_signals)} setups!")
                st.table(pd.DataFrame(found_signals))
            else:
                st.warning("No stocks currently meet the Gap + RSI(2) criteria.")

with tab2:
    st.subheader("Current Rule Set")
    # Integrating your specific operational constraints
    st.write(f"1. **Entry**: Gap down from yesterday's low and RSI(2) < {rsi_threshold}.")
    st.write(f"2. **Profit Taking**: Limit order set at +{profit_target_pct}% from entry.")
    st.write("3. **Hard Exit**: All positions must be flattened at the closing bell.")
    st.write("4. **Backtest Note**: Strategy assumes 25 years of data consistency.")

st.markdown("---")
st.caption("Built for Quant Trading | Focused on Mean Reversion")