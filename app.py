import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ページの基本設定
st.set_page_config(page_title="安芸津牡蠣養殖リスク予測", layout="wide")

st.title("🦪 安芸津牡蠣養殖：2026年環境監視プロトタイプ")
st.write("過去（2025年）の災害級へい死データと比較して、現在のリスクを判定します。")

# 1. データの読み込み
@st.cache_data
def load_data():
    df = pd.read_csv('oyster_akitsu.csv')
    df['date'] = pd.to_datetime(df['date'])
    return df

try:
    df = load_data()
    df_2025 = df[df['year'] == 2025].copy()
    
    # 2. サイドバーでの入力（2026年の最新観測値を想定）
    st.sidebar.header("📡 最新の観測値を入力")
    input_week = st.sidebar.slider("現在の週番号 (week_num)", 1, 52, 30)
    input_temp_0m = st.sidebar.number_input("現在の0m水温 (temp_0m) ℃", value=28.0, step=0.1)
    input_temp = st.sidebar.number_input("現在の5m水温 (temp_5m) ℃", value=27.0, step=0.1)
    input_chl = st.sidebar.number_input("現在の5mクロロフィル (chl_5m)", value=1.5, step=0.1)
    input_precip = st.sidebar.number_input("7月の累計降水量 (mm)", value=150.0, step=1.0)

    # 3. リスク判定ロジック
    st.subheader("⚠️ リスク判定結果")
    
    # 2025年の同週データを取得
    ref_2025 = df_2025[df_2025['week_num'] == input_week]
    
    if not ref_2025.empty:
        ref_temp = ref_2025['temp_5m'].values[0]
        ref_precip = 64.0  # 2025年の7月累計降水量(実績値)
        
        score = 0
        reasons = []

        # 判定A: 水温（2025年超え、または28.5度以上）
        if input_temp >= ref_temp:
            score += 3
            reasons.append(f"水温が2025年同期（{ref_temp}℃）を超えています。")
        elif input_temp >= 28.5:
            score += 2
            reasons.append("水温が28.5℃を超え、熱ストレス圏内です。")

        # 判定B: 降水量（2025年並みの少雨）
        if input_precip <= ref_precip:
            score += 3
            reasons.append(f"7月の降水量が2025年（{ref_precip}mm）と同等以下の深刻な少雨です。")
        elif input_precip <= 100:
            score += 1
            reasons.append("7月の降水量が少なく、高塩分・貧栄養のリスクがあります。")

        # 判定C: クロロフィル（栄養不足）
        if input_chl < 1.0:
            score += 1
            reasons.append("クロロフィルが低く、牡蠣の体力が低下しやすい状態です。")

        # 結果の表示
        if score >= 5:
            st.error(f"### 【危険：赤】リスクスコア: {score}")
            st.write("**判定：2025年の大量へい死パターンと酷似しています。**")
            st.write("👉 対策案：筏を深場へ移動、または人工湧昇装置（SPALOW等）の稼働を最大化してください。")
        elif score >= 2:
            st.warning(f"### 【警戒：黄】リスクスコア: {score}")
            st.write("**判定：環境が悪化しつつあります。今後の予報に注意してください。**")
            st.write("👉 対策案：毎日の貝の観察を強化し、早めの水揚げ準備を検討してください。")
        else:
            st.success(f"### 【安全：青】リスクスコア: {score}")
            st.write("**判定：平年並みの環境です。**")

       # 4. 可視化（グラフ表示）
        st.divider()
        # --- 0m水温グラフの作成 ---
        st.subheader("📈 年度別の水温推移比較 (水深 0m)")
        
        color_map = {2025: "red", 2024: "green", 2023: "blue"}
        fig0 = go.Figure()

        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year]
            line_color = color_map.get(year, "gray")
            line_width = 4 if year == 2025 else 2
            
            fig0.add_trace(go.Scatter(
                x=year_data['week_num'], 
                y=year_data['temp_0m'], 
                name=f"{year}年",
                line=dict(color=line_color, width=line_width),
                mode='lines+markers',
                # x unified を使う場合、ポップアップ内の各行の表示形式を指定します
                hovertemplate='%{y}℃' 
            ))
        
        # 現在の入力値をプロット
        fig0.add_trace(go.Scatter(
            x=[input_week], 
            y=[input_temp_0m], 
            name="現在の0m入力値", 
            marker=dict(size=18, color="black", symbol="star"),
            hovertemplate='現在: %{y}℃'
        ))

        fig0.update_layout(
            xaxis_title="週番号", 
            yaxis_title="水温 (℃)", 
            hovermode="x unified", # 👈 これを追加することで一括表示になります
            height=400,
            legend_title="凡例"
        )
        st.plotly_chart(fig0, use_container_width=True)
        
        st.subheader("📈 年度別の水温推移比較 (水深 5m)")
        
        # 年ごとの色を指定する辞書（カラーマップ）
        color_map = {
            2025: "red",   # 災害級の年
            2024: "green", # 比較用の年
            2023: "blue"   # 比較用の年
        }
        
        fig = go.Figure()

        # 年代順に並べて表示するためにソート
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year]
            
            # 指定した色を取得。設定がない年はグレーにする
            line_color = color_map.get(year, "gray")
            
            # 2025年だけ線を太くして強調する
            line_width = 4 if year == 2025 else 2
            
            fig.add_trace(go.Scatter(
                x=year_data['week_num'], 
                y=year_data['temp_5m'], 
                name=f"{year}年",
                line=dict(color=line_color, width=line_width),
                mode='lines+markers',
                hovertemplate='%{x}週: %{y}℃'
            ))
        
        # 現在の入力値を「★」マークでプロット
        fig.add_trace(go.Scatter(
            x=[input_week], 
            y=[input_temp], 
            name="現在の入力値", 
            marker=dict(size=18, color="black", symbol="star"),
            hovertemplate='現在: %{y}℃'
        ))

        fig.update_layout(
            xaxis_title="週番号 (Week Number)", 
            yaxis_title="水温 (℃)",
            legend_title="凡例", 
            hovermode="x unified",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("選択された週番号の2025年データが存在しません。")

except FileNotFoundError:
    st.error("エラー: `oyster_akitsu.csv` が見つかりません。ファイル名を確認してください。")
