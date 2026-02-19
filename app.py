import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁配置與分頁定義 (地基)
st.set_page_config(page_title="賺大錢V1：專業版", layout="wide")
st.title("💰 賺大錢V1：資產與飆股雷達")

# 定義頁籤
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🚀 新飆股偵測 (實驗區)"])

# 2. 公共工具函數 (兩邊分頁共用)
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

def get_real_ticker(code):
    """精準對齊代碼，包含債券 ETF (00687B)"""
    if "B" in code.upper() or (len(code) <= 4 and code.isdigit()):
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 第一頁：資產監控 (確保現價 100% 正確) ---
with tab1:
    df_raw = load_data()
    if not df_raw.empty:
        st.info("🔄 正在更新市場行情...")
        
        # 採用一對一賦值，保證價格與標的絕對對齊
        prices = []
        progress = st.progress(0)
        for i, code in enumerate(df_raw['標的代碼']):
            full_t = get_real_ticker(code)
            try:
                # 抓取最近兩天數據以確保有最新收盤價
                hist = yf.Ticker(full_t).history(period="2d")
                prices.append(hist['Close'].iloc[-1] if not hist.empty else 0)
            except: prices.append(0)
            progress.progress((i + 1) / len(df_raw))
        
        df = df_raw.copy()
        df['現價'] = prices
        df['市值'] = df['現價'] * df['持股數']
        
        # 修正錯字計算損益
        if '成交均價' in df.columns:
            df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
            df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)
        
        # 顯示儀表板
        m1, m2 = st.columns(2)
        m1.metric("總市值", f"${df['市值'].sum():,.0f}")
        m2.success("✅ 行情已同步")
        
        st.dataframe(df[['標的代碼', '標的名稱', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)
        st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)

# --- 第二頁：波若威模式實驗室 (新飆股偵測) ---
with tab2:
    st.header("🚀 新飆股偵測：波若威模式")
    st.info("掃描條件：量大(>2x) + 漲幅(>3%) + 乖離小(<12%)")
    
    # 這裡放我們討論的「新飆股」掃描名單
    watchlist = ["4908", "2451", "2330", "2317", "2382", "3231", "3034", "6669", "2308", "1513", "1605"]
    
    if st.button("🔥 啟動全市場熱門股掃描"):
        results = []
        status_txt = st.empty()
        pg = st.progress(0)
        
        for i, code in enumerate(watchlist):
            status_txt.text(f"掃描中: {code}")
            full_t = get_real_ticker(code)
            try:
                h = yf.download(full_t, period="20d", progress=False)
                if len(h) > 10:
                    if isinstance(h.columns, pd.MultiIndex): h.columns = h.columns.get_level_values(0)
                    
                    cp, pp = h['Close'].iloc[-1], h['Close'].iloc[-2]
                    cv, av = h['Volume'].iloc[-1], h['Volume'].tail(5).mean()
                    ma10 = h['Close'].rolling(window=10).mean().iloc[-1]
                    
                    v_ratio = cv / av
                    change = ((cp - pp) / pp) * 100
                    bias = ((cp - ma10) / ma10) * 100
                    
                    if v_ratio > 1.5 and change > 2: # 稍微放寬一點條件方便測試
                        results.append({
                            "代碼": code, "漲跌%": round(change, 2), 
                            "量能倍數": round(v_ratio, 2), "10MA乖離%": round(bias, 2),
                            "關鍵防守價": round(h['Low'].iloc[-1], 2)
                        })
            except: pass
            pg.progress((i + 1) / len(watchlist))
        
        if results:
            st.dataframe(pd.DataFrame(results).sort_values("量能倍數", ascending=False), use_container_width=True)
        else:
            st.write("目前無符合條件的標的。")
