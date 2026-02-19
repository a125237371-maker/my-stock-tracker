import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁配置
st.set_page_config(page_title="賺大錢V1：穩定戰術版", layout="wide")
st.title("💰 賺大錢V1：資產與戰術看板")

# 2. 定義頁籤 (分頁切換)
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🎯 關鍵戰術 (實驗區)"])

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

def get_real_ticker(code):
    """修正版：支援債券 ETF (如 00687B)"""
    if "B" in code.upper() or (len(code) <= 4 and code.isdigit()):
        return f"{code}.TW"
    return f"{code}.TWO"

# --- 分頁 1：資產監控 (原本穩定版) ---
with tab1:
    df_raw = load_data()
    if not df_raw.empty:
        st.info("🔄 正在同步 47 檔標的最新報價...")
        
        # 修正版：高效批次抓取
        all_tickers = [get_real_ticker(c) for c in df_raw['標的代碼'].tolist()]
        try:
            # 解決 MultiIndex 問題，直接提取 Close
            data = yf.download(all_tickers, period="1d", group_by='ticker', progress=False)
            
            prices = []
            for t in df_raw['標的代碼']:
                full_t = get_real_ticker(t)
                try:
                    p = data[full_t]['Close'].iloc[-1]
                    prices.append(p if pd.notna(p) else 0)
                except:
                    prices.append(0)
            
            df = df_raw.copy()
            df['現價'] = prices
            df['市值'] = df['現價'] * df['持股數']
            
            # 修正欄位名稱與計算 (修正截圖10的錯字問題)
            if '成交均價' in df.columns:
                df['損益'] = (df['現價'] - df['成交均價']) * df['持股數']
                df['報酬率%'] = ((df['現價'] - df['成交均價']) / df['成交均價'] * 100).round(2)
            
            # 儀表板
            c1, c2 = st.columns(2)
            c1.metric("總市值", f"${df['市值'].sum():,.0f}")
            c2.success("✅ 行情同步成功 (含 00687B)")
            
            st.dataframe(df[['標的代碼', '標的名稱', '現價', '成交均價', '報酬率%', '資產類別']], use_container_width=True)
            st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)
            
        except Exception as e:
            st.error(f"行情同步發生問題: {e}")

# --- 分頁 2：關鍵戰術 (新方案測試區) ---
with tab2:
    st.header("📈 關鍵一條線診斷")
    test_target = st.text_input("輸入代碼看 10MA 乖離與關鍵線 (例如: 2451)", "").strip()
    
    if test_target:
        with st.spinner('計算中...'):
            t_full = get_real_ticker(test_target)
            hist = yf.download(t_full, period="60d", progress=False)
            
            if not hist.empty:
                # 修正 MultiIndex 繪圖問題
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                
                curr_p = float(hist['Close'].iloc[-1])
                ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                
                # 關鍵一條線邏輯
                recent = hist.tail(20).copy()
                recent['Pct'] = (recent['Close'] - recent['Open']) / recent['Open'] * 100
                long_red = recent[recent['Pct'] >= 4]
                key_line = float(long_red.iloc[-1]['Low']) if not long_red.empty else float(hist['Close'].rolling(window=20).mean().iloc[-1])
                
                bias = ((curr_p - ma10) / ma10) * 100
                
                d1, d2 = st.columns(2)
                d1.metric("10MA 乖離", f"{bias:.2f}%")
                d2.metric("關鍵一條線 (防守位)", f"{key_line:.2f}")
                
                if bias >= 15: st.warning("💰 正乖離 > 15%，符合獲利了結點！")
                
                fig = px.line(hist.tail(30), y='Close', title=f"{test_target} 走勢圖")
                fig.add_hline(y=key_line, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)
