import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# --- 1. 網頁配置 ---
st.set_page_config(page_title="賺大錢V1：資產與策略看板", layout="wide")
st.title("💰 賺大錢V1：資產現價與關鍵策略偵測")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

# --- 2. 工具函數 ---
@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"讀取 Google Sheet 失敗: {e}")
        return pd.DataFrame()

def get_ticker(code):
    """判斷上市、上櫃或債券代碼後綴"""
    if (len(code) <= 4 and code.isdigit()) or "B" in code.upper():
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 3. 主程式執行 ---
df_raw = load_data()

if not df_raw.empty:
    with st.spinner('正在獲取最新市場現價...'):
        # 準備所有代碼的 yf 格式
        tickers = [get_ticker(c) for c in df_raw['標的代碼'].tolist()]
        
        # 一次性抓取所有現價 (最快的方法)
        data = yf.download(tickers, period="5d", progress=False)
        
        # 處理 yf 可能回傳的多重索引問題
        if isinstance(data.columns, pd.MultiIndex):
            close_data = data['Close']
        else:
            close_data = data[['Close']]

        # 提取每檔標的最後一筆非空價格
        current_prices = {}
        for t in tickers:
            try:
                series = close_data[t].dropna()
                if not series.empty:
                    current_prices[t] = series.iloc[-1]
                else:
                    current_prices[t] = 0
            except:
                current_prices[t] = 0

    # 4. 更新資產表
    df = df_raw.copy()
    df['現價'] = df['標的代碼'].apply(lambda x: current_prices.get(get_ticker(x), 0))
    df['市值'] = df['現價'] * df['持股數']
    df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
    df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)

    # --- 儀表板數值 ---
    total_market_value = df['市值'].sum()
    total_profit = df['損益'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_market_value:,.0f}")
    c2.metric("總損益", f"${total_profit:,.0f}", f"{(total_profit/(df['成交均價']*df['持股數']).sum()*100):.2f}%")
    c3.success("數據已更新")

    # --- A. 詳細持股清單 (現價已正確跑出) ---
    st.subheader("📑 實時持股監控")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)

    st.write("---")

    # --- B. 個股策略診斷 (點擊才執行，節省效能) ---
    st.header("🔍 個股戰術診斷 (關鍵一條線 x 10MA)")
    target = st.text_input("請輸入代碼檢查 (例如: 2451, 00878, 00687B)", "").strip()
    
    if target:
        with st.spinner(f'正在計算 {target} 策略指標...'):
            t_code = get_ticker(target)
            hist = yf.download(t_code, period="60d", progress=False)
            
            if not hist.empty:
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                curr_p = hist['Close'].iloc[-1]
                ma10 = hist['Close'].rolling(window=10).mean().iloc[-1]
                
                # 關鍵一條線邏輯
                recent = hist.tail(20).copy()
                recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
                long_red = recent[recent['Pct'] >= 4]
                key_line = long_red.iloc[-1]['Low'] if not long_red.empty else hist['Close'].rolling(window=20).mean().iloc[-1]
                
                bias_10ma = ((curr_p - ma10) / ma10) * 100
                
                # 顯示診斷
                d1, d2, d3 = st.columns(3)
                d1.metric("10MA 乖離率", f"{bias_10ma:.2f}%")
                d2.metric("關鍵防守價", f"{key_line:.2f}")
                
                if bias_10ma >= 15:
                    d3.warning("💰 建議獲利")
                    st.warning("⚠️ 正乖離 > 15%，符合獲利了結準則。")
                elif curr_p < key_line:
                    d3.error("❌ 趨勢轉弱")
                    st.error("股價跌破關鍵線，建議嚴守防守。")
                elif bias_10ma <= 3:
                    d3.success("🎯 支撐買點")
                    st.success("接近關鍵線/均線，風險相對低，適合佈局。")
                else:
                    d3.info("📈 趨勢續抱")

                # 畫圖
                fig = px.line(hist.tail(30), y='Close', title=f"{target} 近 30 日走勢")
                fig.add_hline(y=key_line, line_dash="dash", line_color="red", annotation_text="關鍵一條線")
                fig.add_hline(y=ma10, line_dash="dot", line_color="orange", annotation_text="10MA")
                st.plotly_chart(fig, use_container_width=True)

    # --- C. 資產比例圖 ---
    st.write("---")
    st.subheader("📊 資產權重分佈")
    fig_pie = px.pie(df, values='市值', names='資產類別', hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.warning("等待 Google Sheet 數據中...")
