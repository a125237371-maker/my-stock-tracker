import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="賺大錢V1 - 績效追蹤版", layout="wide")
st.title("📈 賺大錢V1：資產成長與績效追蹤")

# Google Sheet 網址 (維持不變)
sheet_base = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_all_data():
    # 讀取第一個分頁 (持股)
    df_portfolio = pd.read_csv(sheet_base)
    # 嘗試讀取 History 分頁 (這裡假設 History 是第二個分頁，gid=... 是分頁 ID)
    # 註：如果不知道 gid，最簡單是另開一個網址讀取
    history_url = sheet_base + "&gid=您的History分頁ID" # 這裡您可以先用簡單的範例數據
    return df_portfolio

try:
    df = load_all_data()
    # (中間抓取即時價格的邏輯維持跟上次一樣...)
    
    # --- 新增：績效累積區塊 ---
    st.subheader("🚀 資產成長曲線 (Equity Curve)")
    
    # 這裡我們先建立一個模擬的歷史數據，等您在 Sheet 填好後我們再對接
    history_data = {
        '日期': ['2026-01-01', '2026-01-15', '2026-02-01', '2026-02-18'],
        '總市值': [8000000, 8350000, 8700000, 9058660],
        '總投入成本': [7200000, 7250000, 7500000, 7644128]
    }
    history_df = pd.DataFrame(history_data)
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=history_df['日期'], y=history_df['總市值'], name='總市值', line=dict(color='gold', width=4)))
    fig_line.add_trace(go.Scatter(x=history_df['日期'], y=history_df['總投入成本'], name='投入成本', fill='tonexty', line=dict(dash='dash')))
    
    st.plotly_chart(fig_line, use_container_width=True)

    # --- 績效分析指標 ---
    st.subheader("🏆 績效總結")
    c1, c2, c3 = st.columns(3)
    c1.metric("歷史最高市值", f"${history_df['總市值'].max():,.0f}")
    c2.metric("資產成長率 (自年初)", f"{((9058660/8000000)-1)*100:.2f}%")
    c3.metric("目前總水位", f"${9058660:,.0f}")

except Exception as e:
    st.error(f"連線失敗: {e}")
