import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. 網頁配置 ---
st.set_page_config(page_title="賺大錢V1：全功能投資看板", layout="wide")
st.title("💰 賺大錢V1：資產、健檢、飆股偵測器")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

# --- 2. 核心數據處理函數 ---
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

def get_suffix(code):
    return ".TW" if (len(code) <= 4 and code.isdigit()) or "B" in code.upper() else ".TWO"

def get_stock_analysis(code):
    t_code = f"{code}{get_suffix(code)}"
    hist = yf.download(t_code, period="60d", progress=False)
    if hist.empty or len(hist) < 20: return None
    
    current_p = hist['Close'].iloc[-1].item()
    ma10 = hist['Close'].rolling(window=10).mean().iloc[-1].item()
    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1].item()
    
    # 找關鍵一條線 (過去20日漲幅>4%紅K之最低點)
    recent = hist.tail(20).copy()
    recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
    long_red = recent[recent['Pct'] >= 4]
    key_line = long_red.iloc[-1]['Low'].item() if not long_red.empty else ma20
    
    # 計算 10MA 乖離率
    bias_10ma = ((current_p - ma10) / ma10) * 100
    
    return {
        "現價": current_p,
        "10MA": ma10,
        "關鍵線": key_line,
        "10MA乖離": bias_10ma,
        "歷史數據": hist
    }

# --- 3. 執行主程式 ---
try:
    df = load_data()
    if df.empty:
        st.error("無法讀取 Google Sheet 數據，請檢查網址權限。")
    else:
        # --- A. 持股健檢與資產總覽 ---
        st.header("📋 持股健檢與資產總覽")
        tickers = df['標的代碼'].tolist()
        
        # 為了效能，首頁僅抓取最新價
        search_list = [f"{t}{get_suffix(t)}" for t in tickers]
        live_data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
        
        current_prices = {}
        for t in tickers:
            t_code = f"{t}{get_suffix(t)}"
            try:
                val = live_data[t_code]['Close'].iloc[-1]
                current_prices[t] = val if not pd.isna(val) else 0
            except: current_prices[t] = 0

        df['現價'] = df['標的代碼'].map(current_prices)
        df['市值'] = df['現價'] * df['持股數']
        df['成本'] = df['成交均價'] * df['持股數']
        df['損益'] = df['市值'] - df['成本']
        df['報酬率%'] = (df['損益'] / df['成本'] * 100).round(2)

        c1, c2, c3 = st.columns(3)
        c1.metric("總市值", f"${df['市值'].sum():,.0f}")
        c2.metric("總損益", f"${df['損益'].sum():,.0f}", f"{df['損益'].sum()/df['成本'].sum()*100:.2f}%")
        c3.info("💡 點擊下方按鈕進行深度健檢")

        if st.button("🔍 執行 47 檔深度健檢 (10MA 乖離偵測)"):
            check_results = []
            with st.spinner('掃描 10MA 乖離中...'):
                for t in tickers:
                    analysis = get_stock_analysis(t)
                    if analysis:
                        bias = analysis['10MA乖離']
                        if bias >= 15: status = "💰 乖離過大 (建議獲利)"
                        elif bias <= 3 and analysis['現價'] > analysis['關鍵線']: status = "🎯 支撐買點"
                        elif analysis['現價'] < analysis['關鍵線']: status = "❌ 破線防守"
                        else: status = "📈 穩定運行"
                        check_results.append({"代碼": t, "狀態": status, "10MA乖離%": f"{bias:.1f}%"})
            st.table(pd.DataFrame(check_results))

        # --- B. 個股診斷區 (關鍵一條線畫圖) ---
        st.write("---")
        st.header("🔍 個股深度診斷")
        target = st.text_input("輸入代碼 (2451, 00878, 00687B)", "").strip()
        if target:
            res = get_stock_analysis(target)
            if res:
                col1, col2, col3 = st.columns(3)
                col1.metric("10MA 乖離", f"{res['10MA乖離']:.2f}%")
                col2.metric("關鍵防守線", f"{res['關鍵線']:.2f}")
                col3.success("趨勢偏多") if res['現價'] > res['關鍵線'] else col3.error("趨勢偏空")
                
                fig = px.line(res['歷史數據'].tail(30), y='Close', title=f"{target} 走勢與關鍵防守線")
                fig.add_hline(y=res['關鍵線'], line_dash="dash", line_color="red", annotation_text="關鍵一條線")
                fig.add_hline(y=res['10MA'], line_dash="dot", line_color="orange", annotation_text="10MA")
                st.plotly_chart(fig, use_container_width=True)

        # --- C. 飆股尋找功能 (市場掃描) ---
        st.write("---")
        st.header("🚀 飆股尋找器 (多頭排列+強勢紅K)")
        if st.button("🔥 掃描市場強勢標的"):
            # 這裡示範掃描熱門觀察標的，可自行增加
            watch_list = ["2330", "2317", "2454", "2382", "3231", "2308", "6669", "2451", "3034"]
            found = []
            with st.spinner('正在尋找符合關鍵線邏輯之標的...'):
                for w in watch_list:
                    ans = get_stock_analysis(w)
                    if ans and ans['10MA乖離'] < 10 and ans['現價'] > ans['關鍵線']:
                        found.append({"代碼": w, "現價": ans['現價'], "狀態": "✅ 符合強勢回檔守線"})
            if found:
                st.dataframe(pd.DataFrame(found), use_container_width=True)
            else:
                st.write("目前熱門股中暫無符合回檔買點標的。")

        # --- D. 資產配置清單 ---
        st.write("---")
        st.subheader("📑 詳細持股清單")
        st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '報酬率%', '資產類別']], use_container_width=True)

except Exception as e:
    st.error(f"系統運行中: {e}")
