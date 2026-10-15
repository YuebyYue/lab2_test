import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Trading Strategy Dashboard", layout="wide")

st.title("Trading Strategy Dashboard")
st.caption("MSFT — Golden Cross Strategy (5-Year Backtest)")

# --- Data Loading ---
@st.cache_data
def load_data():
    stock = yf.Ticker("MSFT")
    data = stock.history(period="5y")
    return data

@st.cache_data
def calculate_moving_averages(data):
    data = data.copy()
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()
    return data

@st.cache_data
def identify_golden_cross(data):
    data = data.copy()
    data['GoldenCross'] = (data['MA50'] > data['MA200']) & (data['MA50'].shift(1) <= data['MA200'].shift(1))
    return data

@st.cache_data
def implement_strategy(data):
    positions = []
    data = data.iloc[200:].copy()
    buy_dates = data[data['GoldenCross'] == True].index.tolist()

    for buy_date in buy_dates:
        buy_price = data.loc[buy_date, 'Close']
        target_price = buy_price * 1.15
        max_sell_date = buy_date + pd.Timedelta(days=60)
        sell_period = data.loc[buy_date:max_sell_date].copy()
        target_reached = sell_period[sell_period['Close'] >= target_price]

        if not target_reached.empty:
            sell_date = target_reached.index[0]
            sell_price = target_reached.loc[sell_date, 'Close']
            sell_reason = "Target reached"
        else:
            sell_date_candidates = sell_period.index.tolist()
            if sell_date_candidates:
                sell_date = sell_date_candidates[-1]
                sell_price = data.loc[sell_date, 'Close']
                sell_reason = "Max holding period"
            else:
                continue

        holding_days = (sell_date - buy_date).days
        profit_pct = (sell_price / buy_price - 1) * 100

        positions.append({
            'BuyDate': buy_date,
            'BuyPrice': buy_price,
            'SellDate': sell_date,
            'SellPrice': sell_price,
            'HoldingDays': holding_days,
            'ProfitPct': profit_pct,
            'SellReason': sell_reason
        })

    return pd.DataFrame(positions)

# --- Load & Process ---
with st.spinner("Loading MSFT data..."):
    data = load_data()
    data = calculate_moving_averages(data)
    data = identify_golden_cross(data)
    positions = implement_strategy(data)

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Price Chart", "Trade Statistics", "Detailed Trades"])

# --- Tab 1: Price Chart ---
with tab1:
    st.subheader("Price Chart with Golden Cross Signals")

    # Prepare chart data
    chart_data = pd.DataFrame({
        'Stock Price': data['Close'],
        'MA50': data['MA50'],
        'MA200': data['MA200'],
    })

    # Buy signals
    buy_signals = pd.Series(np.nan, index=data.index)
    for _, row in positions.iterrows():
        buy_signals.loc[row['BuyDate']] = row['BuyPrice']
    chart_data['Buy Signal'] = buy_signals

    # Sell signals
    sell_signals = pd.Series(np.nan, index=data.index)
    for _, row in positions.iterrows():
        sell_signals.loc[row['SellDate']] = row['SellPrice']
    chart_data['Sell Signal'] = sell_signals

    st.line_chart(chart_data, use_container_width=True)

    st.caption("Green dots = Buy signals | Red dots = Sell signals")

# --- Tab 2: Trade Statistics ---
with tab2:
    st.subheader("Overall Trade Statistics")

    total_trades = len(positions)
    win_trades = len(positions[positions['ProfitPct'] > 0])
    loss_trades = total_trades - win_trades
    win_rate = win_trades / total_trades * 100 if total_trades > 0 else 0
    avg_profit = positions['ProfitPct'].mean()
    avg_holding = positions['HoldingDays'].mean()
    target_reached = len(positions[positions['SellReason'] == 'Target reached'])
    max_period = len(positions[positions['SellReason'] == 'Max holding period'])
    best_trade = positions['ProfitPct'].max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Trades", total_trades)
    col2.metric("Winning Trades", win_trades, f"{win_rate:.2f}% win rate")
    col3.metric("Losing Trades", loss_trades)
    col4.metric("Average Profit", f"+{avg_profit:.2f}%")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Target Reached", target_reached)
    col6.metric("Max Holding Period", max_period)
    col7.metric("Avg Holding Days", f"{avg_holding:.0f}")
    col8.metric("Best Trade", f"+{best_trade:.2f}%")

# --- Tab 3: Detailed Trades ---
with tab3:
    st.subheader("Detailed Trade Records")

    display_df = positions.copy()
    display_df['BuyDate'] = display_df['BuyDate'].dt.strftime('%Y-%m-%d')
    display_df['SellDate'] = display_df['SellDate'].dt.strftime('%Y-%m-%d')
    display_df['BuyPrice'] = display_df['BuyPrice'].apply(lambda x: f"${x:.2f}")
    display_df['SellPrice'] = display_df['SellPrice'].apply(lambda x: f"${x:.2f}")
    display_df['ProfitPct'] = display_df['ProfitPct'].apply(lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%")
    display_df = display_df.rename(columns={
        'BuyDate': 'Buy Date',
        'BuyPrice': 'Buy Price',
        'SellDate': 'Sell Date',
        'SellPrice': 'Sell Price',
        'HoldingDays': 'Holding Days',
        'ProfitPct': 'Profit',
        'SellReason': 'Sell Reason'
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)
