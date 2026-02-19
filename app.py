import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. 網頁配置 ---
st.set_page_config(page_title="賺大錢V1：全功能投資看板", layout="wide")
st.title("💰 賺大錢V1：資產、健檢、策略偵測器")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

# --- 2. 工具函數 ---
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Sheet 讀取失敗: {e}")
        return pd.DataFrame()

def get_ticker(code):
    # 支援債券 ETF 與 一般股票判斷
    if (len(code) <= 4 and code.isdigit()) or "B" in code.upper():
        return f"{code}.TW"
    return f"{code}.TWO"

def get_stock_analysis(code):
    try:
        t_code = get_ticker(code)
        # 抓取稍長的時間確保均線計算正確
        hist = yf.download(t_code, period="60d", progress=False)
        if hist.empty: return None
        
        # 處理 yfinance 多重索引問題
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)
            
        curr_p = float(hist['Close'].iloc[-1])
        ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
        ma20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
        
        # 關鍵一條線邏輯 (20日內漲幅>4%紅K最低點)
        recent = hist.tail(20).copy()
        recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
        long_red = recent[recent['Pct'] >= 4]
        key_line = float(long_red.iloc[-1]['Low']) if not long_red.empty else ma20
        
        bias_10ma = ((curr_p - ma10) / ma10) * 100
        return {"現價": curr_p, "10MA": ma10, "關鍵線": key_line, "10MA乖離": bias_10ma, "歷史": hist}
    except:
        return None

# --- 3. 主程式執行 ---
df = load_data()

if not df.empty:
    # --- A. 個股深度診斷 (10MA 乖離 & 關鍵一條線) ---
    st.header("🔍 個股戰術診斷")
    target = st.text_input("輸入代碼 (2451, 00878, 00687B)", "").strip()
    
    if target:
        with st.spinner(f'正在診斷 {target}...'):
            res = get_stock_analysis(target)
            if res:
                c1, c2, c3 = st.columns(3)
                c1.metric("10MA 乖離率", f"{res['10MA乖離']:.2f}%")
                c2.metric("關鍵防守價", f"{res['關鍵線']:.2f}")
                
                # 判定狀態
                if res['10MA乖離'] >= 15:
                    c3.warning("💰 10MA 乖離過熱")
                    st.warning("⚠️ 符合楊育華策略：正乖離 > 15%，建議分批獲利了結。")
                elif res['現價'] < res['關鍵線']:
                    c3.error("❌ 跌破關鍵線")
                    st.error("趨勢轉弱，跌破長紅K最低點，建議嚴守防守。")
                elif res['10MA乖離'] <= 3:
                    c3.success("🎯 接近支撐買點")
                    st.success("股價貼近均線/關鍵線，適合佈局拚填息。")
                else:
                    c3.info("📈 趨勢運行中")

                # 畫圖
                fig = px.line(res['歷史'].tail(30), y='Close', title=f"{target} 近期走勢")
                fig.add_hline(y=res['關鍵線'], line_dash="dash", line_color="red", annotation_text="關鍵一條線")
                fig.add_hline(y=res['10MA'], line_dash="dot", line_color="orange", annotation_text="10MA")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("抓取失敗，請確認代碼是否正確。")

    st.write("---")
    
    # --- B. 飆股尋找功能 (針對持股與熱門股) ---
    st.header("🚀 飆股與買點偵測")
    if st.button("🔥 掃描推薦標的"):
        watch_list = list(set(df['標的代碼'].tolist() + ["2330", "2451", "2317", "00878"]))
        found = []
        with st.spinner('掃描中...'):
            for w in watch_list[:15]: # 限制數量避免跑太久
                ans = get_stock_analysis(w)
                if ans and ans['10MA乖離'] < 10 and ans['現價'] > ans['關鍵線']:
                    found.append({"代碼": w, "狀態": "✅ 趨勢偏多且未過熱", "10MA乖離": f"{ans['10MA乖離']:.1f}%"})
        if found:
            st.table(pd.DataFrame(found))
        else:
            st.write("目前暫無符合回檔買點標的。")

    st.write("---")

    # --- C. 資產總覽 ---
    st.header("📋 持股資產總覽")
    # 這裡顯示你原本截圖一的清單內容
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '成交均價', '資產類別']], use_container_width=True)
