import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="賺大錢V1：關鍵策略看板", layout="wide")
st.title("💰 賺大錢V1：關鍵一條線 x 15% 獲利策略")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(raw_url)
    df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
    return df

# --- 🎯 關鍵策略偵測邏輯 (含 15% 獲利警示) ---
def get_key_line_analysis(code):
    # 支援債券 ETF 與 一般股票代碼
    suffix = ".TW" if (len(code) <= 4 and code.isdigit()) or "B" in code.upper() else ".TWO"
    t_code = f"{code}{suffix}"
    
    hist = yf.download(t_code, period="40d", progress=False)
    if hist.empty or len(hist) < 20: return "資料不足", 0, 0
    
    # 尋找過去 20 天內的關鍵長紅 K (漲幅 > 4% 且收盤價為波段高點)
    recent = hist.tail(20).copy()
    recent['Pct_Change'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
    long_red_candles = recent[recent['Pct_Change'] >= 4]
    
    if not long_red_candles.empty:
        latest_key = long_red_candles.iloc[-1]
        key_line_price = latest_key['Low'].item() # 關鍵一條線：長紅K最低點
        current_price = recent['Close'].iloc[-1].item()
        dist = ((current_price - key_line_price) / key_line_price) * 100
        
        # 判斷邏輯
        if current_price < key_line_price:
            status = "❌ 破線 (趨勢轉弱，建議避開)"
        elif dist >= 15:
            status = "💰 正乖離 > 15% (過熱，建議分批獲利)"
        elif dist <= 3:
            status = "🎯 接近關鍵線 (支撐強，分批佈局)"
        else:
            status = f"📈 關鍵線上 (乖離 {dist:.1f}%)"
        return status, key_line_price, dist
    else:
        return "☁️ 整理中 (目前無強勢紅K)", 0, 0

try:
    df = load_data()
    
    # --- 頂部摘要 ---
    st.info("🔄 正在執行 47 檔標的之關鍵策略掃描...")

    # --- 🔍 策略決策區 ---
    st.write("---")
    st.subheader("🚀 關鍵一條線 x 獲利了結偵測器")
    st.caption("策略：回檔至線不破買進，正乖離 > 15% 或破線賣出")

    if st.button("🔍 執行全持股診斷"):
        with st.spinner('掃描長紅 K 與計算乖離率中...'):
            results = []
            for _, row in df.iterrows():
                status, key_p, dist = get_key_line_analysis(row['標的代碼'])
                results.append({
                    "代碼": row['標的代碼'],
                    "名稱": row['標的名稱'],
                    "策略建議": status,
                    "關鍵防守價": f"{key_p:.2f}" if key_p > 0 else "-",
                    "距關鍵線 (%)": f"{dist:.1f}%" if key_p > 0 else "-"
                })
            res_df = pd.DataFrame(results)
            # 將需要「獲利」或「買進」的優先排在上面
            sort_order = {"💰 正乖離 > 15% (過熱，建議分批獲利)": 0, "🎯 接近關鍵線 (支撐強，分批佈局)": 1, "📈 關鍵線上 (乖離": 2}
            st.dataframe(res_df, use_container_width=True)

    # --- 原有圖表 ---
    st.write("---")
    st.subheader("📊 現有資產分佈")
    live_prices = {} # 這裡可以整合你原本抓價格的邏輯...
    # (此處保留你原本的 px.pie 與詳細清單代碼即可)

except Exception as e:
    st.error(f"偵測過程發生問題: {e}")
