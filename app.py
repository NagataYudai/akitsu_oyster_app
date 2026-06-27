import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk 

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
    st.title("🦪 安芸津牡蠣養殖 環境リスク監視システム")
    
    st.write("過去の環境推移から、現在のへい死リスクを判定します。")
    st.info(f"📢 **{latest_date.year}年{latest_date.month}月{latest_date.day}日 更新！**")
    
    st.info(
        "💡 **アプリの使い方**\n"
        "- **初期表示:** システムに登録されている最新のデータです。\n"
        "- **過去を振り返る:** 画面左上の「＞＞」マークをタップするとメニューが開きます。カレンダーの「観測日」を変更すると、過去のデータを呼び出して当時の状況を確認できます。\n"
        "- **自分の漁場と比較する:** ご自身で測った数値を直接入力することで自身の漁場の危険度を判定できます。"
    )

    st.divider()

    # 2. サイドバーでの入力
    st.sidebar.header("📡 観測値を入力")
    
    input_date = st.sidebar.date_input("観測日", value=latest_date)
    
    is_future_date = input_date > latest_date
    
    selected_year = input_date.year
    df_selected_year = df[df['year'] == selected_year]
    
    exact_match = df_selected_year[df_selected_year['date'].dt.date == input_date]
    if not exact_match.empty:
        input_week = int(exact_match['week_num'].values[0])
    else:
        input_week = input_date.isocalendar()[1]
        
    st.sidebar.markdown(f"**{selected_year}年 第 {input_week} 週**")

    week_match = df_selected_year[df_selected_year['week_num'] == input_week]

    if not week_match.empty:
        target_data = week_match.iloc[0]
    elif not df_selected_year.empty:
        target_data = df_selected_year.sort_values('week_num', ascending=False).iloc[0]
    else:
        target_data = pd.Series(dtype=float)

    is_off_season = (input_week <= 6) or (input_week >= 44)

    is_missing_week = False
    if not is_future_date and not is_off_season:
        if 'is_interpolated' in target_data and pd.notnull(target_data['is_interpolated']):
            if float(target_data['is_interpolated']) == 1.0:
                is_missing_week = True
        elif target_data.empty:
            is_missing_week = True

    if is_missing_week:
        st.sidebar.warning("選択された週は「未観測」です。")

    def get_val(data_row, col_name):
        if col_name in data_row and pd.notnull(data_row[col_name]):
            return float(data_row[col_name])
        return None

    def_temp_0m = get_val(target_data, 'temp_0m')
    def_temp_5m = get_val(target_data, 'temp_5m')
    def_sal_0m = get_val(target_data, 'sal_0m')
    def_sal_5m = get_val(target_data, 'sal_5m')
    def_do_0m = get_val(target_data, 'do_0m')
    def_do_5m = get_val(target_data, 'do_5m')
    def_chl_0m = get_val(target_data, 'chl_0m')
    def_chl_5m = get_val(target_data, 'chl_5m')
    def_precip_day = get_val(target_data, 'precip_mm_day')
    def_precip = get_val(target_data, 'precip_sum_july')
    def_temp_sum_0m = get_val(target_data, 'temp_sum_0m')
    def_temp_sum_5m = get_val(target_data, 'temp_sum_5m')

    st.sidebar.subheader("海洋環境データ")
    input_temp_0m = st.sidebar.number_input("観測日の0m水温 ℃", value=def_temp_0m, step=0.1)
    input_temp = st.sidebar.number_input("観測日の5m水温 ℃", value=def_temp_5m, step=0.1)
    input_sal_0m = st.sidebar.number_input("観測日の0m塩分 (PSU)", value=def_sal_0m, step=0.1)
    input_sal_5m = st.sidebar.number_input("観測日の5m塩分 (PSU)", value=def_sal_5m, step=0.1)
    input_chl_0m = st.sidebar.number_input("観測日の0mクロロフィル", value=def_chl_0m, step=0.1)
    input_chl = st.sidebar.number_input("観測日の5mクロロフィル", value=def_chl_5m, step=0.1)
    input_do_0m = st.sidebar.number_input("観測日の0m溶存酸素 mg/L", value=def_do_0m, step=0.1)
    input_do_5m = st.sidebar.number_input("観測日の5m溶存酸素 mg/L", value=def_do_5m, step=0.1)
    input_temp_sum_0m = st.sidebar.number_input("観測日の0m積算水温 ℃", value=def_temp_sum_0m, step=10.0)
    input_temp_sum_5m = st.sidebar.number_input("観測日の5m積算水温 ℃", value=def_temp_sum_5m, step=10.0)
    
    st.sidebar.subheader("気象データ")
    input_precip_day = st.sidebar.number_input("週間降水量 (mm)", value=def_precip_day, step=1.0)
    input_precip = st.sidebar.number_input("7月の累計降水量 (mm)", value=def_precip, step=1.0)

    # 3. リスク判定ロジック
    st.subheader("⚠️ リスク判定結果")
    
    star_date = pd.to_datetime(f"2024-{input_date.month:02d}-{input_date.day:02d}")
    
    if is_future_date:
        st.info("🔮 **未来の日付が選択されているため、判定は行えません。**")
    elif is_off_season:
        st.info("❄️ **現在の期間はへい死リスクが低いため、観測休止期間（オフシーズン）です。**")
    else:
        ref_2025 = df_2025[df_2025['week_num'] == input_week]
        ref_2024 = df_2024[df_2024['week_num'] == input_week] 
        ref_2023 = df_2023[df_2023['week_num'] == input_week]
        
        if not ref_2025.empty:
            ref_temp_2025 = ref_2025['temp_5m'].values[0]
            ref_temp_2024 = ref_2024['temp_5m'].values[0] if not ref_2024.empty else 99.0
            ref_temp_2023 = ref_2023['temp_5m'].values[0] if not ref_2023.empty else 99.0
            
            str_temp_2024 = f"{ref_temp_2024}℃" if ref_temp_2024 != 99.0 else "データなし"
            str_temp_2023 = f"{ref_temp_2023}℃" if ref_temp_2023 != 99.0 else "データなし"
            
            score = 0
            reasons = []

            # 判定A: 水温
            if input_temp is not None:
                is_over_2025 = (input_temp >= ref_temp_2025)
                is_over_2024 = (input_temp >= ref_temp_2024)

                if is_over_2025:
                    score += 2
                    reasons.append(f"水深5mの現在の水温（{input_temp}℃）が2025年同期（{ref_temp_2025}℃）を上回るペースで推移しており、今後のさらなる水温上昇に警戒が必要です。")
                elif is_over_2024:
                    score += 2
                    reasons.append(f"水深5mの現在の水温（{input_temp}℃）が2024年同期（{str_temp_2024}）を上回るペースで推移しており、今後のさらなる水温上昇に警戒が必要です。")
                elif input_temp >= 28.0:
                    score += 2
                    reasons.append(f"水深5mの水温が28℃以上（{input_temp}℃）であり、熱ストレス圏内です。")
                elif input_temp > ref_temp_2023 and ref_temp_2023 != 99.0:
                    score += 1
                    reasons.append(f"水深5mの現在の水温（{input_temp}℃）が2023年同期（{str_temp_2023}）を上回って推移しており、やや高めの状態です。")
                elif input_temp >= 27.0:
                    score += 1
                    reasons.append(f"水深5mの水温が27℃以上（{input_temp}℃）であり、熱ストレス圏内です。")
                else:
                    reasons.append(f"水深5mの水温は過去と比較して平年並み、または低い状態です。（{input_temp}℃）")
            else:
                reasons.append("水深5mの水温は「未観測」のため、判定から除外しています。")

            # 判定B: 降水量
            if input_precip is not None:
                if input_precip == 0.0:
                    reasons.append("7月の降水量は時期前のため、リスク判定から除外しています。")
                elif input_precip < 100:
                    score += 2
                    reasons.append(f"7月の降水量が100mm未満（{input_precip}mm）の少雨であり、高塩分・貧栄養のリスクがあります。")
                elif input_precip < 200:
                    score += 1
                    reasons.append(f"7月の降水量が200mm未満（{input_precip}mm）であり、高塩分・貧栄養の兆候に注意が必要です。")
                else:
                    reasons.append(f"7月の降水量は200mm以上（{input_precip}mm）あり、十分な雨が降っています。")
            else:
                reasons.append("7月の降水量は「未観測」のため、判定から除外しています。")

            # 判定C: クロロフィル
            if input_chl is not None:
                if input_chl < 1.0:
                    score += 2
                    reasons.append(f"クロロフィルが非常に低く（{input_chl} µg/L）、牡蠣が餌不足に陥っています。")
                elif input_chl < 2.0:
                    score += 1
                    reasons.append(f"クロロフィルがやや低め（{input_chl} µg/L）で、牡蠣が餌不足に陥るリスクがあります。")
                else:
                    reasons.append(f"クロロフィルは十分（{input_chl} µg/L）あり、牡蠣の餌環境は良好です。")
            else:
                reasons.append("水深5mのクロロフィルは「未観測」のため、判定から除外しています。")

            # 判定D: 溶存酸素の低下リスク
            if input_do_5m is not None:
                if input_do_5m < 4.0:
                    score += 5
                    reasons.append(f"水深5mの溶存酸素が非常に低く（{input_do_5m} mg/L）、貧酸素による致命的なダメージを受けるリスクがあります。")
                elif input_do_5m < 5.0:
                    score += 1
                    reasons.append(f"水深5mの溶存酸素が低下しており（{input_do_5m} mg/L）、環境ストレスがかかりやすい状態です。")
                else:
                    reasons.append(f"溶存酸素は十分（{input_do_5m} mg/L）であり、貧酸素の危険性は低いです。")
            else:
                reasons.append("水深5mの溶存酸素は「未観測」のため、判定から除外しています。")

            # 判定E: 塩分の上昇リスク
            if input_sal_5m is not None:
                if input_sal_5m >= 33.0:
                    score += 1
                    reasons.append(f"塩分が33 PSU以上（{input_sal_5m} PSU）と高くなっており、環境ストレスの要因となる可能性があります。")
                else:
                    reasons.append(f"塩分は正常な範囲内（{input_sal_5m} PSU）です。")
            else:
                reasons.append("水深5mの塩分は「未観測」のため、判定から除外しています。")
            
            missing_items = []
            if input_temp is None: missing_items.append("水温")
            if input_chl is None: missing_items.append("クロロフィル")
            if input_do_5m is None: missing_items.append("溶存酸素")
            if input_sal_5m is None: missing_items.append("塩分")
            
            if input_precip is None and selected_year != 2026:
                missing_items.append("降水量")
            
            if len(missing_items) > 0:
                st.info("### ⚪ 【判定保留】未計測項目あり")
                st.write(f"**判定：未観測の項目（{', '.join(missing_items)}）があるため、全体のリスク判定は保留としています。**")
                for r in reasons:
                    st.write(f"- {r}")
                    
            elif score >= 5:
                st.error(f"### 🔴 【危険：赤】リスクスコア: {score}")
                st.caption("スコア凡例：🔴危険: 5点以上 🟡警戒: 3〜4点 🟢安全: 2点以下")
                st.write("**判定：大量へい死の危険性が極めて高い状態です。**")
                for r in reasons:
                    st.write(f"- {r}")
                
            elif score >= 3:
                st.warning(f"### 🟡 【警戒：黄】リスクスコア: {score}")
                st.caption("スコア凡例：🔴危険: 5点以上 🟡警戒: 3〜4点 🟢安全: 2点以下")
                st.write("**判定：環境が悪化しつつあります。今後の予報に注意してください。**")
                for r in reasons:
                    st.write(f"- {r}")
                
            else:
                st.success(f"### 🟢 【安全：緑】リスクスコア: {score}") 
                st.caption("スコア凡例：🔴危険: 5点以上 🟡警戒: 3〜4点 🟢安全: 2点以下")
                st.write("**判定：現在のところ平年並み、または安全な環境です。**")
                for r in reasons:
                    st.write(f"- {r}")

        st.divider()

        # 観測地点の表示
        st.markdown("📍 **観測地点：三協化成沖**")
        
        lat, lon = 34.30914828361069, 132.81821499692464
        
        layer_circle = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({"lat": [lat], "lon": [lon]}),
            get_position="[lon, lat]",
            get_fill_color=[255, 105, 180, 200],
            get_radius=150, 
        )
        
        layer_pin = pdk.Layer(
            "TextLayer",
            data=pd.DataFrame({"lat": [lat], "lon": [lon], "text": ["📍"]}),
            get_position="[lon, lat]",
            get_text="text",
            get_size=40,
            get_alignment_baseline="'bottom'",
        )
        
        view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=13)
        r = pdk.Deck(
            layers=[layer_circle, layer_pin],
            initial_view_state=view_state,
            map_style="road", 
        )
        st.pydeck_chart(r, height=300)

        # 4. 可視化（グラフ表示の自動化）
        st.divider()
        st.header("📊 環境データの推移比較")
        
        color_map = {2026: "orange", 2025: "red", 2024: "yellowgreen", 2023: "cyan"}
        
        graph_sections = [
            {
                "section_title": "■ 水深 5m",
                "graphs": [
                    {"title": "水温", "icon": "🌡️", "col": "temp_5m", "y_label": "水温 (℃)", "unit": "℃", "input": input_temp, "type": "line"},
                    {"title": "塩分", "icon": "💠", "col": "sal_5m", "y_label": "塩分 (PSU)", "unit": " PSU", "input": input_sal_5m, "type": "line"},
                    {"title": "クロロフィル", "icon": "🟢", "col": "chl_5m", "y_label": "クロロフィル (µg/L)", "unit": " µg/L", "input": input_chl, "type": "line"},
                    {"title": "溶存酸素", "icon": "⚪", "col": "do_5m", "y_label": "溶存酸素 (mg/L)", "unit": " mg/L", "input": input_do_5m, "type": "line"},
                    {"title": "積算水温", "icon": "📈", "col": "temp_sum_5m", "y_label": "積算水温 (℃)", "unit": " ℃", "input": input_temp_sum_5m, "type": "line"},
                ]
            },
            {
                "section_title": "■ 水深 0m",
                "graphs": [
                    {"title": "水温", "icon": "🌡️", "col": "temp_0m", "y_label": "水温 (℃)", "unit": "℃", "input": input_temp_0m, "type": "line"},
                    {"title": "塩分", "icon": "💠", "col": "sal_0m", "y_label": "塩分 (PSU)", "unit": " PSU", "input": input_sal_0m, "type": "line"},
                    {"title": "クロロフィル", "icon": "🟢", "col": "chl_0m", "y_label": "クロロフィル (µg/L)", "unit": " µg/L", "input": input_chl_0m, "type": "line"},
                    {"title": "溶存酸素", "icon": "⚪", "col": "do_0m", "y_label": "溶存酸素 (mg/L)", "unit": " mg/L", "input": input_do_0m, "type": "line"},
                    {"title": "積算水温", "icon": "📈", "col": "temp_sum_0m", "y_label": "積算水温 (℃)", "unit": " ℃", "input": input_temp_sum_0m, "type": "line"},
                ]
            },
            {
                "section_title": "■ 気象データ",
                "graphs": [
                    {"title": "週間降水量", "icon": "🌧️", "col": "precip_mm_day", "y_label": "降水量 (mm)", "unit": " mm", "input": input_precip_day, "type": "line"},
                    {"title": "7月の合計降水量", "icon": "🌧️", "col": "precip_sum_july", "y_label": "降水量 (mm)", "unit": " mm", "input": input_precip, "type": "bar"},
                ]
            }
        ]

        tickvals = [f"2024-{m:02d}-01" for m in range(2, 11)]
        ticktext = [f"{m}月" for m in range(2, 11)]
        
        star_marker = dict(size=18, color="#FFD700", symbol="star", line=dict(color="black", width=1))

        for section in graph_sections:
            st.subheader(section["section_title"])
            
            for g in section["graphs"]:
                st.markdown(f"#### {g['icon']} {g['title']}")
                
                if g['col'] in ['temp_0m', 'temp_5m']:
                    st.caption("※ 背景のうす赤色の範囲は、平年（2023年）以上の値を示しています。")
                    
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
                    
                    if g['input'] is not None:
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
                        # 💡 凡例を上部（タイトルとグラフの間）に配置してスマホでの重なりを防ぐ
                        margin=dict(l=10, r=10, t=60, b=20)
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
                            
                            if year == 2023 and g['col'] in ['temp_0m', 'temp_5m']:
                                max_col_val = df[g['col']].max(skipna=True)
                                input_val = g['input'] if g['input'] is not None else 0.0
                                max_y = max(max_col_val if pd.notnull(max_col_val) else 30.0, input_val) + 2.0
                                fig.add_trace(go.Scatter(
                                    x=year_data['plot_date'], 
                                    y=[max_y] * len(year_data), 
                                    name="平年以上の値（2023年超過）",
                                    line=dict(width=0),
                                    fill='tonexty',
                                    fillcolor='rgba(255, 0, 0, 0.1)', 
                                    showlegend=False,
                                    hoverinfo='skip',
                                    connectgaps=True
                                ))
                    
                    if g['input'] is not None:
                        fig.add_trace(go.Scatter(
                            x=[star_date], 
                            y=[g['input']], 
                            name="観測日の値", 
                            marker=star_marker, 
                            mode="markers", 
                            hovertemplate=f'観測日: %{{y}}{g["unit"]}'
                        ))

                    col_name = g['col']
                    if col_name in ['temp_sum_0m', 'temp_sum_5m']:
                        fig.add_hline(y=600, line_dash="dash", line_color="gray", annotation_text="産卵開始 600℃", annotation_position="bottom right")
                        fig.add_hline(y=900, line_dash="dash", line_color="gray", annotation_text="採苗目安 900℃", annotation_position="bottom right")
                    
                    elif col_name in ['do_0m', 'do_5m']:
                        fig.add_hline(y=5, line_dash="dash", line_color="gray", annotation_text="酸素低下 5mg/L", annotation_position="bottom right")
                        fig.add_hline(y=4, line_dash="dash", line_color="gray", annotation_text="要警戒 4mg/L", annotation_position="bottom right")
                    
                    elif col_name in ['chl_0m', 'chl_5m']:
                        fig.add_hline(y=2, line_dash="dash", line_color="gray", annotation_text="餌料豊富 2µg/L", annotation_position="bottom right")
                        fig.add_hline(y=1, line_dash="dash", line_color="gray", annotation_text="餌不足 1µg/L", annotation_position="bottom right")
                    
                    elif col_name in ['sal_0m', 'sal_5m']:
                        fig.add_hline(y=33, line_dash="dash", line_color="gray", annotation_text="高塩分 33 PSU", annotation_position="bottom right")

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
                        # 💡 凡例をグラフ上部に配置
                        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
                        # 💡 スマホ表示用に上下の余白を少し広げて重なりを防止
                        margin=dict(l=10, r=10, t=60, b=20)
                    )

                st.plotly_chart(fig, use_container_width=True)
                st.divider()

    st.markdown("""
    <div style="font-size: 0.8em; color: gray; margin-top: 50px;">
        <strong>免責事項およびデータの取り扱いについて</strong><br>
        本システムは、安芸津海域における環境監視およびへい死リスクの予測を目的とした研究用プロトタイプです。<br>
        提供するデータや判定結果の正確性・完全性について、いかなる保証も行うものではありません。<br>
        <strong>本システムに掲載されているデータ、グラフ、判定結果等について、無断での抽出、加工、転載、および販売等の二次利用（商用利用）を固く禁じます。</strong><br>
        本システムの利用に伴って生じたトラブルや損害について、当研究室は一切の責任を負いません。<br>
        本システムは予告なく仕様変更、または公開を停止する場合があります。<br><br>
        運営・著作権表記： 広島大学 統合生命科学研究科 小池研究室
    </div>
    """, unsafe_allow_html=True)

except FileNotFoundError:
    st.error("エラー: `oyster_akitsu.csv` が見つかりません。ファイル名を確認してください。")
