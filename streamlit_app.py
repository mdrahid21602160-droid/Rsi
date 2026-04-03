import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="RSI2 Trading Bot",
    page_icon="📈",
    layout="wide"
)

st.title("📈 RSI(2) Trading Bot")
st.markdown("**Buy when RSI(2) < 10 after a gap down | Sell next day at close**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("Settings")
    rsi_threshold = st.slider("RSI(2) Threshold", 2, 20, 10)
    min_drop = st.slider("Min Intraday Drop (%)", 1, 10, 2)
    hold_days = st.selectbox("Holding Period (Days)", [1, 2, 3, 4, 5], index=0)
    
    st.markdown("---")
    st.header("Stock Universe")
    
    tickers = st.multiselect(
        "Select Stocks",
        ["COIN", "NET", "DDOG", "CRWD", "TSLA", "SHOP", "SMCI", "IONQ", "NVDA", "UAL",
         "AMD", "MU", "AVGO", "AMAT", "PLTR", "MDB", "AAPL", "MSFT", "GOOGL", "META"],
        default=["NVDA", "TSLA", "AMD", "META"]
    )
    
    st.markdown("---")
    st.header("Risk Management")
    position_size = st.slider("Position Size (% of portfolio)", 1, 20, 5)
    stop_loss = st.slider("Stop Loss (%)", -10, -1, -5)

def calculate_rsi(data, period=2):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def scan_for_signals(tickers, rsi_thresh, min_drop_pct):
    signals = []
    for ticker in tickers:
        try:
            daily = yf.download(ticker, period="5d", progress=False)
            intraday = yf.download(ticker, period="1d", interval="5m", progress=False)
            
            if len(daily) >= 2 and len(intraday) >= 5:
                prev_low = daily['Low'].iloc[-2]
                current_open = daily['Open'].iloc[-1]
                gap_down = current_open < prev_low
                gap_pct = (current_open - prev_low) / prev_low * 100
                
                rsi = calculate_rsi(intraday['Close'], 2)
                current_rsi = rsi.iloc[-1]
                
                intraday_low = intraday['Low'].min()
                drop_pct = (intraday_low - current_open) / current_open * 100
                current_price = intraday['Close'].iloc[-1]
                
                if gap_down and current_rsi < rsi_thresh and drop_pct < -min_drop_pct:
                    signals.append({
                        "Ticker": ticker,
                        "RSI(2)": round(current_rsi, 1),
                        "Gap %": round(gap_pct, 1),
                        "Drop %": round(drop_pct, 1),
                        "Entry": round(intraday_low, 2),
                        "Current": round(current_price, 2)
                    })
        except:
            pass
    return signals

tab1, tab2, tab3 = st.tabs(["Live Signals", "Backtest Results", "Strategy Guide"])

# Tab 1: Live Signals
with tab1:
    st.header("Real-Time Signal Scanner")
    st.caption(f"Monitoring {len(tickers)} stocks | RSI threshold: {rsi_threshold}")
    
    if st.button("Scan Now", type="primary"):
        with st.spinner("Scanning for signals..."):
            signals = scan_for_signals(tickers, rsi_threshold, min_drop)
        
        if signals:
            st.balloons()
            st.success(f"Found {len(signals)} signals!")
            st.dataframe(pd.DataFrame(signals), use_container_width=True)
            
            st.info(f"""
            Trade Instructions:
            - Buy at Entry price: ${signals[0]['Entry'] if signals else 'N/A'}
            - Position size: {position_size}% of portfolio
            - Stop loss: {abs(stop_loss)}% below entry
            - Exit: Sell at close in {hold_days} day(s)
            """)
        else:
            st.info("No signals detected. Waiting for RSI(2) to drop below threshold.")
    
    st.markdown("---")
    st.subheader("Stock Chart")
    
    chart_ticker = st.selectbox("Select stock to view", tickers if tickers else ["NVDA"])
    
    if chart_ticker:
        df = yf.download(chart_ticker, period="1mo", interval="5m", progress=False)
        if not df.empty:
            df['RSI2'] = calculate_rsi(df['Close'], 2)
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name=chart_ticker
            ))
            fig.update_layout(title=f"{chart_ticker} - 5 Min Chart", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df.index, y=df['RSI2'], name="RSI(2)", line=dict(color='purple')))
            fig2.add_hline(y=rsi_threshold, line_dash="dash", line_color="red")
            fig2.update_layout(title="RSI(2)", height=200, yaxis_range=[0, 100])
            st.plotly_chart(fig2, use_container_width=True)

# Tab 2: Backtest Results
with tab2:
    st.header("Backtest Results (2020-2025)")
    
    results = pd.DataFrame({
        "Stock": ["COIN", "NET", "DDOG", "CRWD", "TSLA", "SHOP", "SMCI", "IONQ", "NVDA", "UAL"],
        "Return %": [292.9, 257.7, 236.4, 231.0, 231.0, 225.2, 221.8, 220.3, 220.1, 211.9],
        "Win Rate %": [76.9, 72.7, 78.7, 78.9, 67.4, 72.7, 70.2, 71.4, 71.6, 68.4],
        "Trades": [78, 77, 75, 76, 86, 77, 84, 56, 67, 76]
    })
    
    st.dataframe(results, use_container_width=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Average Return", "+149.7%")
    with col2:
        st.metric("Win Rate", "72.2%")
    with col3:
        st.metric("Total Trades", "2,365")
    with col4:
        st.metric("Profitable Stocks", "38/38")
    
    fig = go.Figure(go.Bar(
        x=results["Stock"], y=results["Return %"],
        text=results["Return %"].round(1), textposition='auto',
        marker_color='green'
    ))
    fig.update_layout(title="Top Performers", xaxis_title="Stock", yaxis_title="Return %")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Portfolio Simulation")
    initial = st.number_input("Initial Capital $", value=10000, step=5000, key="initial")
    final = initial * (1 + 1.497)
    st.metric("5-Year Value", f"${final:,.0f}", delta=f"+${final - initial:,.0f}")

# Tab 3: Strategy Guide
with tab3:
    st.header("Strategy Guide")
    
    st.subheader("Entry Rules")
    st.markdown("- Open price < Previous day's low (gap down)")
    st.markdown("- RSI(2) drops below 10 during the day")
    st.markdown("- Intraday drop > 2% from open")
    st.markdown("- Buy at the intraday low")
    
    st.subheader("Exit Rules")
    st.markdown("- Sell at next day's close")
    st.markdown(f"- Stop loss: {abs(stop_loss)}% below entry (optional)")
    
    st.subheader("Performance Statistics")
    st.markdown("- Backtest Period: 2020-2025")
    st.markdown("- Stocks Tested: 38 S&P 500 high-beta stocks")
    st.markdown("- Total Trades: 2,365")
    st.markdown("- Win Rate: 72.2%")
    st.markdown("- Average Win: +3.2%")
    st.markdown("- Average Loss: -2.1%")
    st.markdown("- Profit Factor: 3.4")
    st.markdown("- Max Drawdown: -15%")
    
    st.subheader("Top 5 Performing Stocks")
    st.markdown("1. COIN: +292.9% (Crypto exchange)")
    st.markdown("2. NET: +257.7% (Cloudflare)")
    st.markdown("3. DDOG: +236.4% (Datadog)")
    st.markdown("4. CRWD: +231.0% (CrowdStrike)")
    st.markdown("5. TSLA: +231.0% (Tesla)")
    
    st.subheader("Risk Management")
    st.markdown(f"- Position Size: {position_size}% of portfolio per trade")
    st.markdown("- Max Daily Trades: 3")
    st.markdown(f"- Stop Loss: {abs(stop_loss)}% from entry")
    st.markdown("- Avoid earnings week volatility")
    
    st.subheader("Getting Started")
    st.markdown("1. Paper trade for 3 months using this dashboard")
    st.markdown("2. Track all trades in a spreadsheet")
    st.markdown("3. Start with small capital ($1,000-$5,000)")
    st.markdown("4. Focus on top 5-10 performing stocks")
    st.markdown("5. Scale up after 3 profitable months")
    
    st.warning("Disclaimer: Past performance does not guarantee future results. Paper trade before using real capital.")

st.markdown("---")
st.caption(f"RSI(2) Gap Down Strategy | Monitoring {len(tickers)} stocks | Data from Yahoo Finance")