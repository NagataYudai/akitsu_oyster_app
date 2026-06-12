import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ページの基本設定
st.set_page_config(page_title="安芸津牡蠣養殖リスク予測", layout="wide")

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
    df_2023 = df[df['year'] == 2023].copy()
    
    df_2026 = df[df['year'] == 2026]
    
    if not df_2026.empty:
        valid_dates = df_2026['date'].dropna()
        if not valid_dates.empty:
            latest_date = valid_dates.max().date()
        else:
            latest_date = pd.to_datetime("2026-07-01").date()
    else:
        latest_date = pd.to_datetime("2026-07-01").date()

    # タイトルと更新日の表示
    st.title("🦪 安芸津牡蠣養殖：2026年環境監視プロトタイプ")
    st.write("過去（2025年）の災害級へい死データと比較して、現在のリスクを判定します。")
    st.info(f"📢 **{latest_date.year}年{latest_date.month}月{latest_date.day}日 更新！**")

    # ==========================================
    # 💡 観測地点の表示（インタラクティブマップ）
    # ==========================================
    st.markdown("📍 **観測地点：三協化成沖** （CTDサンプリング地点）")
    
    # 自動で表示されるインタラクティブマップ（OpenStreetMapを利用・規約クリア）
    map_data = pd.DataFrame({
        'lat': [34.30914828361069],
        'lon': [132.81821499692464]
    })
    # zoomの数値（13）は、数値を大きくするとより拡大された地図になります
    st.map(map_data, zoom=13)

    st.divider() # 区切り線を引いてスッキリさせる

    # 2. サイドバーでの入力
    st.sidebar.header("📡 観測値を入力")
    
    st.sidebar.info(
        "💡 **アプリの使い方**\n"
        "- **初期表示:** 最初に表示されている数値は、システムに登録されている**最新のデータ**です。\n"
        "- **過去を振り返る:** カレンダーの「観測日」を変更すると、過去のデータを呼び出して当時の状況を確認できます。\n"
        "- **自分の漁場と比較する:** ご自身で測った数値を下の枠に直接入力（書き換え）することで、自分の漁場のデータで危険度を判定・比較できます。"
    )
    
    input_date = st.sidebar.date_input("観測日", value=latest_date)
    
    # 選択された「年」を取得
    selected_year = input_date.year
    df_selected_year = df[df['year'] == selected_year]
    
    # 週番号の計算
    exact_match = df_selected_year[df_selected_year['date'].dt.date == input_date]
    if not exact_match.empty:
        input_week = int(exact_match['week_num'].values[0])
    else:
        input_week = input_date.isocalendar()[1]
        
    st.sidebar.markdown(f"**{selected_year}年 第 {input_week} 週**")

    # 選んだ「年」の同じ週のデータを探す
    week_match = df_selected_year[df_selected_year['week_num'] == input_week]

    if not week_match.empty:
        target_data = week_match.iloc[0]
    elif not df_selected_year.empty:
        target_data = df_selected_year.sort_values('week_num', ascending=False).iloc[0]
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
    def_precip = get_val(target_data, 'precip_sum_july', 0.0)
    def_temp_sum_0m = get_val(target_data, 'temp_sum_0m', 2000.0)
    def_temp_sum_5m = get_val(target_data, 'temp_sum_5m', 1900.0)

    st.sidebar.subheader("海洋環境データ")
    input_temp_0m = st.sidebar.number_input("観測日の0m水温 ℃", value=def_temp_0m, step=0.1)
    input_temp = st.sidebar.number_input("観測日の5m水温 ℃", value=def_temp_5m, step=0.1)
    input_sal_0m = st.sidebar.number_input("観測日の0m塩分", value=def_sal_0m, step=0.1)
    input_sal_5m = st.sidebar.number_input("観測日の5m塩分", value=def_sal_5m, step=0.1)
    input_chl_0m = st.sidebar.number_input("観測日の0mクロロフィル", value=def_chl_0m, step=0.1)
    input_chl = st.sidebar.number_input("観測日の5mクロロフィル", value=def_chl_5m, step=0.1)
    input_do_0m = st.sidebar.number_input("観測日の0m溶存酸素 mg/L", value=def_do_0m, step=0.1)
    input_do_5m = st.sidebar.number_input("観測日の5m溶存酸素 mg/L", value=def_do_5m, step=0.1)
    input_temp_sum_0m = st.sidebar.number_input("観測日の0m積算水温 ℃", value=def_temp_sum_0m, step=10.0)
    input_temp_sum_5m = st.sidebar.number_input("観測日の5m積算水温 ℃", value=def_temp_sum_5m, step=10.0)
    
    st.sidebar.subheader("気象データ")
    input_precip_day = st.sidebar.number_input("直近1週間の降水量 (mm)", value=def_precip_day, step=1.0)
    input_precip = st.sidebar.number_input("7月の累計降水量 (mm)", value=def_precip, step=1.0)

    # 3. リスク判定ロジック
    st.subheader("⚠️ リスク判定結果")
    
    ref_2025 = df_2025[df_2025['week_num'] == input_week]
    ref_2024 = df_2024[df_2024['week_num'] == input_week] 
    ref_2023 = df_2023[df_2023['week_num'] == input_week]
    
    star_date = pd.to_datetime(f"2024-{input_date.month:02d}-{input_date.day:02d}")
    
    if not ref_2025.empty:
        ref_temp_2025 = ref_2025['temp_5m'].values[0]
        ref_temp_2024 = ref_2024['temp_5m'].values[0] if not ref_2024.empty else 99.0
        ref_temp_2023 = ref_2023['temp_5m'].values[0] if not ref_2023.empty else 99.0
        
        str_temp_2024 = f"{ref_temp_2024}℃" if ref_temp_2024 != 99.0 else "データなし"
        str_temp_2023 = f"{ref_temp_2023}℃" if ref_temp_2023 != 99.0 else "データなし"
        
        score = 0
        reasons = []

        # 判定A: 水温
        is_over_2025 = (input_temp >= ref_temp_2025)
        is_over_2024 = (input_temp >= ref_temp_2024)

        if is_over_2025:
            score += 2
            reasons.append(f"水深5mの水温が2025年同期（{ref_temp_2025}℃）を上回るペースで推移しており、今後のさらなる水温上昇に警戒が必要です。")
        elif is_over_2024:
            score += 2
            reasons.append(f"水深5mの水温が2024年同期（{str_temp_2024}）を上回るペースで推移しており、今後のさらなる水温上昇に警戒が必要です。")
        elif input_temp >= 28.0:
            score += 2
            reasons.append(f"水温が28℃以上（{input_temp}℃）であり、極めて危険な熱ストレス圏内です。")
        elif input_temp > ref_temp_2023 and ref_temp_2023 != 99.0:
            score += 1
            reasons.append(f"水深5mの水温が2023年同期（{str_temp_2023}）を上回って推移しており、やや高めの状態です。")
        elif input_temp >= 27.0:
            score += 1
            reasons.append(f"水温が27℃以上（{input_temp}℃）であり、熱ストレスに警戒が必要です。")
        else:
            reasons.append("水深5mの水温は過去と比較して平年並み、または低い状態です。")

        # 判定B: 降水量
        if input_precip == 0.0:
            reasons.append("7月の降水量は未観測（または時期前）のため、リスク判定から除外しています。")
        elif input_precip < 100:
            score += 2
            reasons.append(f"7月の降水量が100mm未満（{input_precip}mm）の少雨であり、高塩分・貧栄養の深刻なリスクがあります。")
        elif input_precip < 200:
            score += 1
            reasons.append(f"7月の降水量が200mm未満（{input_precip}mm）であり、環境悪化の兆候に注意が必要です。")
        else:
            reasons.append(f"7月の降水量は200mm以上（{input_precip}mm）あり、十分な雨が降っています。")

        # 判定C: クロロフィル
        if input_chl < 1.0:
            score += 2
            reasons.append("クロロフィルが非常に低く（1.0未満）、牡蠣が餌不足に陥っています。")
        elif input_chl < 2.0:
            score += 1
            reasons.append("クロロフィルがやや低め（2.0未満）で、牡蠣が餌不足に陥るリスクがあります。")
        else:
            reasons.append("クロロフィルは十分（2.0以上）あり、牡蠣の餌環境は良好です。")

        # 判定D: 溶存酸素の低下リスク
        if input_do_5m < 4.0:
            score += 5
            reasons.append("水深5mの溶存酸素が非常に低く（4mg/L未満）、貧酸素による致命的なダメージを受けるリスクがあります。")
        elif input_do_5m < 5.0:
            score += 1
            reasons.append("水深5mの溶存酸素が低下しており（5mg/L未満）、環境ストレスがかかりやすい状態です。")
        else:
            reasons.append("溶存酸素は十分（5mg/L以上）であり、貧酸素の危険性は低いです。")

        # 判定E: 塩分の上昇リスク
        if input_sal_5m >= 33.0:
            score += 1
            reasons.append(f"塩分が33以上（{input_sal_5m}）と高くなっており、環境ストレスの要因となる可能性があります。")
        else:
            reasons.append(f"塩分は正常な範囲内（{input_sal_5m}）です。")
        
        # 結果の表示
        if score >= 5:
            st.error(f"### 🔴 【危険：赤】リスクスコア: {score}")
            st.caption("※スコア凡例：[🔴危険: 5点以上] [🟡警戒: 3〜4点] [🟢安全: 2点以下]")
            st.write("**判定：大量へい死の危険性が極めて高い状態です。**")
            for r in reasons:
                st.write(f"- {r}")
            
        elif score >= 3:
            st.warning(f"### 🟡 【警戒：黄】リスクスコア: {score}")
            st.caption("※スコア凡例：[🔴危険: 5点以上] [🟡警戒: 3〜4点] [🟢安全: 2点以下]")
            st.write("**判定：環境が悪化しつつあります。今後の予報に注意してください。**")
            for r in reasons:
                st.write(f"- {r}")
            
        else:
            st.success(f"### 🟢 【安全：緑】リスクスコア: {score}") 
            st.caption("※スコア凡例：[🔴危険: 5点以上] [🟡警戒: 3〜4点] [🟢安全: 2点以下]")
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
            {"title": "水深 0m 溶存酸素", "col": "do_0m", "y_label": "溶存酸素 (mg/L)", "unit": " mg/L", "input": input_do_0m, "type": "line"},
            {"title": "水深 5m 溶存酸素", "col": "do_5m", "y_label": "溶存酸素 (mg/L)", "unit": " mg/L", "input": input_do_5m, "type": "line"},
            {"title": "水深 0m 積算水温", "col": "temp_sum_0m", "y_label": "積算水温 (℃)", "unit": " ℃", "input": input_temp_sum_0m, "type": "line"},
            {"title": "水深 5m 積算水温", "col": "temp_sum_5m", "y_label": "積算水温 (℃)", "unit": " ℃", "input": input_temp_sum_5m, "type": "line"},
            {"title": "直近1週間の降水量", "col": "precip_mm_day", "y_label": "降水量 (mm)", "unit": " mm", "input": input_precip_day, "type": "line"},
            {"title": "7月の合計降水量", "col": "precip_sum_july", "y_label": "降水量 (mm)", "unit": " mm", "input": input_precip, "type": "bar"},
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
                    x=[f"{selected_year}年"], 
                    y=[g['input']], 
                    name="観測日の値", 
                    marker=star_marker, 
                    mode="markers",
                    hovertemplate=f'観測日: %{{y}}{g["unit"]}'
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
                        line_width = 4 if year == selected_year else 2
                        
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
                    name="観測日の値", 
                    marker=star_marker, 
                    mode="markers", 
                    hovertemplate=f'観測日: %{{y}}{g["unit"]}'
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
