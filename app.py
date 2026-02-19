import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="賺大錢V1：穩定監控版", layout="wide")
st.title("💰 賺大錢V1：穩定數據監控")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

def get_single_price(code):
    """一檔一檔精準抓取現價"""
    suffix = ".TW" if (len(code) <= 4 and code.isdigit()) or "B" in code.upper() else ".TWO"
    t_code = f"{code}{suffix}"
    try:
        # 只抓最近 5 天的資料，確保能拿到最後一個收盤價
        stock = yf.Ticker(t_code)
        hist = stock.history(period="5d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return 0
    except:
        return 0

# --- 主程式執行 ---
df = load_data()

if not df.empty:
    if st.button("🔄 重新整理即時行情"):
        st.cache_data.clear()

    # 建立一個進度條，因為一檔一檔抓會需要一點時間
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    current_prices = []
    for i, code in enumerate(df['標的代碼']):
        status_text.text(f"正在更新第 {i+1}/{len(df)} 檔: {code}...")
        price = get_single_price(code)
        current_prices.append(price)
        progress_bar.progress((i + 1) / len(df))
    
    status_text.text("✅ 行情更新完成！")
    
    # 計算數據
    df['現價'] = current_prices
    df['市值'] = df['現價'] * df['持股數']
    df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
    df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)

    # 儀表板
    c1, c2, c3 = st.columns(3)
    total_val = df['市值'].sum()
    total_profit = df['損益'].sum()
    c1.metric("總市值", f"${total_val:,.0f}")
    c2.metric("總損益", f"${total_profit:,.0f}", f"{(total_profit/(df['成交均價']*df['持股數']).sum()*100):.2f}%")
    c3.success("穩定連線中")

    # 持股清單
    st.subheader("📑 詳細持股監控")
    st.dataframe(df[['標的代碼', '標的名稱', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)

    # --- 🔍 個股診斷 (當你需要看 10MA 或 關鍵一條線時再用) ---
    st.write("---")
    st.header("🔍 個股技術診斷")
    target = st.text_input("輸入代碼看 10MA 乖離與關鍵線 (如: 2451, 00878)", "").strip()
    
    if target:
        suffix = ".TW" if (len(target) <= 4 and target.isdigit()) or "B" in target.upper() else ".TWO"
        t_code = f"{target}{suffix}"
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
            
            d1, d2, d3 = st.columns(3)
            d1.metric("10MA 乖離", f"{bias_10ma:.2f}%")
            d2.metric("關鍵防守價", f"{key_line:.2f}")
            
            if bias_10ma >= 15:
                d3.warning("💰 建議獲利")
            elif curr_p < key_line:
                d3.error("❌ 破線")
            else:
                d3.info("📈 趨勢續抱")

            fig = px.line(hist.tail(30), y='Close', title=f"{target} 走勢圖")
            fig.add_hline(y=key_line, line_dash="dash", line_color="red", annotation_text="關鍵一條線")
            fig.add_hline(y=ma10, line_dash="dot", line_color="orange", annotation_text="10MA")
            st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("等待資料中...")
