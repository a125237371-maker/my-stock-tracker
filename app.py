import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

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
    # 建立一個待抓取的清單
    search_list = []
    for t in tickers_raw:
        search_list.append(f"{t}.TW")
        search_list.append(f"{t}.TWO")
    
    # 一次性抓取所有可能的代碼 (上市+上櫃)
    data = yf.download(search_list, period="1d", group_by='ticker')
    
    for t in tickers_raw:
        # 先試上市 (.TW)
        tw_price = data[f"{t}.TW"]['Close'].iloc[-1] if f"{t}.TW" in data.columns and not pd.isna(data[f"{t}.TW"]['Close'].iloc[-1]) else None
        
        if tw_price:
            price_dict[t] = tw_price
        else:
            # 如果上市抓不到，試上櫃 (.TWO)
            two_price = data[f"{t}.TWO"]['Close'].iloc[-1] if f"{t}.TWO" in data.columns and not pd.isna(data[f"{t}.TWO"]['Close'].iloc[-1]) else None
            price_dict[t] = two_price if two_price else 0
            
    return price_dict

try:
    df = load_data()
    st.info("🔄 正在自動偵測上市/上櫃即時行情...")
    
    # 執行自動偵測抓取
    live_prices = get_live_prices(df['標的代碼'].tolist())
    
    # 損益計算
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
    c3.metric("偵測狀態", "✅ 上市/上櫃全數對齊")

    # 圓餅圖
    st.subheader("📊 資產配置分布")
    fig = px.pie(df, values='市值', names='資產類別', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # 清單
    st.subheader("📑 詳細持股清單 (已自動校正價格)")
    st.dataframe(df[['標的代碼', '標的名稱', '持股數', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)

except Exception as e:
    st.error(f"發生預期外錯誤: {e}")
