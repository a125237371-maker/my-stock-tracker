import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 網頁配置
st.set_page_config(page_title="賺大錢V1：資產監控版", layout="wide")
st.title("💰 賺大錢V1：穩定資產監控")

# Google Sheet CSV 連結
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"讀取 Sheet 失敗: {e}")
        return pd.DataFrame()

def get_real_ticker(code):
    """精準判斷台股與債券 ETF 後綴"""
    # 判斷是否為債券 ETF (代碼包含 B) 或 一般上市股票
    if "B" in code.upper() or (len(code) <= 4 and code.isdigit()):
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 核心邏輯開始 ---
df = load_data()

if not df.empty:
    st.info("🔄 正在同步 47 檔標的最新報價，請稍候...")
    
    # 建立進度條
    progress_bar = st.progress(0)
    current_prices = []
    
    # 採一檔一檔精準對齊模式，徹底避免價格錯位
    for i, code in enumerate(df['標的代碼']):
        full_ticker = get_real_ticker(code)
        try:
            # 獲取最新行情
            ticker_obj = yf.Ticker(full_ticker)
            # 抓取最近 1 天數據
            hist = ticker_obj.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                price = 0.0
        except:
            price = 0.0
        
        current_prices.append(price)
        progress_bar.progress((i + 1) / len(df))

    # 更新 DataFrame 數據
    df['現價'] = current_prices
    df['市值'] = df['現價'] * df['持股數']
    df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
    df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)

    # 儀表板
    total_market_value = df['市值'].sum()
    total_cost = (df['成交均價'] * df['持股數']).sum()
    total_profit = total_market_value - total_cost
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總市值", f"${total_market_value:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", f"{(total_profit/total_cost*100):.2f}%")
    c3.success("✅ 行情同步完成")

    # --- 詳細持股清單 ---
    st.subheader("📑 實時持股監控清單")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)

    # --- 資產分布圖表 ---
    st.write("---")
    st.subheader("📊 資產類別權重")
    fig = px.pie(df, values='市值', names='資產類別', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("等待 Google Sheet 數據中，請確保連結正確。")
