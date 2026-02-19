import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="賺大錢V1：綜合戰術看板", layout="wide")
st.title("💰 賺大錢V1：綜合投資工具箱")

# 2. 定義分頁頁籤
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🎯 關鍵戰術 (實驗區)"])

# 3. 共享數據載入函數
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

def get_ticker_suffix(code):
    if (len(code) <= 4 and code.isdigit()) or "B" in code.upper():
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 第一頁：資產監控 (完全沿用穩定邏輯) ---
with tab1:
    st.header("實時資產追蹤")
    df_raw = load_data()
    if not df_raw.empty:
        with st.spinner('同步市場報價中...'):
            search_list = [get_ticker_suffix(c) for c in df_raw['標的代碼'].tolist()]
            # 採用的穩定批次下載法
            market_data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
            
            price_map = {}
            for t in df_raw['標的代碼'].tolist():
                full_t = get_ticker_suffix(t)
                try:
                    price_map[t] = market_data[full_t]['Close'].iloc[-1]
                except:
                    price_map[t] = 0
            
            df = df_raw.copy()
            df['現價'] = df['標的代碼'].map(price_map)
            df['市值'] = df['現價'] * df['持股數']
            df['成本'] = df['成交均價'] * df['持股數']
            df['報酬率%'] = ((df['現價'] - df['成交均軍價']) / df['成交均價'] * 100).round(2) if '成交均價' in df.columns else 0
            
            # 儀表板
            m1, m2 = st.columns(2)
            m1.metric("總資產市值", f"${df['市值'].sum():,.0f}")
            m2.success("✅ 行情同步完成 (含債券 ETF)")
            
            st.dataframe(df[['標的代碼', '標的名稱', '現價', '持股數', '資產類別']], use_container_width=True)
            st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)
    else:
        st.warning("請檢查 Google Sheet 資料源。")

# --- 第二頁：關鍵戰術 (新功能開發區) ---
with tab2:
    st.header("📈 關鍵一條線 x 10MA 診斷器")
    st.info("這裡測試：長紅K最低點防守位 & 10MA 正乖離 15% 獲利法。")
    
    test_target = st.text_input("輸入代碼診斷買賣點 (例如: 2451, 00878)", "").strip()
    
    if test_target:
        with st.spinner(f'正在分析 {test_target} 戰術位置...'):
            t_full = get_ticker_suffix(test_target)
            hist = yf.download(t_full, period="60d", progress=False)
            
            if not hist.empty:
                # 修正 yfinance 多重索引
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                curr_p = hist['Close'].iloc[-1]
                ma10 = hist['Close'].rolling(window=10).mean().iloc[-1]
                
                # 關鍵一條線 (20日內漲幅>4%紅K最低點)
                recent = hist.tail(20).copy()
                recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
                long_red = recent[recent['Pct'] >= 4]
                key_line = long_red.iloc[-1]['Low'] if not long_red.empty else hist['Close'].rolling(window=20).mean().iloc[-1]
                
                bias_10ma = ((curr_p - ma10) / ma10) * 100
                
                # 戰術儀表板
                d1, d2, d3 = st.columns(3)
                d1.metric("10MA 乖離率", f"{bias_10ma:.2f}%")
                d2.metric("關鍵防守價", f"{key_line:.2f}")
                
                if bias_10ma >= 15:
                    d3.warning("💰 建議分批獲利")
                elif curr_p < key_line:
                    d3.error("❌ 破線警訊")
                elif bias_10ma <= 3:
                    d3.success("🎯 支撐買點")
                else:
                    d3.info("📉 趨勢續抱")

                # 畫出戰術圖
                fig = px.line(hist.tail(30), y='Close', title=f"{test_target} 戰術圖表")
                fig.add_hline(y=key_line, line_dash="dash", line_color="red", annotation_text="關鍵線")
                fig.add_hline(y=ma10, line_dash="dot", line_color="orange", annotation_text="10MA")
                st.plotly_chart(fig, use_container_width=True)
