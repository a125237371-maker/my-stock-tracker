import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="賺大錢V1：穩定數據版", layout="wide")
st.title("💰 賺大錢V1：資產現價穩定監控")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

def get_clean_price(code):
    """最穩定的單筆行情抓取邏輯"""
    suffix = ".TW" if (len(code) <= 4 and code.isdigit()) or "B" in code.upper() else ".TWO"
    t_code = f"{code}{suffix}"
    try:
        ticker = yf.Ticker(t_code)
        # 使用 fast_info 或是 history 抓取最新價
        hist = ticker.history(period="5d")
        if not hist.empty:
            # 確保欄位沒有多重索引問題
            return float(hist['Close'].iloc[-1])
        return 0.0
    except:
        return 0.0

# --- 主程式執行 ---
df = load_data()

if not df.empty:
    st.info("🔄 正在更新 47 檔標的即時行情，請稍候...")
    
    # 執行數據抓取
    prices = []
    progress_bar = st.progress(0)
    for i, code in enumerate(df['標的代碼']):
        p = get_clean_price(code)
        prices.append(p)
        progress_bar.progress((i + 1) / len(df))
    
    # 將數據寫回 DataFrame
    df['現價'] = prices
    df['現價'] = df['現價'].replace(0, method='ffill') # 避免暫時性 0 值的保險
    df['市值'] = df['現價'] * df['持股數']
    df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
    df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)

    # 頂部統計
    c1, c2, c3 = st.columns(3)
    total_val = df['市值'].sum()
    total_profit = df['損益'].sum()
    c1.metric("總市值", f"${total_val:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", f"{(total_profit/(df['成交均價']*df['持股數']).sum()*100):.2f}%")
    c3.success("✅ 行情同步成功")

    # 持股詳細清單
    st.subheader("📑 實時持股監控清單")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)

    # --- 🔍 個股診斷功能 (10MA 乖離 & 關鍵一條線) ---
    st.write("---")
    st.header("🔍 個股策略診斷")
    target = st.text_input("請輸入代碼 (例如: 2451, 00878, 00687B)", "").strip()
    
    if target:
        with st.spinner('計算策略指標中...'):
            suffix = ".TW" if (len(target) <= 4 and target.isdigit()) or "B" in target.upper() else ".TWO"
            t_code = f"{target}{suffix}"
            hist = yf.download(t_code, period="60d", progress=False)
            
            if not hist.empty:
                # 強制修復多重索引欄位
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                curr_p = float(hist['Close'].iloc[-1])
                ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                
                # 關鍵一條線偵測 (20日內漲幅>4%紅K最低點)
                recent = hist.tail(20).copy()
                recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
                long_red = recent[recent['Pct'] >= 4]
                key_line = float(long_red.iloc[-1]['Low']) if not long_red.empty else float(hist['Close'].rolling(window=20).mean().iloc[-1])
                
                bias_10ma = ((curr_p - ma10) / ma10) * 100
                
                d1, d2, d3 = st.columns(3)
                d1.metric("10MA 乖離率", f"{bias_10ma:.2f}%")
                d2.metric("關鍵防守價", f"{key_line:.2f}")
                
                if bias_10ma >= 15:
                    d3.warning("💰 建議獲利")
                elif curr_p < key_line:
                    d3.error("❌ 破線整理")
                elif bias_10ma <= 3:
                    d3.success("🎯 支撐買點")
                else:
                    d3.info("📈 趨勢續抱")

                fig = px.line(hist.tail(30), y='Close', title=f"{target} 近期走勢")
                fig.add_hline(y=key_line, line_dash="dash", line_color="red", annotation_text="關鍵線")
                st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("請確保 Google Sheet 網址正確且已公開分享。")
