import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="賺大錢V1 資產看板", layout="wide")
st.title("💰 賺大錢V1：自動偵測資產追蹤")

raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(raw_url)
    df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
    return df

def get_live_prices(tickers_raw):
    price_dict = {}
    search_list = []
    for t in tickers_raw:
        search_list.append(f"{t}.TW")
        search_list.append(f"{t}.TWO")
    
    data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
    
    for t in tickers_raw:
        tw_price = data[f"{t}.TW"]['Close'].iloc[-1] if f"{t}.TW" in data.columns and not pd.isna(data[f"{t}.TW"]['Close'].iloc[-1]) else None
        if tw_price:
            price_dict[t] = tw_price
        else:
            two_price = data[f"{t}.TWO"]['Close'].iloc[-1] if f"{t}.TWO" in data.columns and not pd.isna(data[f"{t}.TWO"]['Close'].iloc[-1]) else None
            price_dict[t] = two_price if two_price else 0
    return price_dict

# --- 🎯 修正版：除息公告偵測函數 ---
@st.cache_data(ttl=3600)
def check_dividend_alerts(tickers_raw):
    alert_list = []
    today = datetime.now().date()
    for t in tickers_raw:
        # 修正判斷邏輯：債券 ETF 或代碼帶字母的都走 .TW 嘗試，抓不到再換
        t_code = f"{t}.TW"
        s = yf.Ticker(t_code)
        cal = s.calendar
        
        # 如果上市抓不到，且代碼是 4 位純數字（上櫃股票），嘗試 .TWO
        if (cal is None or 'Dividend Date' not in cal) and (len(t) == 4 and t.isdigit()):
            t_code = f"{t}.TWO"
            s = yf.Ticker(t_code)
            cal = s.calendar

        if cal is not None and 'Dividend Date' in cal:
            div_date = cal['Dividend Date']
            if div_date >= (today - timedelta(days=3)):
                alert_list.append({
                    "標的代碼": t,
                    "除息日": div_date,
                    "預估配息": s.info.get('dividendRate', "公告中"),
                    "目前股價": s.info.get('currentPrice', "N/A"),
                    "殖利率(%)": f"{s.info.get('dividendYield', 0)*100:.2f}%" if s.info.get('dividendYield') else "計算中"
                })
    return pd.DataFrame(alert_list)

try:
    # 確保先載入 df
    df = load_data()
    st.info("🔄 正在同步行情與掃描 00687B 等標的公告...")
    
    live_prices = get_live_prices(df['標的代碼'].tolist())
    
    df['現價'] = df['標的代碼'].map(live_prices)
    df['市值'] = df['現價'] * df['持股數']
    df['成本'] = df['成交均價'] * df['持股數']
    df['未實現損益'] = df['市值'] - df['成本']
    df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

    # 儀表板數據
    total_mkt = df['市值'].sum()
    total_cost = df['成本'].sum()
    total_profit = total_mkt - total_cost

    c1, c2, c3 = st.columns(3)
    c1.metric("總資產市值", f"${total_mkt:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/total_cost*100):.2f}%")
    c3.metric("偵測狀態", "✅ 全資產類型兼容中")

    # --- 🎯 填息戰情室 ---
    st.write("---")
    st.subheader("🗓️ 近期除息公告偵測")
    with st.spinner('掃描中，包含債券 ETF 公告...'):
        dividend_alerts = check_dividend_alerts(df['標的代碼'].tolist())
    
    if not dividend_alerts.empty:
        st.success(f"📢 偵測到 {len(dividend_alerts)} 筆公告！")
        st.dataframe(dividend_alerts, use_container_width=True)
    else:
        st.write("✨ 目前 47 檔持股暫無最新公告。")

    st.subheader("📊 資產配置分布")
    fig = px.pie(df, values='市值', names='資產類別', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📑 詳細持股清單")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)
# --- 🔍 投資決策輔助 (標的篩選與買賣點) ---
st.write("---")
st.subheader("🔍 投資決策輔助 (技術面偵測)")

def get_signals(stock_code):
    t_code = f"{stock_code}.TW" if len(stock_code) <= 4 and stock_code.isdigit() else f"{stock_code}.TWO"
    data = yf.download(t_code, period="60d", interval="1d", progress=False)
    
    if data.empty: return "資料不足"
    
    # 計算 20日均線 (MA20) 與 RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    current_price = data['Close'].iloc[-1]
    ma20 = data['Close'].rolling(window=20).mean().iloc[-1]
    
    # 簡單判斷邏輯
    if rsi.iloc[-1] < 30:
        return "🔥 超跌 (建議關注買點)"
    elif rsi.iloc[-1] > 70:
        return "⚠️ 超漲 (建議減碼)"
    elif current_price > ma20:
        return "📈 多頭趨勢"
    else:
        return "☁️ 整理中"

# 執行偵測
if st.button("🚀 開始掃描持股買賣信號"):
    results = []
    for code in df['標的代碼'].tolist()[:10]: # 先測試前 10 檔，避免跑太久
        signal = get_signals(code)
        results.append({"標的": code, "技術信號": signal})
    st.table(pd.DataFrame(results))
except Exception as e:
    st.error(f"發生預期外錯誤: {e}")
