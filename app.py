import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. 共用工具區 (地基，放最上面)
# ==========================================

st.set_page_config(page_title="賺大錢V1 資產看板", layout="wide")
st.title("💰 賺大錢V1：綜合戰術看板")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    """讀取 Google Sheet CSV"""
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"資料載入失敗: {e}")
        return pd.DataFrame()

def get_live_prices(tickers_raw):
    """穩定版：自動偵測上市櫃即時行情"""
    price_dict = {}
    search_list = []
    for t in tickers_raw:
        search_list.append(f"{t}.TW")
        search_list.append(f"{t}.TWO")
    
    # 批次抓取
    data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
    
    for t in tickers_raw:
        try:
            # 優先嘗試 .TW
            tw_col = f"{t}.TW"
            if tw_col in data.columns and not data[tw_col]['Close'].dropna().empty:
                price_dict[t] = data[tw_col]['Close'].iloc[-1]
            else:
                # 嘗試 .TWO
                two_col = f"{t}.TWO"
                if two_col in data.columns and not data[two_col]['Close'].dropna().empty:
                    price_dict[t] = data[two_col]['Close'].iloc[-1]
                else:
                    price_dict[t] = 0
        except:
            price_dict[t] = 0
    return price_dict

@st.cache_data(ttl=3600)
def check_dividend_alerts(tickers_raw):
    """除息公告偵測函數"""
    alert_list = []
    today = datetime.now().date()
    for t in tickers_raw:
        # 邏輯優化：4位數字且不帶字母的通常是台股股票，其他可能是 ETF
        t_code = f"{t}.TW"
        s = yf.Ticker(t_code)
        cal = s.calendar
        
        # 備援判斷：如果上市抓不到，且符合上櫃特徵
        if (cal is None or 'Dividend Date' not in cal) and (len(t) == 4 and t.isdigit()):
            t_code = f"{t}.TWO"
            s = yf.Ticker(t_code)
            cal = s.calendar

        if cal is not None and 'Dividend Date' in cal:
            div_date = cal['Dividend Date']
            # 抓取最近 3 天到未來的公告
            if div_date >= (today - timedelta(days=3)):
                alert_list.append({
                    "標的代碼": t,
                    "除息日": div_date,
                    "預估配息": s.info.get('dividendRate', "公告中"),
                    "目前股價": s.info.get('currentPrice', "N/A"),
                    "殖利率(%)": f"{s.info.get('dividendYield', 0)*100:.2f}%" if s.info.get('dividendYield') else "計算中"
                })
    return pd.DataFrame(alert_list)

# ==========================================
# 2. 頁籤定義 (導航區)
# ==========================================

tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🚀 波若威模式 (實驗區)"])

# ==========================================
# 3. 分頁內容執行
# ==========================================

try:
    df_raw = load_data()
    
    # --- 第一頁內容 ---
    with tab1:
        if not df_raw.empty:
            st.info("🔄 正在同步行情與掃描 00687B 等標的公告...")
            
            # 執行共用函數
            live_prices = get_live_prices(df_raw['標的代碼'].tolist())
            
            df = df_raw.copy()
            df['現價'] = df['標的代碼'].map(live_prices)
            df['市值'] = df['現價'] * df['持股數']
            df['成本'] = df['成交均價'] * df['持股數']
            df['未實現損益'] = df['市值'] - df['成本']
            df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

            # 儀表板
            total_mkt = df['市值'].sum()
            total_cost = df['成本'].sum()
            total_profit = total_mkt - total_cost

            c1, c2, c3 = st.columns(3)
            c1.metric("總資產市值", f"${total_mkt:,.0f}")
            c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/total_cost*100):.2f}%")
            c3.metric("偵測狀態", "✅ 公共函數驅動中")

            # 除息戰情室
            st.write("---")
            st.subheader("🗓️ 近期除息公告偵測")
            with st.spinner('掃描中...'):
                dividend_alerts = check_dividend_alerts(df['標的代碼'].tolist())
            
            if not dividend_alerts.empty:
                st.success(f"📢 偵測到 {len(dividend_alerts)} 筆公告！")
                st.dataframe(dividend_alerts, use_container_width=True)
            else:
                st.write("✨ 目前持股暫無最新公告。")

            st.subheader("📊 資產配置分布")
            fig = px.pie(df, values='市值', names='資產類別', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📑 詳細持股清單")
            st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)

    # --- 第二頁內容 (待填入) ---
    with tab2:
        st.header("🎯 波若威模式：新飆股偵測區")
        st.write("這裡會使用最上方的公共函數進行「全市場掃描」。")
        # 您剛才提到的「波若威模式」代碼可以寫在這裡
        if st.button("🔥 啟動新飆股偵測"):
            st.write("偵測邏輯運行中... (這裡您可以自行發揮)")

except Exception as e:
    st.error(f"發生預期外錯誤: {e}")
