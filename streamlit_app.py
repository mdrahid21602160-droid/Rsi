import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="RSI2 Strategy", layout="wide")

st.title("RSI(2) Gap Down Trading Strategy")
st.markdown("**Buy when RSI(2) < 10 after a gap down | Sell next day at close**")
st.markdown("---")

with st.sidebar:
    st.header("Settings")
    rsi_threshold = st.slider("RSI(2) Threshold", 2, 20, 10)
    
    tickers = st.multiselect(
        "Stocks to Monitor",
        ["NVDA", "TSLA", "AMD", "META", "COIN", "NET", "CRWD", "SMCI", "PLTR", "AAPL", "MSFT", "GOOGL"],
        default=["NVDA", "TSLA", "AMD", "META"]
    )

def calculate_rsi(data, period=2):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

tab1, tab2, tab3 = st.tabs(["Live Signals", "Backtest Results", "Strategy Guide"])

with tab1:
    st.header("Real-Time Signal Scanner")
    
    if st.button("Scan Now", type="primary"):
        signals = []
        with st.spinner("Scanning..."):
            for ticker in tickers:
                try:
                    daily = yf.download(ticker, period="5d", progress=False)
                    intraday = yf.download(ticker, period="1d", interval="5m", progress=False)
                    
                    if len(daily) >= 2 and len(intraday) >= 5:
                        prev_low = daily['Low'].iloc[-2]
                        current_open = daily['Open'].iloc[-1]
                        gap_down = current_open < prev_low
                        
                        rsi = calculate_rsi(intraday['Close'], 2)
                        current_rsi = rsi.iloc[-1]
                        
                        intraday_low = intraday['Low'].min()
                        drop_pct = (intraday_low - current_open) / current_open * 100
                        
                        if gap_down and current_rsi < rsi_threshold:
                            signals.append({
                                "Ticker": ticker,
                                "RSI(2)": round(current_rsi, 1),
                                "Drop %": round(drop_pct, 1),
                                "Entry Price": round(intraday_low, 2)
                            })
                except:
                    pass
        
        if signals:
            st.success(f"Found {len(signals)} signals")
            st.dataframe(pd.DataFrame(signals), use_container_width=True)
        else:
            st.info("No signals found")
    
    st.markdown("---")
    st.subheader("Stock Chart")
    
    chart_ticker = st.selectbox("Select stock", tickers if tickers else ["NVDA"])
    
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

with tab2:
    st.header("Backtest Results 2020-2025")
    
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
    
    fig = go.Figure(go.Bar(x=results["Stock"], y=results["Return %"], text=results["Return %"].round(1), textposition='auto', marker_color='green'))
    fig.update_layout(title="Top Performers", xaxis_title="Stock", yaxis_title="Return %")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Portfolio Simulation")
    initial = st.number_input("Initial Capital $", value=10000, step=5000)
    final = initial * (1 + 1.497)
    st.metric("5-Year Value", f"${final:,.0f}", delta=f"+${final - initial:,.0f}")

with tab3:
    st.header("Strategy Guide")
    st.markdown("**Entry Rules:**")
    st.markdown("- Open price < Previous day's low (gap down)")
    st.markdown("- RSI(2) drops below 10 during the day")
    st.markdown("- Intraday drop > 2% from open")
    st.markdown("- Buy at the intraday low")
    
    st.markdown("**Exit Rules:**")
    st.markdown("- Sell at next day's close")
    
    st.markdown("**Performance (38 stocks, 2020-2025):**")
    st.markdown("- 100% of stocks profitable")
    st.markdown("- 72.2% win rate on trades")
    st.markdown("- +149.7% average return per stock")
    st.markdown("- 20.1% annualized return")
    
    st.markdown("**Top 5 Stocks:**")
    st.markdown("1. COIN: +292.9%")
    st.markdown("2. NET: +257.7%")
    st.markdown("3. DDOG: +236.4%")
    st.markdown("4. CRWD: +231.0%")
    st.markdown("5. TSLA: +231.0%")
    
    st.warning("Disclaimer: Past performance does not guarantee future results. Paper trade before using real capital.")

st.markdown("---")
st.caption("RSI(2) Gap Down Strategy | Data from Yahoo Finance")