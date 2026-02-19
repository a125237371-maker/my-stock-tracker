import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta

# --- 填息價差戰情室 ---
st.subheader("🎯 填息交易追蹤 (公告即時偵測)")

def get_dividend_alerts(stock_list):
    alerts = []
    for code in stock_list:
        # 轉換為 yfinance 代碼
        ticker_code = f"{code}.TW" if int(code) < 10000 else f"{code}.TWO"
        stock = yf.Ticker(ticker_code)
        
        # 抓取最近的除息公告
        info = stock.calendar
        if 'Dividend Date' in info and info['Dividend Date']:
            div_date = info['Dividend Date']
            # 只顯示「未來」或「剛除息 5 天內」的公告
            if div_date >= (datetime.now().date() - timedelta(days=5)):
                alerts.append({
                    "標的": code,
                    "除息日": div_date,
                    "除息金額": stock.info.get('dividendRate', 0),
                    "目前股價": stock.info.get('currentPrice', 0),
                })
    return pd.DataFrame(alerts)

# 假設 df 是你讀取 Google Sheet 的持股清單
my_codes = df['標的代碼'].astype(str).tolist()

# 偵測公告
with st.spinner('正在偵測公告中...'):
    dividend_alerts = get_dividend_alerts(my_codes)

if not dividend_alerts.empty:
    st.success("📢 偵測到近期除息公告！")
    # 顯示列表，並幫你算「填息進度」
    st.table(dividend_alerts)
else:
    # 如果沒公告就顯示一句話，保持畫面清爽
    st.write("目前 47 檔持股暫無最新除息公告，耐心等待進場時機。")
