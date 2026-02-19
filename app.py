import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# --- 1. 公共區域：所有頁籤共用的地基 ---
st.set_page_config(page_title="賺大錢V1：專業版", layout="wide")
st.title("💰 賺大錢V1：資產與飆股雷達")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
  
# --- 2. 定義導航頁籤 ---
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🚀 波若威模式 (實驗區)"])

# --- 第一頁：資產監控 ---
with tab1:
    df_raw = load_data()
    if not df_raw.empty:
        st.info("🔄 正在更新即時行情...")
        # 呼叫公共區域的抓取函數
        live_prices = fetch_stock_data(df_raw['標的代碼'].tolist())
        
        df = df_raw.copy()
        df['現價'] = df['標的代碼'].map(live_prices)
        df['市值'] = df['現價'] * df['持股數']
        
        # 修正錯字計算
        if '成交均價' in df.columns:
            df['未實現損益'] = df['市值'] - (df['成交均價'] * df['持股數'])
            df['報酬率%'] = (df['未實現損益'] / (df['成交均價'] * df['持股數']) * 100).round(2)
        
        m1, m2 = st.columns(2)
        m1.metric("總市值", f"${df['市值'].sum():,.0f}")
        m2.success("✅ 市場數據同步完成")
        
        st.dataframe(df[['標的代碼', '標的名稱', '現價', '報酬率%', '資產類別']], use_container_width=True)
        st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)

# --- 第二頁：波若威模式 ---
with tab2:
    st.header("🕵️ 波若威模式偵測器")
    # 這裡的邏輯也會呼叫公共區域的 get_real_ticker，不會再報 NameError
    test_list = ["4908", "2451", "2330", "2317", "2382", "3231", "3034", "6669"]
    
    if st.button("🔍 執行波若威模式掃描"):
        results = []
        pg = st.progress(0)
        for i, code in enumerate(test_list):
            t_full = get_real_ticker(code)
            try:
                h = yf.download(t_full, period="20d", progress=False)
                if len(h) > 10:
                    # 強制拉平多重索引避免 Plotly 報錯
                    if isinstance(h.columns, pd.MultiIndex): h.columns = h.columns.get_level_values(0)
                    
                    cp, pp = h['Close'].iloc[-1], h['Close'].iloc[-2]
                    cv, av = h['Volume'].iloc[-1], h['Volume'].tail(5).mean()
                    ma10 = h['Close'].rolling(window=10).mean().iloc[-1]
                    
                    results.append({
                        "代碼": code, "漲跌%": round(((cp-pp)/pp)*100, 2),
                        "量能倍數": round(cv/av, 2), "10MA乖離%": round(((cp-ma10)/ma10)*100, 2)
                    })
            except: pass
            pg.progress((i+1)/len(test_list))
        
        if results:
            st.dataframe(pd.DataFrame(results).sort_values("量能倍數", ascending=False), use_container_width=True)
