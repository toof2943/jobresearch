"""求人管理ページ - ローカルDB管理"""
import io
import streamlit as st
import pandas as pd
from db import get_all_jobs, add_job, delete_job, import_csv, init_db

init_db()

st.set_page_config(page_title="求人管理", page_icon="📋", layout="wide")
st.title("求人管理")

tab_list, tab_add, tab_import = st.tabs(["求人一覧", "手動追加", "CSVインポート"])

# --- 求人一覧 ---
with tab_list:
    jobs_df = get_all_jobs()
    if jobs_df.empty:
        st.info("求人データがありません。CSVインポートまたは求人検索でデータを追加してください。")
    else:
        st.write(f"登録求人数: {len(jobs_df)}件")

        # フィルタ
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            filter_type = st.text_input("職種で絞り込み", key="filter_type")
        with col_filter2:
            filter_loc = st.text_input("勤務地で絞り込み", key="filter_loc")
        with col_filter3:
            filter_source = st.selectbox("取得元", ["すべて", "indeed", "csv", "manual"], key="filter_source")

        filtered = jobs_df.copy()
        if filter_type:
            mask = (
                filtered["job_type"].fillna("").str.contains(filter_type, case=False)
                | filtered["job_title"].fillna("").str.contains(filter_type, case=False)
            )
            filtered = filtered[mask]
        if filter_loc:
            filtered = filtered[filtered["location"].fillna("").str.contains(filter_loc, case=False)]
        if filter_source != "すべて":
            filtered = filtered[filtered["source"] == filter_source]

        # 表示カラム
        display_cols = ["id", "company_name", "job_title", "job_type", "salary_min", "salary_max", "location", "work_schedule", "source"]
        display_cols = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[display_cols],
            use_container_width=True,
            column_config={
                "id": "ID",
                "company_name": "会社名",
                "job_title": "求人タイトル",
                "job_type": "職種",
                "salary_min": "年収下限",
                "salary_max": "年収上限",
                "location": "勤務地",
                "work_schedule": "雇用形態",
                "source": "取得元",
            },
        )

        # 削除
        st.subheader("求人削除")
        delete_id = st.number_input("削除するID", min_value=0, step=1, key="delete_id")
        if st.button("削除", type="secondary"):
            if delete_id > 0:
                delete_job(delete_id)
                st.success(f"ID {delete_id} を削除しました")
                st.rerun()

# --- 手動追加 ---
with tab_add:
    with st.form("add_job_form"):
        st.subheader("求人情報を入力")
        company = st.text_input("会社名")
        title = st.text_input("求人タイトル")
        job_type = st.text_input("職種")
        col_sal1, col_sal2 = st.columns(2)
        with col_sal1:
            sal_min = st.number_input("年収下限（万円）", min_value=0, value=0)
        with col_sal2:
            sal_max = st.number_input("年収上限（万円）", min_value=0, value=0)
        loc = st.text_input("勤務地")
        overtime = st.text_input("残業時間")
        schedule = st.selectbox("雇用形態", ["正社員", "契約社員", "パート・アルバイト", "派遣", "業務委託", "その他"])
        desc = st.text_area("仕事内容")
        reqs = st.text_area("応募条件")
        benefits = st.text_area("福利厚生")

        if st.form_submit_button("追加", type="primary"):
            if company and title:
                add_job({
                    "company_name": company,
                    "job_title": title,
                    "job_type": job_type,
                    "salary_min": sal_min or None,
                    "salary_max": sal_max or None,
                    "location": loc,
                    "overtime_hours": overtime,
                    "work_schedule": schedule,
                    "description": desc,
                    "requirements": reqs,
                    "benefits": benefits,
                    "source": "manual",
                })
                st.success("求人を追加しました！")
            else:
                st.error("会社名と求人タイトルは必須です。")

# --- CSVインポート ---
with tab_import:
    st.subheader("CSVファイルをインポート")
    st.markdown("対応ヘッダー: 会社名, 求人タイトル, 職種, 年収下限（万円）, 年収上限（万円）, 勤務地, 残業時間, 雇用形態, 仕事内容, 応募条件, 福利厚生")

    uploaded = st.file_uploader("CSVファイル", type=["csv"])
    if uploaded:
        # エンコーディング検出
        raw = uploaded.read()
        uploaded.seek(0)
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(raw), encoding="shift_jis")

        st.write(f"プレビュー（{len(df)}行）")
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("インポート実行", type="primary"):
            count = import_csv(df)
            st.success(f"{count}件の求人をインポートしました！")
