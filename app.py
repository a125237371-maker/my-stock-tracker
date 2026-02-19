import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="賺大錢V1 資產看板", layout="wide")
st.title("💰 賺大錢V1：關鍵一條線策略看板")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(raw_url)
    df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
    return df

# --- 🎯 關鍵一條線偵測邏輯 ---
def get_key_line_analysis(code):
    t_code = f"{code}.TW" if len(code) <= 4 and code.isdigit() else f"{code}.TWO"
    hist = yf.download(t_code, period="40d", progress=False)
    if hist.empty or len(hist) < 20: return "資料不足", 0, 0
    
    # 尋找過去 20 天內符合「關鍵紅K」的標的 (漲幅 > 4% 且過前高)
    recent_data = hist.tail(20).copy()
    recent_data['Pct_Change'] = (recent_data['Close'] - recent_data['Open']) / recent_data['Open'] * 100
    
    # 篩選出長紅 K (收紅且漲幅 > 4%)
    long_red_candles = recent_data[recent_data['Pct_Change'] >= 4]
    
    if not long_red_candles.empty:
        # 取最後出現的那根關鍵紅K
        latest_key_candle = long_red_candles.iloc[-1]
        key_line_price = latest_key_candle['Low'].item() # 關鍵一條線：紅K最低點
        current_price = recent_data['Close'].iloc[-1].item()
        dist = ((current_price - key_line_price) / key_line_price) * 100
        
        if current_price < key_line_price:
            status = "❌ 破線 (趨勢轉弱)"
        elif dist <= 3:
            status = "🎯 接近關鍵線 (支撐買點)"
        elif dist > 10:
            status = "⚠️ 乖離過大 (不宜追高)"
        else:
            status = "📈 線上強勢"
        return status, key_line_price, dist
    else:
        return "☁️ 盤整 (無關鍵紅K)", 0, 0

try:
    df = load_data()
    
    # 頂部儀表板與損益計算 (保留原功能)
    st.info("🔄 正在掃描 47 檔標的之「關鍵一條線」位置...")
    
    # --- 🔍 關鍵一條線戰情室 ---
    st.write("---")
    st.subheader("🎯 關鍵一條線：買賣點決策區")
    st.caption("依據楊育華分析師邏輯：回檔至長紅K最低點不破為最佳買點")

    if st.button("🚀 執行全持股策略掃描"):
        with st.spinner('掃描長紅 K 棒中...'):
            results = []
            for _, row in df.iterrows():
                status, key_price, dist = get_key_line_analysis(row['標的代碼'])
                results.append({
                    "代碼": row['標的代碼'],
                    "名稱": row['標的名稱'],
                    "目前狀態": status,
                    "關鍵防守價": f"{key_price:.2f}" if key_price > 0 else "未偵測到",
                    "距關鍵線 (%)": f"{dist:.1f}%" if key_price > 0 else "-"
                })
            # 排序：把「接近關鍵線」的排在最前面，方便找買點
            res_df = pd.DataFrame(results)
            st.dataframe(res_df.sort_values("目前狀態", ascending=False), use_container_width=True)

    # (下方保留原本的圓餅圖與持股清單程式碼...)
    # ... 原本的 px.pie 與 df 顯示邏輯 ...
    st.subheader("📊 原有資產配置")
    # ... (此處省略部分重複代碼，請直接在您 GitHub 檔案中保留即可)

except Exception as e:
    st.error(f"系統偵測中: {e}")
