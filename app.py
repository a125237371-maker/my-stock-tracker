import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="賺大錢V1：分頁測試版", layout="wide")
st.title("💰 賺大錢V1：分頁功能測試")

# 2. 定義頁籤 (分頁切換)
tab1, tab2 = st.tabs(["📊 資產監控 (待填入)", "🎯 戰術實驗區 (空白)"])

# 3. 讀取 Google Sheet 數據 (這是兩邊共用的資料源)
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

# --- 第一頁：準備填入您找回來的「穩定版」代碼 ---
with tab1:
    st.header("第一分頁：資產看板")
    df = load_data()
    
    if not df.empty:
        st.success(f"✅ 資料載入成功！共 {len(df)} 檔標的。")
        st.write("請將您找回來的穩定版「價格抓取」與「表格顯示」代碼貼在這一區。")
        
        # 暫時用最簡單的表格顯示資料，確認資料有進來
        st.dataframe(df.head(), use_container_width=True)
    else:
        st.warning("目前讀不到 Google Sheet 資料，請檢查連結。")

# --- 第二頁：完全空白，不放任何代碼 ---
with tab2:
    st.header("第二分頁：新功能開發")
    st.write("這裡是空白區，目前沒有任何代碼，不會干擾第一頁。")
