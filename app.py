import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 設定網頁標題
st.set_page_config(page_title="賺大錢V1 - 資產監控中心", layout="wide")
st.title("📈 賺大錢V1：資產規畫紀錄追蹤")

# 1. 讀取 Google Sheet 資料 (這裡未來會連結您的檔案)
# 假設我們讀取後的資料存成 df
def load_data():
    # 這裡會放入連結您 Google Drive 檔案的邏輯
    # 範例欄位：標的代碼, 標的名稱, 持股數, 成交均價, 資產類別
    return pd.read_csv("your_portfolio.csv") 

df = load_data()

# 2. 自動抓取即時現價 (Yahoo Finance)
def get_live_prices(tickers):
    # 台股需加上 .TW
    formatted_tickers = [str(t) + ".TW" if len(str(t)) == 4 else str(t) for t in tickers]
    data = yf.download(formatted_tickers, period="1d")['Close'].iloc[-1]
    return data

# 3. 計算資產數據
# 市值 = 持股數 * 現價
# 損益 = (現價 - 均價) * 持股數

# 4. 網頁視覺化呈現
col1, col2, col3 = st.columns(3)
col1.metric("總資產市值", "計算中...")
col2.metric("總未實現損益", "計算中...", delta_color="normal")
col3.metric("預估年領息", "計算中...")

# 畫出資產配置圖
fig = px.pie(df, values='市值', names='資產類別', title='我的資產分布')
st.plotly_chart(fig)
