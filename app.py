import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk 

# ページの基本設定
st.set_page_config(page_title="安芸津牡蠣養殖 環境監視システム", layout="wide")

# 1. データの読み込み（oyster_akitsu_2.csv と oyster_akitsu.csv の両方に対応）
@st.cache_data(ttl=3600)  
def load_data():
    csv_path = 'oyster_akitsu_2.csv' if os.path.exists('oyster_akitsu_2.csv') else 'oyster_akitsu.csv'
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    # date列の年表記ゆれをyear列に合わせて正規化
    df['date'] = df.apply(
        lambda r: r['date'].replace(year=int(r['year'])) if pd.notnull(r['date']) and pd.notnull(r['year']) else r['date'],
        axis=1
    )
    df['plot_date'] = df['date'].apply(lambda d: d.replace(year=2024) if pd.notnull(d) else d)
    # 冬季（11月〜5月）グラフ用の日付列（11〜12月は2023年、1〜5月は2024年に配置）
    df['winter_plot_date'] = df['date'].apply(
        lambda d: (d.replace(year=2023) if d.month >= 11 else d.replace(year=2024)) if pd.notnull(d) else d
    )
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
    
    st.write("安芸津海域の最新海況データと過去の環境推移を比較・確認できます。")
    st.info(f"📢 **{latest_date.year}年{latest_date.month}月{latest_date.day}日 データ更新！**")
    
    st.info(
        "💡 **アプリの使い方**\n"
        "- **初期表示:** システムに登録されている最新の海況データです。\n"
        "- **過去を振り返る:** 画面左上の「＞＞」マークをタップするとメニューが開きます。カレンダーの「観測日」を変更すると、過去のデータを呼び出して当時の状況を確認できます。\n"
        "- **自分の漁場と比較する:** ご自身で測った数値を直接入力することで、グラフ上での比較や（6月〜10月は）自身の漁場の危険度を判定できます。"
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

    # 夏季（6月〜10月：第23〜44週）か冬季（11月〜5月：第1〜22週・第45〜53週）かの判定
    is_risk_season = (23 <= input_week <= 44) and (6 <= input_date.month <= 10)

    is_missing_week = False
    if not is_future_date:
        if 'is_interpolated' in target_data and pd.notnull(target_data['is_interpolated']):
            if float(target_data['is_interpolated']) == 1.0:
                is_missing_week = True
        elif target_data.empty:
            is_missing_week = True

    if is_missing_week:
        st.sidebar.warning("選択された週は「未観測（または補間データ）」です。")

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

    # 過去同週データの取得
    ref_2025 = df_2025[df_2025['week_num'] == input_week]
    ref_2024 = df_2024[df_2024['week_num'] == input_week] 
    ref_2023 = df_2023[df_2023['week_num'] == input_week]
    
    def safe_get_ref_temp(df_ref):
        if not df_ref.empty:
            val = df_ref['temp_5m'].values[0]
            if pd.notnull(val):
                return float(val)
        return 99.0  

    ref_temp_2025 = safe_get_ref_temp(ref_2025)
    ref_temp_2024 = safe_get_ref_temp(ref_2024)
    ref_temp_2023 = safe_get_ref_temp(ref_2023)
    
    str_temp_2025 = f"{ref_temp_2025}℃" if ref_temp_2025 != 99.0 else "データなし"
    str_temp_2024 = f"{ref_temp_2024}℃" if ref_temp_2024 != 99.0 else "データなし"
    str_temp_2023 = f"{ref_temp_2023}℃" if ref_temp_2023 != 99.0 else "データなし"

    star_date = pd.to_datetime(f"2024-{input_date.month:02d}-{input_date.day:02d}")
    star_year_winter = 2023 if input_date.month >= 11 else 2024
    star_date_winter = pd.to_datetime(f"{star_year_winter}-{input_date.month:02d}-{input_date.day:02d}")

    # 3. メイン表示エリア（夏季は「へい死リスク」、冬季は「現在の海況」に切り替え）
    if is_future_date:
        st.subheader("⚠️ リスク判定結果 / 現在の海況")
        st.info("🔮 **未来の日付が選択されているため、データの表示・判定は行えません。**")

    elif is_risk_season:
        # =========================================================
        # 【夏季：6月〜10月】へい死リスク判定ページ
        # =========================================================
        st.subheader("⚠️ リスク判定結果")
        
        score = 0
        reasons = []

        if input_date.month >= 9:
            trend_str = "上回って推移しており"
            alert_str = "高水温による熱ストレスの蓄積に警戒が必要です。"
        else:
            trend_str = "上回るペースで推移しており"
            alert_str = "今後のさらなる水温上昇に警戒が必要です。"

        # ① 水温
        if input_temp is not None:
            is_over_2025 = (input_temp >= ref_temp_2025) and (ref_temp_2025 != 99.0)
            is_over_2024 = (input_temp >= ref_temp_2024) and (ref_temp_2024 != 99.0)

            if is_over_2025:
                score += 2
                reasons.append(f"水深5mの現在の水温（{input_temp}℃）が2025年同期（{str_temp_2025}）を{trend_str}、{alert_str}")
            elif is_over_2024:
                score += 2
                reasons.append(f"水深5mの現在の水温（{input_temp}℃）が2024年同期（{str_temp_2024}）を{trend_str}、{alert_str}")
            elif input_temp >= 28.0:
                score += 2
                reasons.append(f"水深5mの水温が28℃以上（{input_temp}℃）であり、熱ストレス圏内です。")
            elif input_temp >= ref_temp_2023 and ref_temp_2023 != 99.0: 
                score += 1
                reasons.append(f"水深5mの現在の水温（{input_temp}℃）が2023年同期（{str_temp_2023}）を上回って推移しており、やや高めの状態です。")
            elif input_temp >= 27.0:
                score += 1
                reasons.append(f"水深5mの水温が27℃以上（{input_temp}℃）であり、熱ストレス圏内です。")
            else:
                reasons.append(f"水深5mの水温は過去と比較して平年並み、または低い状態です。（{input_temp}℃）")
        else:
            reasons.append("水深5mの水温は「未観測」のため、判定から除外しています。")

        # ② 塩分の上昇リスク
        if input_sal_5m is not None:
            if input_sal_5m >= 33.0:
                score += 1
                reasons.append(f"塩分が33 PSU以上（{input_sal_5m} PSU）と高くなっており、環境ストレスの要因となる可能性があります。")
            else:
                reasons.append(f"塩分は正常な範囲内（{input_sal_5m} PSU）です。")
        else:
            reasons.append("水深5mの塩分は「未観測」のため、判定から除外しています。")

        # ③ クロロフィル
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

        # ④ 溶存酸素の低下リスク
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

        # ⑤ 7月降水量
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
        
        missing_items = []
        if input_temp is None: missing_items.append("水温")
        if input_sal_5m is None: missing_items.append("塩分")
        if input_chl is None: missing_items.append("クロロフィル")
        if input_do_5m is None: missing_items.append("溶存酸素")
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
            st.write("**判定：大量へい死の危険性が高い状態です。**")
            for r in reasons:
                st.write(f"- {r}")
            
        elif score >= 3:
            st.warning(f"### 🟡 【警戒：黄】リスクスコア: {score}")
            st.caption("スコア凡例：🔴危険: 5点以上 🟡警戒: 3〜4点 🟢安全: 2点以下")
            if input_date.month >= 9:
                st.write("**判定：注意が必要な環境です。これまでの環境ストレスの蓄積が懸念されます。カキの様子に注意してください。**")
            else:
                st.write("**判定：環境が悪化しつつあります。今後の予報に注意してください。**")
            for r in reasons:
                st.write(f"- {r}")
            
        else:
            st.success(f"### 🟢 【安全：緑】リスクスコア: {score}") 
            st.caption("スコア凡例：🔴危険: 5点以上 🟡警戒: 3〜4点 🟢安全: 2点以下")
            st.write("**判定：現在のところ平年並み、または安全な環境です。**")
            for r in reasons:
                st.write(f"- {r}")

    else:
        # =========================================================
        # 【冬季：11月〜5月】現在の海況ページ（各ボックス内に評価文言を統合）
        # =========================================================
        st.subheader("🌊 現在の海況")
        st.caption("※ 11月〜翌年5月はへい死リスクが低いため、リスクスコアの判定は休止し、最新の海況を表示しています。")

        prev_week_df = df_selected_year[df_selected_year['week_num'] == (input_week - 1)]
        prev_data = prev_week_df.iloc[0] if not prev_week_df.empty else pd.Series(dtype=float)

        def calc_delta_str(curr_val, col_name, unit):
            prev_val = get_val(prev_data, col_name)
            if curr_val is not None and prev_val is not None:
                diff = curr_val - prev_val
                return f"{diff:+.2f} {unit}（先週比）"
            return None

        # 各項目の評価メッセージを作成
        if input_temp is not None:
            temp_eval = f"水深5mの現在の水温は {input_temp}℃ です。"
        else:
            temp_eval = "水深5mの水温は「未観測」です。"

        if input_sal_5m is not None:
            if input_sal_5m >= 33.0:
                sal_eval = f"塩分が33 PSU以上（{input_sal_5m} PSU）と高くなっており、環境ストレスの要因となる可能性があります。"
            else:
                sal_eval = f"塩分は正常な範囲内（{input_sal_5m} PSU）です。"
        else:
            sal_eval = "水深5mの塩分は「未観測」です。"

        if input_chl is not None:
            if input_chl < 1.0:
                chl_eval = f"クロロフィルが非常に低く（{input_chl} µg/L）、牡蠣が餌不足に陥っています。"
            elif input_chl < 2.0:
                chl_eval = f"クロロフィルがやや低め（{input_chl} µg/L）で、牡蠣が餌不足に陥るリスクがあります。"
            else:
                chl_eval = f"クロロフィルは十分（{input_chl} µg/L）あり、牡蠣の餌環境は良好です。"
        else:
            chl_eval = "水深5mのクロロフィルは「未観測」です。"

        if input_do_5m is not None:
            if input_do_5m < 4.0:
                do_eval = f"水深5mの溶存酸素が非常に低く（{input_do_5m} mg/L）、貧酸素による致命的なダメージを受けるリスクがあります。"
            elif input_do_5m < 5.0:
                do_eval = f"水深5mの溶存酸素が低下しており（{input_do_5m} mg/L）、環境ストレスがかかりやすい状態です。"
            else:
                do_eval = f"溶存酸素は十分（{input_do_5m} mg/L）であり、貧酸素の危険性は低いです。"
        else:
            do_eval = "水深5mの溶存酸素は「未観測」です。"

        # 4列のボックス内に数値（水温のみ先週比つき）と具体的な評価を表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            with st.container(border=True):
                st.metric(
                    label="🌡️ 水深5m 水温",
                    value=f"{input_temp:.2f} ℃" if input_temp is not None else "未観測",
                    delta=calc_delta_str(input_temp, 'temp_5m', '℃'),
                    delta_color="off"
                )
                st.write(temp_eval)
        with col2:
            with st.container(border=True):
                st.metric(
                    label="💠 水深5m 塩分",
                    value=f"{input_sal_5m:.2f} PSU" if input_sal_5m is not None else "未観測"
                )
                st.write(sal_eval)
        with col3:
            with st.container(border=True):
                st.metric(
                    label="🟢 水深5m クロロフィル（餌）",
                    value=f"{input_chl:.2f} µg/L" if input_chl is not None else "未観測"
                )
                st.write(chl_eval)
        with col4:
            with st.container(border=True):
                st.metric(
                    label="⚪ 水深5m 溶存酸素",
                    value=f"{input_do_5m:.2f} mg/L" if input_do_5m is not None else "未観測"
                )
                st.write(do_eval)

    # 4. 可視化（夏季は6〜10月、冬季は11〜5月のグラフに切り替え）
    st.divider()
    if is_risk_season:
        st.header("📊 環境データの推移比較（夏季：6月〜10月）")
    else:
        st.header("📊 環境データの推移比較（冬季：11月〜5月）")
    
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

    # 冬季（11月〜5月）用の目盛り
    tickvals_winter = ["2023-11-01", "2023-12-01", "2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]
    ticktext_winter = ["11月", "12月", "1月", "2月", "3月", "4月", "5月"]

    # 夏季（6月〜10月）用の目盛り
    tickvals_summer = [f"2024-{m:02d}-01" for m in range(6, 11)]
    ticktext_summer = [f"{m}月" for m in range(6, 11)]

    # 積算水温・冬季（2月〜5月）用の目盛り
    tickvals_sum_winter = [f"2024-{m:02d}-01" for m in range(2, 6)]
    ticktext_sum_winter = [f"{m}月" for m in range(2, 6)]

    # 積算水温・夏季（2月〜10月）用の目盛り
    tickvals_sum_summer = [f"2024-{m:02d}-01" for m in range(2, 11)]
    ticktext_sum_summer = [f"{m}月" for m in range(2, 11)]
    
    star_marker = dict(size=18, color="#FFD700", symbol="star", line=dict(color="black", width=1))

    for section in graph_sections:
        st.subheader(section["section_title"])
        
        for g in section["graphs"]:
            st.markdown(f"#### {g['icon']} {g['title']}")
            
            if g['col'] == 'precip_mm_day':
                st.caption("※ 降水量の観測地点：竹原")
            
            graph_type = g.get("type", "line") 
            col_name = g['col']
            
            # ---------------------------------------------------------
            # A. 棒グラフ（7月の合計降水量）
            # ---------------------------------------------------------
            if graph_type == "bar":
                fig = go.Figure()
                years_list = []
                values_list = []
                colors_list = []
                
                for year in sorted(df['year'].unique()):
                    year_data = df[df['year'] == year]
                    if col_name in year_data.columns:
                        valid_data = year_data[col_name].dropna()
                        if not valid_data.empty:
                            years_list.append(f"{int(year)}年")
                            values_list.append(valid_data.max())
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
                    margin=dict(l=10, r=10, t=60, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.divider()

            # ---------------------------------------------------------
            # B. 積算水温グラフ（冬季は2月〜5月、夏季は2月〜10月）
            # ---------------------------------------------------------
            elif col_name in ['temp_sum_0m', 'temp_sum_5m']:
                fig = go.Figure()

                if is_risk_season:
                    # 夏季モード：2月〜10月
                    target_months = list(range(2, 11))
                    x_range = ["2024-02-01", "2024-10-31"]
                    t_vals = tickvals_sum_summer
                    t_text = ticktext_sum_summer
                else:
                    # 冬季モード：2月〜5月
                    target_months = [2, 3, 4, 5]
                    x_range = ["2024-02-01", "2024-05-31"]
                    t_vals = tickvals_sum_winter
                    t_text = ticktext_sum_winter

                df_sum_sub = df[df['date'].dt.month.isin(target_months)]
                for year in sorted(df['year'].unique()):
                    year_data = df_sum_sub[df_sum_sub['year'] == year].sort_values('plot_date')
                    if col_name in year_data.columns:
                        line_color = color_map.get(year, "gray")
                        fig.add_trace(go.Scatter(
                            x=year_data['plot_date'],
                            y=year_data[col_name],
                            name=f"{int(year)}年",
                            line=dict(color=line_color, width=2),
                            mode='lines+markers',
                            hovertemplate=f'%{{y}}{g["unit"]}',
                            connectgaps=True
                        ))

                if g['input'] is not None and input_date.month in target_months:
                    fig.add_trace(go.Scatter(
                        x=[star_date],
                        y=[g['input']],
                        name="観測日の値",
                        marker=star_marker,
                        mode="markers",
                        hovertemplate=f'観測日: %{{y}}{g["unit"]}'
                    ))

                fig.add_hline(y=600, line_dash="dash", line_color="gray", annotation_text="産卵開始 600℃", annotation_position="bottom right")
                fig.add_hline(y=900, line_dash="dash", line_color="gray", annotation_text="採苗目安 900℃", annotation_position="bottom right")

                fig.update_layout(
                    xaxis=dict(
                        title="",
                        tickmode="array",
                        tickvals=t_vals,
                        ticktext=t_text,
                        range=x_range,
                        hoverformat="%-m月%-d日"
                    ),
                    yaxis_title=g['y_label'],
                    hovermode="x unified",
                    height=350,
                    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
                    margin=dict(l=10, r=10, t=60, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.divider()

            # ---------------------------------------------------------
            # C. その他の折れ線グラフ（夏季は6月〜10月、冬季は11月〜5月）
            # ---------------------------------------------------------
            else:
                fig = go.Figure()

                if is_risk_season:
                    # 【夏季モード：6月〜10月】
                    if col_name in ['temp_0m', 'temp_5m']:
                        st.caption("※ 背景のうす赤色の範囲は、25℃以上の値を示しています。")

                    df_summer_all = df[df['date'].dt.month.isin([6, 7, 8, 9, 10])]
                    for year in sorted(df['year'].unique()):
                        year_data = df_summer_all[df_summer_all['year'] == year].sort_values('plot_date')
                        if col_name in year_data.columns:
                            line_color = color_map.get(year, "gray")
                            fig.add_trace(go.Scatter(
                                x=year_data['plot_date'],
                                y=year_data[col_name],
                                name=f"{int(year)}年",
                                line=dict(color=line_color, width=2),
                                mode='lines+markers',
                                hovertemplate=f'%{{y}}{g["unit"]}',
                                connectgaps=True
                            ))

                    if col_name in ['temp_0m', 'temp_5m']:
                        max_col_val = df_summer_all[col_name].max(skipna=True)
                        input_val = g['input'] if g['input'] is not None else 0.0
                        max_y = max(max_col_val if pd.notnull(max_col_val) else 30.0, input_val) + 2.0
                        fig.add_hrect(
                            y0=25.0,
                            y1=max_y,
                            fillcolor='rgba(255, 0, 0, 0.1)',
                            line_width=0,
                            layer='below'
                        )

                    if g['input'] is not None:
                        fig.add_trace(go.Scatter(
                            x=[star_date],
                            y=[g['input']],
                            name="観測日の値",
                            marker=star_marker,
                            mode="markers",
                            hovertemplate=f'観測日: %{{y}}{g["unit"]}'
                        ))

                    x_range = ["2024-06-01", "2024-10-31"]
                    t_vals = tickvals_summer
                    t_text = ticktext_summer

                else:
                    # 【冬季モード：11月〜5月（案B）】
                    for year in sorted(df['year'].unique()):
                        year_data = df[df['year'] == year]
                        if col_name in year_data.columns:
                            line_color = color_map.get(year, "gray")
                            legend_name = f"{int(year)}年"

                            nov_dec = year_data[year_data['date'].dt.month >= 11].dropna(subset=[col_name]).sort_values('winter_plot_date')
                            jan_may = year_data[year_data['date'].dt.month <= 5].dropna(subset=[col_name]).sort_values('winter_plot_date')

                            if not nov_dec.empty and not jan_may.empty:
                                gap_row = pd.DataFrame({'winter_plot_date': [pd.to_datetime('2023-12-31')], col_name: [None]})
                                w_data = pd.concat([nov_dec, gap_row, jan_may], ignore_index=True)
                            elif not nov_dec.empty:
                                w_data = nov_dec
                            else:
                                w_data = jan_may

                            if not w_data.empty:
                                fig.add_trace(go.Scatter(
                                    x=w_data['winter_plot_date'],
                                    y=w_data[col_name],
                                    name=legend_name,
                                    legendgroup=legend_name,
                                    line=dict(color=line_color, width=2),
                                    mode='lines+markers',
                                    hovertemplate=f'%{{y}}{g["unit"]}',
                                    connectgaps=False
                                ))

                            # 前年（year - 1）の11〜12月最終データから当年（year）の1月初回データへ線を結ぶ
                            prev_year_data = df[df['year'] == (year - 1)]
                            if not prev_year_data.empty and not jan_may.empty:
                                prev_nov_dec = prev_year_data[prev_year_data['date'].dt.month >= 11].dropna(subset=[col_name]).sort_values('winter_plot_date')
                                if not prev_nov_dec.empty:
                                    last_prev = prev_nov_dec.iloc[-1]
                                    first_curr = jan_may.iloc[0]
                                    fig.add_trace(go.Scatter(
                                        x=[last_prev['winter_plot_date'], first_curr['winter_plot_date']],
                                        y=[last_prev[col_name], first_curr[col_name]],
                                        name=legend_name,
                                        legendgroup=legend_name,
                                        showlegend=False,
                                        line=dict(color=line_color, width=2),
                                        mode='lines',
                                        hoverinfo='skip'
                                    ))

                    if g['input'] is not None:
                        fig.add_trace(go.Scatter(
                            x=[star_date_winter],
                            y=[g['input']],
                            name="観測日の値",
                            marker=star_marker,
                            mode="markers",
                            hovertemplate=f'観測日: %{{y}}{g["unit"]}'
                        ))

                    x_range = ["2023-11-01", "2024-05-31"]
                    t_vals = tickvals_winter
                    t_text = ticktext_winter

                # 共通の基準線（溶存酸素・クロロフィル・塩分）
                if col_name in ['do_0m', 'do_5m']:
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
                        tickvals=t_vals,
                        ticktext=t_text,
                        range=x_range,
                        hoverformat="%-m月%-d日"
                    ),
                    yaxis_title=g['y_label'],
                    hovermode="x unified",
                    height=350,
                    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
                    margin=dict(l=10, r=10, t=60, b=20)
                )

                st.plotly_chart(fig, use_container_width=True)
                st.divider()

    # 観測地点のマップを一番最後（降水量グラフの後）に描画
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
    st.error("エラー: CSVファイル（`oyster_akitsu_2.csv` または `oyster_akitsu.csv`）が見つかりません。ファイル名を確認してください。")
