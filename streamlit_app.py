import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
import time
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="RSI(2) Trading Bot Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 10px;
    }
    .signal-buy {
        background-color: #00ff0022;
        padding: 10px;
        border-radius: 10px;
        border-left: 4px solid #00ff00;
    }
    .signal-wait {
        background-color: #ffaa0022;
        padding: 10px;
        border-radius: 10px;
        border-left: 4px solid #ffaa00;
    }
</style>
""", unsafe_allow_html=True)

# Session state for tracking
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = None

# Title
st.title("📈 RSI(2) Trading Bot Pro")
st.markdown("**Mean Reversion Strategy | Gap Down + RSI(2) < 10 | Next Day Exit**")
st.markdown("---")

# ============ SIDEBAR ============
with st.sidebar:
    st.header("⚙️ Strategy Parameters")
    
    rsi_threshold = st.slider("RSI(2) Threshold", 2, 20, 10, 
                               help="Buy when RSI drops below this value")
    
    min_drop = st.slider("Min Intraday Drop (%)", 1, 10, 2,
                         help="Minimum % drop from open to trigger")
    
    hold_days = st.selectbox("Holding Period (Days)", [1, 2, 3, 4, 5], index=0,
                             help="Sell after this many days")
    
    st.markdown("---")
    st.header("📊 Stock Universe")
    
    # Expanded stock list - Top 25 performers
    all_stocks = {
        "Top Performers": ["COIN", "NET", "DDOG", "CRWD", "TSLA", "SHOP", "SMCI", "IONQ", "NVDA", "UAL"],
        "Semiconductors": ["AMD", "MU", "AVGO", "AMAT", "LRCX", "ON", "MPWR"],
        "Software/SaaS": ["PLTR", "MDB", "SNOW", "CRM", "ADBE", "NOW", "PANW"],
        "Mega Cap": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    }
    
    selected_tiers = st.multiselect(
        "Select Stock Groups",
        list(all_stocks.keys()),
        default=["Top Performers"]
    )
    
    tickers = []
    for tier in selected_tiers:
        tickers.extend(all_stocks[tier])
    tickers = list(set(tickers))  # Remove duplicates
    
    st.caption(f"Monitoring {len(tickers)} stocks")
    
    st.markdown("---")
    st.header("💰 Risk Management")
    
    position_size = st.slider("Position Size (% of portfolio)", 1, 20, 5)
    max_daily_trades = st.number_input("Max Trades Per Day", 1, 10, 3)
    stop_loss = st.slider("Stop Loss (%)", -10, -1, -5, help="Exit if down this much")
    
    st.markdown("---")
    st.header("🔔 Alerts")
    email = st.text_input("Email for Alerts (optional)", placeholder="your@email.com")
    
    st.markdown("---")
    st.caption("Strategy validated on 38 stocks | +149.7% return (2020-2025)")

# ============ FUNCTIONS ============
def calculate_rsi(data, period=2):
    """Calculate RSI"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(data, period=14):
    """Calculate ATR for volatility"""
    high = data['High']
    low = data['Low']
    close = data['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def get_stock_metrics(ticker):
    """Get fundamental metrics for a stock"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'market_cap': info.get('marketCap', 0),
            'beta': info.get('beta', 1),
            'volume': info.get('volume', 0),
            'avg_volume': info.get('averageVolume', 0)
        }
    except:
        return None

def scan_for_signals(tickers, rsi_thresh, min_drop_pct):
    """Enhanced signal scanner"""
    signals = []
    
    for ticker in tickers:
        try:
            # Get daily data
            daily = yf.download(ticker, period="5d", progress=False)
            if len(daily) < 2:
                continue
            
            # Get intraday data
            intraday = yf.download(ticker, period="1d", interval="5m", progress=False)
            if len(intraday) < 5:
                continue
            
            # Calculate conditions
            prev_low = daily['Low'].iloc[-2]
            current_open = daily['Open'].iloc[-1]
            gap_down = current_open < prev_low
            gap_pct = (current_open - prev_low) / prev_low * 100
            
            rsi = calculate_rsi(intraday['Close'], 2)
            current_rsi = rsi.iloc[-1]
            rsi_touch_time = intraday.index[rsi < rsi_thresh] if any(rsi < rsi_thresh) else []
            
            intraday_low = intraday['Low'].min()
            intraday_high = intraday['High'].max()
            drop_pct = (intraday_low - current_open) / current_open * 100
            current_price = intraday['Close'].iloc[-1]
            
            # Volatility check
            atr = calculate_atr(intraday)
            current_atr = atr.iloc[-1] if len(atr) > 0 else 0
            atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0
            
            # Signal strength (0-100)
            signal_strength = 0
            if gap_down:
                signal_strength += 30
            if current_rsi < rsi_thresh:
                signal_strength += 40
            if drop_pct < -min_drop_pct:
                signal_strength += 30
            
            if gap_down and current_rsi < rsi_thresh and drop_pct < -min_drop_pct:
                signals.append({
                    "Ticker": ticker,
                    "Signal": "🔴 BUY",
                    "Strength": f"{signal_strength}%",
                    "RSI(2)": round(current_rsi, 1),
                    "Gap %": round(gap_pct, 1),
                    "Drop %": round(drop_pct, 1),
                    "Entry": round(intraday_low, 2),
                    "Current": round(current_price, 2),
                    "ATR %": round(atr_pct, 1),
                    "Time": datetime.now().strftime("%H:%M")
                })
        except Exception as e:
            continue
    
    return signals

# ============ MAIN TABS ============
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔴 Live Signals", "📊 Backtest", "📈 Analytics", "💰 Paper Trading", "📖 Guide"])

# ============ TAB 1: LIVE SIGNALS ============
with tab1:
    st.header("🔴 Real-Time Signal Scanner")
    st.caption(f"Scanning {len(tickers)} stocks | RSI threshold: {rsi_threshold} | Min drop: {min_drop}%")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Stocks Monitored", len(tickers))
    with col2:
        st.metric("RSI Threshold", rsi_threshold)
    with col3:
        st.metric("Min Drop", f"{min_drop}%")
    with col4:
        st.metric("Hold Days", hold_days)
    
    # Auto-refresh checkbox
    auto_refresh = st.checkbox("Auto-refresh every 5 minutes", value=False)
    
    if st.button("🔄 Scan Now", type="primary", use_container_width=True):
        with st.spinner(f"Scanning {len(tickers)} stocks for RSI(2) drops..."):
            signals = scan_for_signals(tickers, rsi_threshold, min_drop)
            st.session_state.last_scan = datetime.now()
        
        if signals:
            st.balloons()
            st.success(f"🚨 {len(signals)} SIGNAL(S) FOUND!")
            
            # Display signals in a nice table
            signals_df = pd.DataFrame(signals)
            st.dataframe(signals_df, use_container_width=True, hide_index=True)
            
            # Trade execution instructions
            st.markdown("---")
            st.subheader("🎯 Trade Execution")
            
            for signal in signals:
                with st.container():
                    st.markdown(f"""
                    <div class="signal-buy">
                    <b>{signal['Ticker']}</b> - BUY SIGNAL<br>
                    Entry Price: <b>${signal['Entry']}</b><br>
                    Current RSI(2): <b>{signal['RSI(2)']}</b><br>
                    Position Size: <b>{position_size}%</b> of portfolio<br>
                    Stop Loss: <b>{abs(stop_loss)}%</b> below entry<br>
                    Exit: Close on <b>{hold_days} day(s)</b>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add to trade history
                    st.session_state.trade_history.append({
                        'date': datetime.now(),
                        'ticker': signal['Ticker'],
                        'entry': signal['Entry'],
                        'position_size': position_size,
                        'status': 'open'
                    })
        else:
            st.info("⏳ No signals detected. Waiting for RSI(2) to drop below threshold after a gap down.")
            
            # Show current market status
            st.markdown("---")
            st.subheader("📊 Current Market Status")
            
            # Show RSI for selected stocks
            rsi_status = []
            for ticker in tickers[:10]:  # Limit to 10 for performance
                try:
                    df = yf.download(ticker, period="1d", interval="5m", progress=False)
                    if len(df) > 0:
                        rsi = calculate_rsi(df['Close'], 2)
                        current_rsi = rsi.iloc[-1]
                        rsi_status.append({"Ticker": ticker, "Current RSI(2)": round(current_rsi, 1)})
                except:
                    pass
            
            if rsi_status:
                st.dataframe(pd.DataFrame(rsi_status), use_container_width=True)
    
    if auto_refresh:
        st.rerun()

# ============ TAB 2: BACKTEST RESULTS ============
with tab2:
    st.header("📊 Backtest Results (2020-2025)")
    
    # Full results from your backtest
    full_results = pd.DataFrame({
        "Ticker": ["COIN", "NET", "DDOG", "CRWD", "TSLA", "SHOP", "SMCI", "IONQ", "NVDA", "UAL", 
                   "ALB", "PLTR", "MPWR", "MDB", "VST", "AMD", "MU", "AVGO", "AMAT", "META"],
        "Return %": [292.9, 257.7, 236.4, 231.0, 231.0, 225.2, 221.8, 220.3, 220.1, 211.9,
                     203.4, 191.7, 191.5, 183.0, 158.4, 170.8, 104.2, 122.3, 95.2, 106.3],
        "Win Rate %": [76.9, 72.7, 78.7, 78.9, 67.4, 72.7, 70.2, 71.4, 71.6, 68.4,
                      70.8, 70.0, 78.1, 64.7, 79.5, 72.0, 65.7, 80.9, 71.9, 77.6],
        "Trades": [78, 77, 75, 76, 86, 77, 84, 56, 67, 76,
                  96, 70, 64, 85, 44, 82, 67, 47, 57, 49]
    })
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        min_return = st.slider("Minimum Return %", 0, 300, 0)
    with col2:
        min_win_rate = st.slider("Minimum Win Rate %", 0, 100, 50)
    
    filtered = full_results[(full_results["Return %"] >= min_return) & (full_results["Win Rate %"] >= min_win_rate)]
    
    st.dataframe(filtered.sort_values("Return %", ascending=False), use_container_width=True, hide_index=True)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Average Return", "+149.7%", delta="vs SPY +60%")
    with col2:
        st.metric("Win Rate", "72.2%", delta="+12%")
    with col3:
        st.metric("Total Trades", "2,365", delta="38 stocks")
    with col4:
        st.metric("Profitable Stocks", "38/38", delta="100%")
    
    # Charts
    st.subheader("📊 Performance Visualization")
    
    chart_type = st.radio("Select Chart", ["Bar Chart", "Scatter Plot"], horizontal=True)
    
    if chart_type == "Bar Chart":
        fig = go.Figure(go.Bar(
            x=filtered.head(15)["Ticker"],
            y=filtered.head(15)["Return %"],
            text=filtered.head(15)["Return %"].round(1),
            textposition='auto',
            marker_color='green',
            marker_line_color='darkgreen',
            marker_line_width=1
        ))
        fig.update_layout(title="Top 15 Performers by Return", xaxis_title="Stock", yaxis_title="Return (%)", height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.scatter(
            filtered, x="Win Rate %", y="Return %", 
            text="Ticker", size="Trades",
            title="Return vs Win Rate Analysis",
            labels={"Win Rate %": "Win Rate (%)", "Return %": "Total Return (%)"}
        )
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)
    
    # Portfolio simulation
    st.subheader("💰 Portfolio Simulation")
    
    col1, col2 = st.columns(2)
    with col1:
        initial_capital = st.number_input("Initial Capital ($)", value=10000, step=5000)
    with col2:
        num_stocks = st.slider("Number of stocks to trade", 1, 38, 10)
    
    # Calculate simulated return
    top_stocks = full_results.nlargest(num_stocks, "Return %")
    avg_stock_return = top_stocks["Return %"].mean()
    final_value = initial_capital * (1 + avg_stock_return / 100)
    
    st.metric(f"Portfolio Value ({num_stocks} stocks)", f"${final_value:,.0f}", 
              delta=f"+${final_value - initial_capital:,.0f}")
    st.caption(f"Average return of top {num_stocks} stocks: {avg_stock_return:.1f}%")

# ============ TAB 3: ANALYTICS ============
with tab3:
    st.header("📈 Market Analytics")
    
    # Selected stock for deep analysis
    analyze_ticker = st.selectbox("Select stock for detailed analysis", tickers)
    
    if analyze_ticker:
        # Fetch data
        df_daily = yf.download(analyze_ticker, period="3mo", progress=False)
        df_intraday = yf.download(analyze_ticker, period="5d", interval="5m", progress=False)
        
        if not df_daily.empty:
            # Calculate indicators
            df_daily['RSI2'] = calculate_rsi(df_daily['Close'], 2)
            df_daily['ATR'] = calculate_atr(df_daily)
            df_daily['Prev_Low'] = df_daily['Low'].shift(1)
            df_daily['Gap_Down'] = df_daily['Open'] < df_daily['Prev_Low']
            df_daily['Signal'] = df_daily['Gap_Down'] & (df_daily['RSI2'] < rsi_threshold)
            
            # Price chart
            st.subheader(f"{analyze_ticker} - Daily Chart")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_daily.index, open=df_daily['Open'], high=df_daily['High'],
                low=df_daily['Low'], close=df_daily['Close'], name=analyze_ticker
            ))
            
            # Add signal markers
            signal_dates = df_daily[df_daily['Signal']].index
            for date in signal_dates:
                fig.add_vline(x=date, line_dash="dash", line_color="green", line_width=1)
            
            fig.update_layout(height=400, xaxis_title="Date", yaxis_title="Price")
            st.plotly_chart(fig, use_container_width=True)
            
            # RSI chart
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_daily.index, y=df_daily['RSI2'], name="RSI(2)", line=dict(color='purple', width=2)))
            fig2.add_hline(y=rsi_threshold, line_dash="dash", line_color="red", annotation_text=f"Threshold: {rsi_threshold}")
            fig2.add_hline(y=5, line_dash="dot", line_color="orange", annotation_text="Extreme")
            fig2.update_layout(height=200, yaxis_range=[0, 100])
            st.plotly_chart(fig2, use_container_width=True)
            
            # Statistics
            st.subheader("📊 Stock Statistics")
            
            signals_found = df_daily['Signal'].sum()
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Signals (3 months)", signals_found)
            with col2:
                st.metric("Avg RSI(2)", round(df_daily['RSI2'].mean(), 1))
            with col3:
                st.metric("Min RSI(2)", round(df_daily['RSI2'].min(), 1))
            with col4:
                st.metric("Current RSI(2)", round(df_daily['RSI2'].iloc[-1], 1))
            
            # Intraday pattern
            if not df_intraday.empty:
                st.subheader("Intraday Pattern Today")
                df_intraday['RSI2'] = calculate_rsi(df_intraday['Close'], 2)
                
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=df_intraday.index, y=df_intraday['Close'], name="Price", line=dict(color='blue')))
                fig3.add_trace(go.Scatter(x=df_intraday.index, y=df_intraday['RSI2'], name="RSI(2)", line=dict(color='purple'), yaxis="y2"))
                fig3.update_layout(
                    height=400,
                    yaxis=dict(title="Price"),
                    yaxis2=dict(title="RSI(2)", overlaying='y', side='right', range=[0, 100])
                )
                st.plotly_chart(fig3, use_container_width=True)

# ============ TAB 4: PAPER TRADING ============
with tab4:
    st.header("💰 Paper Trading Journal")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Active Trades")
        if st.session_state.trade_history:
            active_trades = [t for t in st.session_state.trade_history if t.get('status') == 'open']
            if active_trades:
                st.dataframe(pd.DataFrame(active_trades), use_container_width=True)
            else:
                st.info("No active trades")
        else:
            st.info("No trades yet. Click 'Scan Now' to find signals")
    
    with col2:
        st.subheader("📊 Performance")
        if st.session_state.trade_history:
            closed_trades = [t for t in st.session_state.trade_history if t.get('status') == 'closed']
            st.metric("Total Trades", len(st.session_state.trade_history))
            st.metric("Closed Trades", len(closed_trades))
        else:
            st.metric("Total Trades", 0)
    
    st.subheader("📋 Add Manual Trade")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        manual_ticker = st.text_input("Ticker", "AAPL")
    with col2:
        manual_entry = st.number_input("Entry Price", value=100.0)
    with col3:
        manual_size = st.number_input("Position Size %", value=5)
    with col4:
        if st.button("Add Trade"):
            st.session_state.trade_history.append({
                'date': datetime.now(),
                'ticker': manual_ticker.upper(),
                'entry': manual_entry,
                'position_size': manual_size,
                'status': 'open'
            })
            st.success("Trade added!")
            st.rerun()

# ============ TAB 5: GUIDE ============
with tab5:
    st.header("📖 Complete Strategy Guide")
    
    st.markdown("""
    ### 🎯 Strategy Overview
    
    This is a **mean reversion strategy** that capitalizes on panic selling. When a stock gaps down and RSI(2) drops below 10, it's often oversold and likely to bounce.
    
    ### 📋 Entry Rules
    
    | Condition | Requirement | Explanation |
    |-----------|-------------|-------------|
    | Gap Down | Open < Previous Day's Low | Weakness confirmed |
    | RSI Drop | RSI(2) < 10 | Extreme oversold |
    | Intraday Panic | Drop > 2% from open | Capitulation |
    | Entry | Buy at intraday low | Best price |
    
    ### 📤 Exit Rules
    
    | Condition | Action |
    |-----------|--------|
    | Standard | Sell at next day's close |
    | Stop Loss | Exit if down 5% from entry |
    | Take Profit | Consider at +10% |
    
    ### 📊 Performance Statistics
    