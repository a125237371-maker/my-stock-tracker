import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="賺大錢V1：雙分頁戰術看板", layout="wide")
st.title("💰 賺大錢V1：資產與戰術看板")

# 2. 定義頁籤 (分頁切換)
tab1, tab2 = st.tabs(["📊 資產監控 (穩定版)", "🎯 戰術實驗區 (空白)"])

# 3. 讀取數據 (資料源共用)
raw_url = "https://docs.google.com/spreadsheets/d/187zWkatewIxuR6ojgss40nP2WWz1gL8D4Gu1zISgp6M/export?format=csv"

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(raw_url)
        df['標的代碼'] = df['標的代碼'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

# --- 第一頁：資產監控 (放入您最穩定的那一版邏輯) ---
with tab1:
    df_raw = load_data()
    if not df_raw.empty:
        st.info("🔄 正在同步 47 檔標的行情...")
        
        # 穩定版行情抓取邏輯
        def get_live_prices(tickers_raw):
            search_list = []
            for t in tickers_raw:
                search_list.append(f"{t}.TW")
                search_list.append(f"{t}.TWO")
            
            # 抓取數據
            data = yf.download(search_list, period="1d", group_by='ticker', progress=False)
            
            price_dict = {}
            for t in tickers_raw:
                try:
                    # 優先檢查 .TW
                    tw_p = data[f"{t}.TW"]['Close'].iloc[-1] if f"{t}.TW" in data.columns else None
                    if pd.notna(tw_p):
                        price_dict[t] = tw_p
                    else:
                        # 抓不到則檢查 .TWO
                        two_p = data[f"{t}.TWO"]['Close'].iloc[-1] if f"{t}.TWO" in data.columns else None
                        price_dict[t] = two_p if pd.notna(two_p) else 0
                except:
                    price_dict[t] = 0
            return price_dict

        live_prices = get_live_prices(df_raw['標的代碼'].tolist())
        
        # 計算數據
        df = df_raw.copy()
        df['現價'] = df['標的代碼'].map(live_prices)
        df['市值'] = df['現價'] * df['持股數']
        df['成本'] = df['成交均價'] * df['持股數']
        df['未實現損益'] = df['市值'] - df['成本']
        df['報酬率(%)'] = (df['未實現損益'] / df['成本'] * 100).round(2)

        # 儀表板
        c1, c2, c3 = st.columns(3)
        total_mkt = df['市值'].sum()
        total_profit = df['未實現損益'].sum()
        c1.metric("總資產市值", f"${total_mkt:,.0f}")
        c2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{(total_profit/df['成本'].sum()*100):.2f}%")
        c3.success("✅ 行情同步成功")

        # 圖表與清單
        st.subheader("📊 資產配置與清單")
        st.plotly_chart(px.pie(df, values='市值', names='資產類別', hole=0.4), use_container_width=True)
        st.dataframe(df[['標的代碼', '標的名稱', '現價', '未實現損益', '報酬率(%)', '資產類別']], use_container_width=True)
    else:
        st.warning("等待資料源載入中...")

# --- 第二頁：新飆股偵測雷達 (全市場掃描) ---
with tab2:
    st.header("🚀 新飆股偵測雷達")
    st.caption("目標：從市場熱門股中，篩選出『量能爆發、起漲初步、10MA 乖離適中』的標的。")
    
    # 定義掃描池：0050 + 0051 (台灣最具代表性的 150 檔中大型標的)
    # 這是發現「有質量的飆股」最有效率的池子
    @st.cache_data(ttl=3600)
    def get_market_watchlist():
        # 這裡列出部分熱門觀察名單，可依需求擴充
        hot_tech = ["2330", "2317", "2454", "2382", "3231", "2451", "3034", "6669", "2308", "2357"] # AI/電子
        hot_cpo = ["4908", "3363", "4979", "3163", "6442"] # CPO/光通訊
        hot_mid = ["2603", "2609", "2618", "2610", "1605", "1513", "1519", "1503"] # 航運/重電
        return list(set(hot_tech + hot_cpo + hot_mid))

    if st.button("🔥 執行全市場熱門股掃描 (波若威模式)"):
        watchlist = get_market_watchlist()
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, code in enumerate(watchlist):
            status_text.text(f"正在掃描潛在飆股 ({i+1}/{len(watchlist)}): {code}...")
            full_t = get_real_ticker(code)
            try:
                # 抓取 20 天數據
                hist = yf.download(full_t, period="20d", progress=False)
                if len(hist) > 10:
                    if isinstance(hist.columns, pd.MultiIndex):
                        hist.columns = hist.columns.get_level_values(0)
                    
                    curr_p = float(hist['Close'].iloc[-1])
                    prev_p = float(hist['Close'].iloc[-2])
                    curr_vol = int(hist['Volume'].iloc[-1])
                    avg_vol = int(hist['Volume'].tail(5).mean())
                    ma10 = float(hist['Close'].rolling(window=10).mean().iloc[-1])
                    
                    change_pct = ((curr_p - prev_p) / prev_p) * 100
                    vol_ratio = curr_vol / avg_vol
                    bias_10ma = ((curr_p - ma10) / ma10) * 100
                    
                    # --- 核心篩選邏輯：波若威模式 ---
                    # 1. 量能倍數 > 2 (主力介入)
                    # 2. 漲幅 > 3% (發動中)
                    # 3. 10MA 乖離 < 12% (避免追在最高點)
                    
                    is_hot = vol_ratio > 2 and change_pct > 3 and bias_10ma < 12
                    
                    if is_hot:
                        results.append({
                            "代碼": code,
                            "漲跌幅%": round(change_pct, 2),
                            "量能倍數": round(vol_ratio, 2),
                            "10MA乖離%": round(bias_10ma, 2),
                            "今日成交量": curr_vol,
                            "關鍵防守(紅K低)": round(hist['Low'].iloc[-1], 2)
                        })
            except:
                pass
            progress_bar.progress((i + 1) / len(watchlist))
            
        status_text.text("✅ 掃描完成！")
        
        if results:
            scan_df = pd.DataFrame(results)
            st.success(f"🚩 偵測到 {len(scan_df)} 檔符合「波若威起漲模式」的潛在飆股！")
            st.dataframe(scan_df.sort_values("量能倍數", ascending=False), use_container_width=True)
            
            # 視覺化：畫出乖離率 vs 量能倍數的分佈
            st.write("---")
            st.subheader("📍 潛在標的分布 (找左上角的：量大且乖離小)")
            fig = px.scatter(scan_df, x="10MA乖離%", y="量能倍數", text="代碼", size="漲跌幅%", 
                             color="量能倍數", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("目前熱門股中，暫無標的符合「波若威模式」(量增2倍+乖離小)。這代表市場目前可能處於縮量整理期。")

    st.write("---")
    st.subheader("🕵️ 如何判斷這是不是新飆股？")
    st.markdown("""
    1. **看量能倍數**：越高越好，代表主力剛進場。
    2. **看 10MA 乖離**：數值在 **3% - 8%** 之間最理想，這是剛發動的黃金位置。
    3. **看族群性**：如果掃出來的標的很多都屬於同一個族群（例如都是光通訊），那機率更高！
    """)
