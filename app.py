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
    search_list = []
    for t in tickers_raw:
        # 自動識別債券 ETF 或特殊代碼，優先放進清單
        search_list.append(f"{t}.TW")
        search_list.append(f"{t}.TWO")
    
    # 增加 progress=False 讓介面更乾淨
    data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
    
    for t in tickers_raw:
        # 修正多重索引抓取邏輯
        try:
            tw_data = data[f"{t}.TW"]
            tw_price = tw_data['Close'].iloc[-1] if not tw_data['Close'].empty else None
            
            if pd.notna(tw_price):
                price_dict[t] = tw_price
            else:
                two_data = data[f"{t}.TWO"]
                two_price = two_data['Close'].iloc[-1] if not two_data['Close'].empty else None
                price_dict[t] = two_price if pd.notna(two_price) else 0
        except:
            price_dict[t] = 0
            
    return price_dict

try:
    df = load_data()
    st.info("🔄 正在自動同步上市/上櫃即時行情...")
    
    live_prices = get_live_prices(df['標的代碼'].tolist())
    
    df['現價'] = df['標的代碼'].map(live_prices)
    df['市值'] = df['現價'] * df['持股數']
    df['成本'] = df['成交均價'] * df['持股數']
    df['未實現損益'] = df['市值'] - df['成本']
    df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

    total_mkt = df['市值'].sum()
    total_cost = df['成本'].sum()
    total_profit = total_mkt - total_cost

    c1, c2, c3 = st.columns(3)
    c1.metric("總資產市值", f"${total_mkt:,.0f}")
    c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/total_cost*100):.2f}%")
    c3.metric("偵測狀態", f"✅ 已同步 {len(df)} 檔標的")

    st.subheader("📊 資產配置分布")
    fig = px.pie(df, values='市值', names='資產類別', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📑 詳細持股清單")
    # 增加排序，讓損益最高的排在前面，一眼看到誰在賺錢
    st.dataframe(df.sort_values("未實現損益", ascending=False)[['標的代碼', '標的名稱', '持股數', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)

except Exception as e:
    st.error(f"發生預期外錯誤: {e}")
