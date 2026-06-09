import streamlit as st
import pandas as pd
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
    df['plot_date'] = df['date'].apply(lambda d: d.replace(year=2024) if pd.notnull(d) else d)
    return df

try:
    df = load_data()
    df_2025 = df[df['year'] == 2025].copy()
    df_2024 = df[df['year'] == 2024].copy()
    
    # 2. サイドバーでの入力
    st.sidebar.header("📡 最新の観測値を入力")
    
    df_2026 = df[df['year'] == 2026]
    
    if not df_2026.empty:
        valid_dates = df_2026['date'].dropna()
        if not valid_dates.empty:
            latest_date = valid_dates.max().date()
        else:
            latest_date = pd.to_datetime("2026-07-01").date()
    else:
        latest_date = pd.to_datetime("2026-07-01").date()

    input_date = st.sidebar.date_input("現在の観測日", value=latest_date)
    
    exact_match = df_2026[df_2026['date'].dt.date == input_date]
    if not exact_match.empty:
        input_week = int(exact_match['week_num'].values[0])
    else:
        input_week = input_date.isocalendar()[1]
        
    st.sidebar.caption(f"※ 裏側のシステム判定用: 第 {input_week} 週")

    if not exact_match.empty:
        target_data = exact_match.iloc[0]
    elif not df_2026.empty:
        target_data = df_2026.sort_values('week_num', ascending=False).iloc[0]
    else:
        target_data = pd.Series(dtype=float)

    def get_val(data_row, col_name, default_val):
        if col_name in data_row and pd.notnull(data_row[col_name]):
            return float(data_row[col_name])
        return default_val

    def_temp_0m = get_val(target_data, 'temp_0m', 28.0)
    def_temp_5m = get_val(target_data, 'temp_5m', 27.0)
    def_sal_0m = get_val(target_data, 'sal_0m', 30.0)
    def_sal_5m = get_val(target_data, 'sal_5m', 31.0)
    def_do_0m = get_val(target_data, 'do_0m', 6.0)
    def_do_5m = get_val(target_data, 'do_5m', 5.0)
    def_chl_0m = get_val(target_data, 'chl_0m', 1.5)
    def_chl_5m = get_val(target_data, 'chl_5m', 1.5)
    def_precip_day = get_val(target_data, 'precip_mm_day', 0.0)
    def_precip = get_val(target_data, 'precip_sum_july', 150.0)
    def_air_avg = get_val(target_data, 'air_temp_avg', 28.0)
    def_air_month = get_val(target_data, 'air_temp_month', 26.0)

    st.sidebar.subheader("水温・塩分・DO・クロロフィル")
    input_temp_0m = st.sidebar.number_input("現在の0m水温 (temp_0m) ℃", value=def_temp_0m, step=0.1)
    input_temp = st.sidebar.number_input("現在の5m水温 (temp_5m) ℃", value=def_temp_5m, step=0.1)
    input_sal_0m = st.sidebar.number_input("現在の0m塩分 (sal_0m)", value=def_sal_0m, step=0.1)
    input_sal_5m = st.sidebar.number_input("現在の5m塩分 (sal_5m)", value=def_sal_5m, step=0.1)
    input_do_0m = st.sidebar.number_input("現在の0mDO (do_0m) mg/L", value=def_do_0m, step=0.1)
    input_do_5m = st.sidebar.number_input("現在の5mDO (do_5m) mg/L", value=def_do_5m, step=0.1)
    input_chl_0m = st.sidebar.number_input("現在の0mクロロフィル (chl_0m)", value=def_chl_0m, step=0.1)
    input_chl = st.sidebar.number_input("現在の5mクロロフィル (chl_5m)", value=def_chl_5m, step=0.1)
    
    st.sidebar.subheader("気象データ")
    input_precip_day = st.sidebar.number_input("直近1週間の降水量 (mm)", value=def_precip_day, step=1.0)
    input_precip = st.sidebar.number_input("7月の累計降水量 (mm)", value=def_precip, step=1.0)
    input_air_avg = st.sidebar.number_input("調査日の日平均気温 (℃)", value=def_air_avg, step=0.1)
    input_air_month = st.sidebar.number_input("月平均気温 (℃)", value=def_air_month, step=0.1)

    # 3. リスク判定ロジック
    st.subheader("⚠️ リスク判定結果")
    
    ref_2025 = df_2025[df_2025['week_num'] == input_week]
    ref_2024 = df_2024[df_2024['week_num'] == input_week] 
    
    star_date = pd.to_datetime(f"2024-{input_date.month:02d}-{input_date.day:02d}")
    
    if not ref_2025.empty:
        ref_temp_2025 = ref_2025['temp_5m'].values[0]
        ref_temp_2024 = ref_2024['temp_5m'].values[0] if not ref_2024.empty else -99.0
        
        score = 0
        reasons = []

        # 判定A: 水温
        if input_temp > ref_temp_2025:
            score += 2
            reasons.append(f"水深5mの水温が2025年同期（{ref_temp_2025}℃）を超えており、極めて危険な熱ストレス圏内です。")
        elif input_temp >= 28.0:
            score += 2
            reasons.append(f"水温が28℃以上（{input_temp}℃）であり、極めて危険な熱ストレス圏内です。")
        elif input_temp > ref_temp_2024:
            score += 1
            reasons.append(f"水深5mの水温が2024年同期（{ref_temp_2024}℃）を超えており、高めに推移しています。")
        elif input_temp >= 27.0:
            score += 1
            reasons.append(f"水温が27℃以上（{input_temp}℃）であり、熱ストレスに警戒が必要です。")
        else:
            reasons.append("水深5mの水温は過去と比較して平年並み、または低い状態です。")

        # 判定B: 降水量
        if input_precip < 100:
            score += 2
            reasons.append(f"7月の降水量が100mm未満（{input_precip}mm）の少雨であり、高塩分・貧栄養の深刻なリスクがあります。")
        elif input_precip < 200:
            score += 1
            reasons.append(f"7月の降水量が200mm未満（{input_precip}mm）であり、環境悪化の兆候に注意が必要です。")
        else:
            reasons.append(f"7月の降水量は200mm以上（{input_precip}mm）あり、平年並みの水準です。")

        # 判定C: クロロフィル
        if input_chl < 1.0:
            score += 2
            reasons.append("クロロフィルが非常に低く（1.0未満）、牡蠣が栄養不足に陥るリスクがあります。")
        elif input_chl < 2.0:
            score += 1
            reasons.append("クロロフィルがやや低め（2.0未満）で、牡蠣の体力が低下しやすい状態です。")
        else:
            reasons.append("クロロフィルは十分（2.0以上）あり、牡蠣の栄養状態は良好です。")

        # 判定D: DO（溶存酸素）の低下リスク
        if input_do_5m < 4.0:
            score += 5
            reasons.append("水深5mのDO（溶存酸素）が非常に低く（4mg/L未満）、貧酸素による致命的なダメージを受けるリスクがあります。")
        elif input_do_5m < 5.0:
            score += 1
            reasons.append("水深5mのDOが低下しており（5mg/L未満）、環境ストレスがかかりやすい状態です。")
        else:
            reasons.append("DOは十分（5mg/L以上）であり、貧酸素の危険性は低いです。")

        # 判定E: 塩分の上昇リスク
        if input_sal_5m >= 33.0:
            score += 1
            reasons.append(f"塩分が33以上（{input_sal_5m}）と高くなっており、環境ストレスの要因となる可能性があります。")
        else:
            reasons.append(f"塩分は正常な範囲内（{input_sal_5m}）です。")
        
        # ==========================================
        # 💡 結果の表示（閾値と色の調整）
        # ==========================================
        if score >= 5:
            st.error(f"### 【危険：赤】リスクスコア: {score}")
            st.write("**判定：大量へい死の危険性が極めて高い状態です。直ちに対策が必要です。**")
            for r in reasons:
                st.write(f"- {r}")
            st.write("👉 **対策案：直ちに牡蠣の状態を確認して下さい。筏を移動させてください。**")
            
        elif score >= 3: # 💡 3点以上に変更
            st.warning(f"### 【警戒：黄】リスクスコア: {score}")
            st.write("**判定：環境が悪化しつつあります。今後の予報に注意してください。**")
            for r in reasons:
                st.write(f"- {r}")
            st.write("👉 **対策案：カキの様子をこまめに観察してください。筏の移動を検討してください。**")
            
        else: # 💡 残り（2点以下）は緑へ変更
            st.success(f"### 【安全：緑】リスクスコア: {score}") 
            st.write("**判定：現在のところ平年並み、または安全な環境です。**")
            for r in reasons:
                st.write(f"- {r}")

        # 4. 可視化（グラフ表示の自動化）
        st.divider()
        st.header("📊 環境データの推移比較")
        
        color_map = {2026: "orange", 2025: "red", 2024: "yellowgreen", 2023: "cyan"}
        
        graphs_config = [
            {"title": "水深 0m 水温", "col": "temp_0m", "y_label": "水温 (℃)", "unit": "℃", "input": input_temp_0m, "type": "line"},
            {"title": "水深 5m 水温", "col": "temp_5m", "y_label": "水温 (℃)", "unit": "℃", "input": input_temp, "type": "line"},
            {"title": "水深 0m 塩分", "col": "sal_0m", "y_label": "塩分", "unit": "", "input": input_sal_0m, "type": "line"},
            {"title": "水深 5m 塩分", "col": "sal_5m", "y_label": "塩分", "unit": "", "input": input_sal_5m, "type": "line"},
            {"title": "水深 0m クロロフィル", "col": "chl_0m", "y_label": "クロロフィル (µg/L)", "unit": " µg/L", "input": input_chl_0m, "type": "line"},
            {"title": "水深 5m クロロフィル", "col": "chl_5m", "y_label": "クロロフィル (µg/L)", "unit": " µg/L", "input": input_chl, "type": "line"},
            {"title": "水深 0m DO（溶存酸素）", "col": "do_0m", "y_label": "DO (mg/L)", "unit": " mg/L", "input": input_do_0m, "type": "line"},
            {"title": "水深 5m DO（溶存酸素）", "col": "do_5m", "y_label": "DO (mg/L)", "unit": " mg/L", "input": input_do_5m, "type": "line"},
            {"title": "直近1週間の降水量", "col": "precip_mm_day", "y_label": "降水量 (mm)", "unit": " mm", "input": input_precip_day, "type": "line"},
            {"title": "7月の合計降水量", "col": "precip_sum_july", "y_label": "降水量 (mm)", "unit": " mm", "input": input_precip, "type": "bar"},
            {"title": "調査日の日平均気温", "col": "air_temp_avg", "y_label": "気温 (℃)", "unit": " ℃", "input": input_air_avg, "type": "line"},
            {"title": "月平均気温", "col": "air_temp_month", "y_label": "気温 (℃)", "unit": " ℃", "input": input_air_month, "type": "line"},
        ]

        tickvals = [f"2024-{m:02d}-01" for m in range(2, 11)]
        ticktext = [f"{m}月" for m in range(2, 11)]
        
        star_marker = dict(size=18, color="#FFD700", symbol="star", line=dict(color="black", width=1))

        for g in graphs_config:
            st.subheader(f"📈 {g['title']}")
            fig = go.Figure()
            
            graph_type = g.get("type", "line") 
            
            if graph_type == "bar":
                years_list = []
                values_list = []
                colors_list = []
                
                for year in sorted(df['year'].unique()):
                    year_data = df[df['year'] == year]
                    if g['col'] in year_data.columns:
                        valid_data = year_data[g['col']].dropna()
                        if not valid_data.empty:
                            years_list.append(f"{int(year)}年")
                            values_list.append(valid_data.values[0])
                            colors_list.append(color_map.get(year, "gray"))
                
                fig.add_trace(go.Bar(
                    x=years_list, 
                    y=values_list, 
                    marker_color=colors_list,
                    name="実績値",
                    hovertemplate=f'%{{y}}{g["unit"]}'
                ))
                
                fig.add_trace(go.Scatter(
                    x=["2026年"], 
                    y=[g['input']], 
                    name="現在の入力値", 
                    marker=star_marker, 
                    mode="markers",
                    hovertemplate=f'現在: %{{y}}{g["unit"]}'
                ))

                fig.update_layout(
                    xaxis_title="年",
                    yaxis_title=g['y_label'],
                    height=350,
                    showlegend=False, 
                    margin=dict(l=10, r=10, t=30, b=10)
                )

            else:
                for year in sorted(df['year'].unique()):
                    year_data = df[df['year'] == year]
                    
                    if g['col'] in year_data.columns:
                        line_color = color_map.get(year, "gray")
                        line_width = 4 if year == 2026 else 2
                        
                        fig.add_trace(go.Scatter(
                            x=year_data['plot_date'], 
                            y=year_data[g['col']], 
                            name=f"{int(year)}年", 
                            line=dict(color=line_color, width=line_width),
                            mode='lines+markers',
                            hovertemplate=f'%{{y}}{g["unit"]}',
                            connectgaps=True
                        ))
                
                fig.add_trace(go.Scatter(
                    x=[star_date], 
                    y=[g['input']], 
                    name="現在の入力値", 
                    marker=star_marker, 
                    mode="markers", 
                    hovertemplate=f'現在: %{{y}}{g["unit"]}'
                ))

                fig.update_layout(
                    xaxis=dict(
                        title="",
                        tickmode="array",
                        tickvals=tickvals,
                        ticktext=ticktext, 
                        range=["2024-02-01", "2024-10-31"],
                        hoverformat="%-m月%-d日" 
                    ),
                    yaxis_title=g['y_label'], 
                    hovermode="x unified",
                    height=350,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                    margin=dict(l=10, r=10, t=30, b=10)
                )

            st.plotly_chart(fig, use_container_width=True)
            st.divider()

    else:
        st.info("選択された日付に対応する2025年データが存在しません。")

except FileNotFoundError:
    st.error("エラー: `oyster_akitsu.csv` が見つかりません。ファイル名を確認してください。")
