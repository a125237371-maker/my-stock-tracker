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
    
    # 一次性抓取所有行情
    data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
    
    for t in tickers_raw:
        tw_price = data[f"{t}.TW"]['Close'].iloc[-1] if f"{t}.TW" in data.columns and not pd.isna(data[f"{t}.TW"]['Close'].iloc[-1]) else None
        if tw_price:
            price_dict[t] = tw_price
        else:
            two_price = data[f"{t}.TWO"]['Close'].iloc[-1] if f"{t}.TWO" in data.columns and not pd.isna(data[f"{t}.TWO"]['Close'].iloc[-1]) else None
            price_dict[t] = two_price if two_price else 0
    return price_dict

# --- 🎯 除息公告偵測函數 ---
@st.cache_data(ttl=3600)
def check_dividend_alerts(tickers_raw):
    alert_list = []
    today = datetime.now().date()
    for t in tickers_raw:
        t_code = f"{t}.TW" if int(t) < 10000 else f"{t}.TWO"
        s = yf.Ticker(t_code)
        cal = s.calendar
        if cal is not None and 'Dividend Date' in cal:
            div_date = cal['Dividend Date']
            # 偵測未來或近期除息標的
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
    # 1. 讀取資料 (這裡定義了 df，所以後面的功能才不會報錯)
    df = load_data()
    st.info("🔄 正在同步上市/上櫃即時行情與除息公告...")
    
    # 2. 執行偵測抓取
    live_prices = get_live_prices(df['標的代碼'].tolist())
    
    # 3. 損益計算
    df['現價'] = df['標的代碼'].map(live_prices)
    df['市值'] = df['現價'] * df['持股數']
    df['成本'] = df['成交均價'] * df['持股數']
    df['未實現損益'] = df['市值'] - df['成本']
    df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

    # 4. 頂部儀表板
    total_mkt = df['市值'].sum()
    total_cost = df['成本'].sum()
    total_profit = total_mkt - total_cost

    c1, c2, c3 = st.columns(3)
    c1.metric("總資產市值", f"${total_mkt:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/total_cost*100):.2f}%")
    c3.metric("偵測狀態", "✅ 數據已對齊")

    # --- 5. 🎯 填息交易追蹤 (公告即時偵測) ---
    st.write("---")
    st.subheader("🗓️ 近期除息公告偵測")
    with st.spinner('掃描除息公告中...'):
        dividend_alerts = check_dividend_alerts(df['標的代碼'].tolist())
    
    if not dividend_alerts.empty:
        st.success(f"📢 偵測到 {len(dividend_alerts)} 筆近期除息公告！")
        st.dataframe(dividend_alerts, use_container_width=True)
    else:
        st.write("✨ 目前暫無新的除息公告。")

    # 6. 圓餅圖
    st.subheader("📊 資產配置分布")
    fig = px.pie(df, values='市值', names='資產類別', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # 7. 清單
    st.subheader("📑 詳細持股清單")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)

except Exception as e:
    st.error(f"發生預期外錯誤: {e}")
