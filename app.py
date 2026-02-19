import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="賺大錢V1 資產看板", layout="wide")
st.title("💰 賺大錢V1：投資決策與資產追蹤")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(raw_url)
    df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
    return df

def get_live_prices(tickers_raw):
    price_dict = {}
    search_list = [f"{t}.TW" for t in tickers_raw] + [f"{t}.TWO" for t in tickers_raw]
    data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
    for t in tickers_raw:
        tw_price = data[f"{t}.TW"]['Close'].iloc[-1] if f"{t}.TW" in data.columns and not pd.isna(data[f"{t}.TW"]['Close'].iloc[-1]) else None
        if tw_price:
            price_dict[t] = tw_price
        else:
            two_price = data[f"{t}.TWO"]['Close'].iloc[-1] if f"{t}.TWO" in data.columns and not pd.isna(data[f"{t}.TWO"]['Close'].iloc[-1]) else None
            price_dict[t] = two_price if two_price else 0
    return price_dict

# --- 🎯 買賣點診斷邏輯 ---
def get_technical_signals(code):
    t_code = f"{code}.TW" if len(code) <= 4 and code.isdigit() else f"{code}.TWO"
    hist = yf.download(t_code, period="60d", progress=False)
    if hist.empty or len(hist) < 20: return "資料不足", 50
    
    # 計算 RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1].item()
    
    # 計算月線 (MA20)
    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1].item()
    current_p = hist['Close'].iloc[-1].item()
    
    if rsi < 30: signal = "🔥 超跌 (分批買進)"
    elif rsi > 70: signal = "⚠️ 超漲 (考慮減碼)"
    elif current_p > ma20: signal = "📈 多頭強勢"
    else: signal = "☁️ 盤整回檔"
    return signal, rsi

try:
    df = load_data()
    live_prices = get_live_prices(df['標的代碼'].tolist())
    df['現價'] = df['標的代碼'].map(live_prices)
    df['市值'] = df['現價'] * df['持股數']
    df['成本'] = df['成交均價'] * df['持股數']
    df['未實現損益'] = df['市值'] - df['成本']
    df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

    # 頂部指標
    total_mkt = df['市值'].sum()
    total_profit = total_mkt - df['成本'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_mkt:,.0f}")
    c2.metric("總損益", f"${total_profit:,.0f}", delta=f"{(total_profit/df['成本'].sum()*100):.2f}%")
    c3.metric("狀態", "✅ 行情與買賣點同步中")

    # --- 🔍 買賣點與診斷區 ---
    st.write("---")
    st.subheader("🔍 持股診斷與買賣點預警")
    if st.button("🚀 執行全持股技術掃描"):
        with st.spinner('分析 47 檔標的中...'):
            results = []
            for _, row in df.iterrows():
                sig, rsi_val = get_technical_signals(row['標的代碼'])
                results.append({"代碼": row['標的代碼'], "名稱": row['標的名稱'], "信號": sig, "RSI": f"{rsi_val:.1f}"})
            st.dataframe(pd.DataFrame(results), use_container_width=True)

    # 圖表與清單
    st.subheader("📊 資產配置與清單")
    st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)
    st.dataframe(df[['標的代碼', '標的名稱', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)

except Exception as e:
    st.error(f"錯誤: {e}")
