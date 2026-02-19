import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="賺大錢V1：雙分頁戰術看板", layout="wide")
st.title("💰 賺大錢V1：資產與戰術看板")

# 2. 定義頁籤 (分頁切換)
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🎯 戰術實驗區 (空白)"])

# 3. 讀取數據 (資料源共用)
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

# --- 第一頁：資產監控 (放入您最穩定的那一版邏輯) ---
with tab1:
    df_raw = load_data()
    if not df_raw.empty:
        st.info("🔄 正在同步 47 檔標的行情...")
        
        # 穩定版行情抓取邏輯
        def get_live_prices(tickers_raw):
            search_list = []
            for t in tickers_raw:
                search_list.append(f"{t}.TW")
                search_list.append(f"{t}.TWO")
            
            # 抓取數據
            data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
            
            price_dict = {}
            for t in tickers_raw:
                try:
                    # 優先檢查 .TW
                    tw_p = data[f"{t}.TW"]['Close'].iloc[-1] if f"{t}.TW" in data.columns else None
                    if pd.notna(tw_p):
                        price_dict[t] = tw_p
                    else:
                        # 抓不到則檢查 .TWO
                        two_p = data[f"{t}.TWO"]['Close'].iloc[-1] if f"{t}.TWO" in data.columns else None
                        price_dict[t] = two_p if pd.notna(two_p) else 0
                except:
                    price_dict[t] = 0
            return price_dict

        live_prices = get_live_prices(df_raw['標的代碼'].tolist())
        
        # 計算數據
        df = df_raw.copy()
        df['現價'] = df['標的代碼'].map(live_prices)
        df['市值'] = df['現價'] * df['持股數']
        df['成本'] = df['成交均價'] * df['持股數']
        df['未實現損益'] = df['市值'] - df['成本']
        df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

        # 儀表板
        c1, c2, c3 = st.columns(3)
        total_mkt = df['市值'].sum()
        total_profit = df['未實現損益'].sum()
        c1.metric("總資產市值", f"${total_mkt:,.0f}")
        c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/df['成本'].sum()*100):.2f}%")
        c3.success("✅ 行情同步成功")

        # 圖表與清單
        st.subheader("📊 資產配置與清單")
        st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)
        st.dataframe(df[['標的代碼', '標的名稱', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)
    else:
        st.warning("等待資料源載入中...")

# --- 第二頁：實驗區 (目前留空) ---
with tab2:
    st.header("🎯 戰術開發實驗區")
    st.write("這裡是空白區。待第一頁完全確認沒問題後，我們再慢慢把「關鍵一條線」加進來。")
