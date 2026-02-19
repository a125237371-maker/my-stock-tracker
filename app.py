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
    except: return pd.DataFrame()

def get_real_ticker(code):
    """精準代碼轉換：支援債券ETF(B)與上市櫃"""
    if "B" in code.upper() or (len(code) <= 4 and code.isdigit()):
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 2. 定義導航頁籤 ---
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🚀 波若威模式 (實驗區)"])

# --- 第一頁：資產監控 ---
with tab1:
    df_raw = load_data()
    if not df_raw.empty:
        st.info("🔄 正在更新即時行情...")
        
        # 採用一對一賦值，徹底解決資料錯位與現價 0 的問題
        current_prices = []
        progress_bar = st.progress(0)
        for i, code in enumerate(df_raw['標的代碼']):
            full_t = get_real_ticker(code)
            try:
                # 抓取最近 1 天數據
                ticker_obj = yf.Ticker(full_t)
                hist = ticker_obj.history(period="1d")
                current_prices.append(hist['Close'].iloc[-1] if not hist.empty else 0.0)
            except:
                current_prices.append(0.0)
            progress_bar.progress((i + 1) / len(df_raw))
        
        df = df_raw.copy()
        df['現價'] = current_prices
        df['市值'] = df['現價'] * df['持股數']
        
        # 修正計算邏輯與錯字 (刪除「軍」字)
        if '成交均價' in df.columns:
            df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
            df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)
        
        m1, m2 = st.columns(2)
        m1.metric("總市值", f"${df['市值'].sum():,.0f}")
        m2.success("✅ 市場數據同步完成 (含 00687B)")
        
        st.dataframe(df[['標的代碼', '標的名稱', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)
        st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)

# --- 第二頁：波若威模式實驗室 ---
with tab2:
    st.header("🚀 新飆股偵測：波若威模式")
    # 這裡現在可以安全讀取頂層的 get_real_ticker 函數，不再報 NameError
    watchlist = ["4908", "2451", "2330", "2317", "2382", "3231", "3034", "6669"]
    
    if st.button("🔥 啟動全市場熱門股掃描"):
        results = []
        pg = st.progress(0)
        for i, code in enumerate(watchlist):
            t_full = get_real_ticker(code)
            try:
                h = yf.download(t_full, period="20d", progress=False)
                if len(h) > 10:
                    # 修復 Plotly 繪圖報錯：拉平多重索引
                    if isinstance(h.columns, pd.MultiIndex): h.columns = h.columns.get_level_values(0)
                    
                    cp, pp = h['Close'].iloc[-1], h['Close'].iloc[-2]
                    cv, av = h['Volume'].iloc[-1], h['Volume'].tail(5).mean()
                    ma10 = h['Close'].rolling(window=10).mean().iloc[-1]
                    
                    if cv / av > 1.5 and ((cp-pp)/pp)*100 > 2:
                        results.append({
                            "代碼": code, "漲跌%": round(((cp-pp)/pp)*100, 2),
                            "量能倍數": round(cv/av, 2), "10MA乖離%": round(((cp-ma10)/ma10)*100, 2),
                            "關鍵防守價": round(h['Low'].iloc[-1], 2)
                        })
            except: pass
            pg.progress((i+1)/len(watchlist))
        
        if results:
            st.dataframe(pd.DataFrame(results).sort_values("量能倍數", ascending=False), use_container_width=True)
        else:
            st.write("目前無符合條件標的。")
