import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# --- 1. 網頁配置 ---
st.set_page_config(page_title="賺大錢V1：資產策略看板", layout="wide")
st.title("💰 賺大錢V1：資產現價與策略診斷")

# Google Sheet 連結
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"讀取 Sheet 失敗: {e}")
        return pd.DataFrame()

def get_ticker(code):
    """判斷代碼後綴，兼容債券 ETF 與一般股票"""
    if (len(code) <= 4 and code.isdigit()) or "B" in code.upper():
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 2. 主程式執行 ---
df_raw = load_data()

if not df_raw.empty:
    with st.spinner('正在獲取最新市場報價...'):
        # 準備所有代碼的 yfinance 格式
        ticker_list = [get_ticker(c) for c in df_raw['標的代碼'].tolist()]
        
        # 一次性抓取所有最新現價
        data = yf.download(ticker_list, period="5d", group_by='ticker', progress=False)
        
        current_prices = {}
        for t in df_raw['標的代碼'].tolist():
            t_full = get_ticker(t)
            try:
                # 處理 yfinance 多重索引，獲取 Close 價格
                if t_full in data.columns.levels[0]:
                    series = data[t_full]['Close'].dropna()
                    current_prices[t] = series.iloc[-1] if not series.empty else 0
                else:
                    current_prices[t] = 0
            except:
                current_prices[t] = 0

    # 更新數據表
    df = df_raw.copy()
    df['現價'] = df['標的代碼'].apply(lambda x: current_prices.get(x, 0))
    df['市值'] = df['現價'] * df['持股數']
    df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
    df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)

    # --- 儀表板 ---
    total_val = df['市值'].sum()
    total_profit = df['損益'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_val:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", f"{(total_profit/(df['成交均價']*df['持股數']).sum()*100):.2f}%")
    c3.success("行情已連線")

    # --- A. 詳細持股清單 (確保現價跑出來) ---
    st.subheader("📑 實時持股監控清單")
    # 這裡顯示您最關心的詳細表格
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)

    st.write("---")

    # --- B. 個股策略診斷 (手動輸入，避免跑不完) ---
    st.header("🔍 個股策略診斷 (關鍵一條線 x 10MA)")
    target = st.text_input("輸入代碼檢查策略 (如: 2451, 00878, 00687B)", "").strip()
    
    if target:
        with st.spinner(f'正在分析 {target}...'):
            t_full = get_ticker(target)
            hist = yf.download(t_full, period="60d", progress=False)
            
            if not hist.empty:
                # 修正多重索引問題
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                curr_p = hist['Close'].iloc[-1]
                ma10 = hist['Close'].rolling(window=10).mean().iloc[-1]
                
                # 關鍵一條線邏輯 (20日內漲幅>4%紅K之最低點)
                recent = hist.tail(20).copy()
                recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
                long_red = recent[recent['Pct'] >= 4]
                key_line = long_red.iloc[-1]['Low'] if not long_red.empty else hist['Close'].rolling(window=20).mean().iloc[-1]
                
                bias_10ma = ((curr_p - ma10) / ma10) * 100
                
                # 顯示診斷指標
                d1, d2, d3 = st.columns(3)
                d1.metric("10MA 乖離率", f"{bias_10ma:.2f}%")
                d2.metric("關鍵一條線 (防守價)", f"{key_line:.2f}")
                
                if bias_10ma >= 15:
                    d3.warning("💰 建議分批獲利")
                    st.warning("⚠️ 符合策略：10MA 正乖離 > 15%，短線過熱。")
                elif curr_p < key_line:
                    d3.error("❌ 趨勢轉弱")
                elif bias_10ma <= 3:
                    d3.success("🎯 支撐買點")
                else:
                    d3.info("📈 趨勢續抱")

                # 畫圖
                fig = px.line(hist.tail(30), y='Close', title=f"{target} 近期走勢與關鍵防守線")
                fig.add_hline(y=key_line, line_dash="dash", line_color="red", annotation_text="關鍵一條線")
                fig.add_hline(y=ma10, line_dash="dot", line_color="orange", annotation_text="10MA")
                st.plotly_chart(fig, use_container_width=True)

    # --- C. 資產分布圓餅圖 ---
    st.write("---")
    st.subheader("📊 資產類別分佈")
    st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)

else:
    st.warning("請檢查 Google Sheet 權限與數據格式。")
