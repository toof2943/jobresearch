"""求人検索ページ - ソースアダプターで検索→結果取込"""
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from scraper import fetch_job_detail
from ai_parser import generate_search_keywords, parse_job_page
from db import add_jobs_bulk
from job_sources import JobSearchQuery, list_sources, search_jobs_with_sources

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

st.set_page_config(page_title="求人検索", page_icon="🔎", layout="wide")
st.title("求人検索（ソースアダプター）")

if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = None

st.subheader("検索条件")

col_keyword, col_location = st.columns([2, 1])
with col_keyword:
    keyword = st.text_input("キーワード", placeholder="例: 一般事務 正社員")
with col_location:
    location = st.text_input("勤務地", placeholder="例: 東京")

if st.session_state.candidate_profile:
    profile = st.session_state.candidate_profile
    st.info(
        f"候補者: {profile.get('name', '不明')} | 希望: {profile.get('desired_job_type', '')} / {profile.get('desired_location', '')}"
    )

    if st.button("候補者の条件からキーワード生成（AI）"):
        with st.spinner("キーワード生成中..."):
            try:
                keywords = generate_search_keywords(profile)
                st.session_state.suggested_keywords = keywords
            except Exception as e:
                st.error(f"キーワード生成エラー: {e}")

    if "suggested_keywords" in st.session_state:
        st.write("おすすめキーワード:")
        for i, kw in enumerate(st.session_state.suggested_keywords):
            if st.button(f"📋 {kw}", key=f"kw_{i}"):
                st.session_state.use_keyword = kw
                st.rerun()

    if "use_keyword" in st.session_state:
        keyword = st.session_state.use_keyword
        del st.session_state.use_keyword
else:
    st.warning("候補者が登録されていません。先に「候補者登録」ページでメモを解析してください。")

st.markdown("---")
source_options = list_sources()
source_ids = [sid for sid, _ in source_options]
source_label_to_id = {label: sid for sid, label in source_options}
default_labels = [label for sid, label in source_options if sid in ("company_site", "csv_seed")]

selected_labels = st.multiselect(
    "検索ソース",
    options=[label for _, label in source_options],
    default=default_labels,
)
selected_sources = [source_label_to_id[label] for label in selected_labels]

col_pages, col_csv = st.columns(2)
with col_pages:
    max_pages = st.number_input("検索ページ数（スクレイピング系）", min_value=1, max_value=5, value=2)
with col_csv:
    csv_path = st.text_input("CSVソースパス", value="data/sample_jobs.csv")

company_sites_input = ""
if "company_site" in selected_sources:
    company_sites_input = st.text_area(
        "企業公式サイトURL（1行1件）",
        placeholder="https://corp.example.com/recruit\nhttps://another.example.jp/careers",
        height=120,
    )

if st.button("選択ソースで検索", type="primary", disabled=(not keyword or not selected_sources)):
    with st.spinner(f"「{keyword}」で検索中..."):
        query = JobSearchQuery(
            keyword=keyword,
            location=location,
            pages=max_pages,
            csv_path=csv_path,
            company_sites=[line.strip() for line in company_sites_input.splitlines() if line.strip()],
        )
        results, errors = search_jobs_with_sources(query, selected_sources)
        st.session_state.search_results = results

        if results:
            st.success(f"{len(results)}件の求人が見つかりました")
        else:
            st.warning("求人が見つかりませんでした。キーワードかソースを変えてみてください。")

        for sid, msg in errors.items():
            st.warning(f"{sid}: 取得失敗 - {msg}")

if st.session_state.search_results:
    st.subheader(f"検索結果（{len(st.session_state.search_results)}件）")

    selected_indices = []
    for i, job in enumerate(st.session_state.search_results):
        with st.container():
            col_check, col_info = st.columns([0.5, 9.5])
            with col_check:
                checked = st.checkbox("", key=f"select_{i}")
                if checked:
                    selected_indices.append(i)
            with col_info:
                salary_text = ""
                if job.get("salary_min"):
                    salary_text = f"{job['salary_min']}万"
                    if job.get("salary_max"):
                        salary_text += f"〜{job['salary_max']}万"
                    salary_text = f" | 💰 {salary_text}"

                st.markdown(
                    f"**{job.get('job_title', '不明')}** - {job.get('company_name', '不明')}"
                    f"  \n📍 {job.get('location', '不明')}{salary_text} | 取得元: {job.get('source', '不明')}"
                )
                if job.get("description"):
                    desc = str(job.get("description", ""))
                    st.caption(desc[:150] + "..." if len(desc) > 150 else desc)

                col_detail, col_url = st.columns(2)
                with col_url:
                    if job.get("source_url"):
                        st.markdown(f"[求人ページを開く]({job['source_url']})")

                with col_detail:
                    if job.get("source_url") and st.button("AI詳細解析", key=f"detail_{i}"):
                        with st.spinner("求人ページを解析中..."):
                            try:
                                page_text = fetch_job_detail(job["source_url"])
                                if page_text.startswith("ページ取得エラー:"):
                                    st.error(page_text)
                                else:
                                    parsed = parse_job_page(page_text)
                                    for k, v in parsed.items():
                                        if v is not None:
                                            st.session_state.search_results[i][k] = v
                                    st.success("詳細情報を取得しました")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"解析エラー: {e}")
            st.divider()

    if selected_indices:
        if st.button(f"選択した {len(selected_indices)} 件をDBに保存", type="primary"):
            jobs_to_save = [st.session_state.search_results[i] for i in selected_indices]
            count = add_jobs_bulk(jobs_to_save)
            st.success(f"{count}件の求人をDBに保存しました！")

    if st.button("全件をDBに保存"):
        count = add_jobs_bulk(st.session_state.search_results)
        st.success(f"{count}件の求人をDBに保存しました！")
