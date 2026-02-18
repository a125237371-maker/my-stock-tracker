import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 設定網頁
st.set_page_config(page_title="賺大錢V1 資產看板", layout="wide")
st.title("💰 賺大錢V1：資產規畫即時追蹤")

# 1. 處理 Google Sheet 網址 (將 edit 改為 export?format=csv)
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)  # 每 10 分鐘自動更新一次，避免被 Yahoo 封鎖
def load_data():
    # 讀取試算表，請確認您的分頁名稱正確，或直接讀取第一頁
    df = pd.read_csv(raw_url)
    # 確保代碼是字串格式
    df['標的代碼'] = df['標的代碼'].astype(str)
    return df

try:
    df = load_data()

    # 2. 格式化代碼以符合 yfinance (例如 2330 -> 2330.TW)
    def format_ticker(symbol):
        symbol = symbol.strip()
        if symbol.isdigit():
            return f"{symbol}.TW"
        # 處理 00687B 或 00937B 等債券型
        if symbol.endswith('B') or symbol.endswith('A'):
            return f"{symbol}.TW"
        return f"{symbol}.TW"

    tickers = [format_ticker(s) for s in df['標的代碼']]

    # 3. 抓取即時價格
    st.info("正在連線至市場抓取最新報價...")
    price_data = yf.download(tickers, period="1d")['Close']
    
    # 取得最新一筆非空值
    last_prices = price_data.iloc[-1]

    # 4. 損益計算
    df['現價'] = df['標的代碼'].apply(lambda x: round(last_prices.get(format_ticker(x), 0), 2))
    df['市值'] = df['現價'] * df['持股數']
    df['成本'] = df['成交均價'] * df['持股數']
    df['未實現損益'] = df['市值'] - df['成本']
    df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

    # 5. 儀表板視覺化
    total_mkt = df['市值'].sum()
    total_cost = df['成本'].sum()
    total_profit = total_mkt - total_cost

    c1, c2, c3 = st.columns(3)
    c1.metric("總資產市值", f"${total_mkt:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/total_cost*100):.2f}%")
    c3.metric("持股檔數", f"{len(df)} 檔")

    # 資產比例圖
    st.subheader("📊 資產配置分布")
    fig = px.pie(df, values='市值', names='資產類別', hole=0.4,
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

    # 詳細清單
    st.subheader("📑 詳細持股清單")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '成交均價', '現價', '未實現損益', '報酬率(%)', '資產類別']], 
                 use_container_width=True)

except Exception as e:
    st.error(f"讀取資料發生錯誤，請檢查試算表權限或格式。錯誤訊息: {e}")
