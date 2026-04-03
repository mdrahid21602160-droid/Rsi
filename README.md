# RSI(2) Gap Down Trading Strategy

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-name.streamlit.app)

## 📈 Strategy Overview

This trading bot implements a mean-reversion strategy based on the 2-period RSI indicator and gap down conditions.

### Strategy Rules
- **Entry:** Open < Previous Low AND RSI(2) < 10 AND intraday drop >2%
- **Buy:** At the intraday low
- **Exit:** Sell at next day's close
- **Hold Period:** 1 day

### Backtest Results (2020-2025)
- **38 stocks tested, 100% profitable**
- **Average return: +149.7%**
- **Win rate: 72.2%**
- **Annualized return: 20.1%**

### Top Performers
| Stock | Return | Trades | Win Rate |
|-------|--------|--------|----------|
| COIN  | +292.9% | 78 | 76.9% |
| NET   | +257.7% | 77 | 72.7% |
| DDOG  | +236.4% | 75 | 78.7% |
| CRWD  | +231.0% | 76 | 78.9% |
| TSLA  | +231.0% | 86 | 67.4% |

## 🚀 Live Demo

[https://your-app-name.streamlit.app](https://your-app-name.streamlit.app)

## 🛠️ Local Development

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rsi2-trading-bot.git
cd rsi2-trading-bot

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py