"""マッチング結果ページ"""
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from db import get_all_jobs, init_db
from matcher import rank_jobs
from ai_parser import generate_match_reasoning

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
init_db()

st.set_page_config(page_title="マッチング", page_icon="🎯", layout="wide")
st.title("マッチング結果")

if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = None

profile = st.session_state.candidate_profile

if profile is None:
    st.warning("候補者が登録されていません。先に「候補者登録」ページでメモを解析してください。")
    st.stop()

# 候補者サマリ
st.subheader("候補者情報")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("氏名", profile.get("name", "不明"))
with col2:
    st.metric("希望職種", profile.get("desired_job_type", "不明"))
with col3:
    st.metric("希望勤務地", profile.get("desired_location", "不明"))
with col4:
    st.metric("希望年収", profile.get("desired_salary", "不明"))

st.markdown("---")

# マッチング実行
jobs_df = get_all_jobs()

if jobs_df.empty:
    st.warning("求人データがありません。先に「求人検索」または「求人管理」からデータを追加してください。")
    st.stop()

ranked = rank_jobs(profile, jobs_df)

# 表示件数
total_count = len(ranked)
if total_count <= 5:
    top_n = total_count
else:
    top_n = st.slider("表示件数", min_value=1, max_value=min(50, total_count), value=min(10, total_count))

st.subheader(f"マッチ求人（{len(ranked)}件中 上位{top_n}件）")

for i, row in ranked.head(top_n).iterrows():
    total = row.get("total_score", 0)

    # スコアに応じた色
    if total >= 60:
        color = "🟢"
    elif total >= 40:
        color = "🟡"
    else:
        color = "⚪"

    with st.expander(
        f"{color} {i+1}位: スコア {total}/100 | {row.get('company_name', '不明')} - {row.get('job_title', '不明')}",
        expanded=(i < 3),
    ):
        col_info, col_score = st.columns([3, 2])

        with col_info:
            st.markdown(f"**会社名:** {row.get('company_name', '不明')}")
            st.markdown(f"**求人タイトル:** {row.get('job_title', '不明')}")
            st.markdown(f"**職種:** {row.get('job_type', '不明')}")

            sal_text = ""
            if row.get("salary_min"):
                sal_text = f"{int(row['salary_min'])}万"
            if row.get("salary_max"):
                sal_text += f"〜{int(row['salary_max'])}万"
            st.markdown(f"**年収:** {sal_text or '不明'}")
            st.markdown(f"**勤務地:** {row.get('location', '不明')}")
            st.markdown(f"**雇用形態:** {row.get('work_schedule', '不明')}")
            st.markdown(f"**残業:** {row.get('overtime_hours', '不明')}")

            if row.get("description"):
                desc = str(row["description"])
                st.markdown(f"**仕事内容:** {desc[:200]}{'...' if len(desc) > 200 else ''}")

            if row.get("source_url"):
                st.markdown(f"[求人ページを開く]({row['source_url']})")

        with col_score:
            st.markdown("**スコア内訳:**")
            score_items = {
                "職種": ("score_job_type", 30),
                "年収": ("score_salary", 25),
                "勤務地": ("score_location", 20),
                "残業": ("score_overtime", 10),
                "雇用形態": ("score_schedule", 10),
                "スキル": ("score_skills", 5),
            }
            for label, (key, max_val) in score_items.items():
                val = row.get(key, 0)
                st.progress(val / max_val if max_val > 0 else 0, text=f"{label}: {val}/{max_val}")

        # AIコメント生成
        if st.button(f"AIコメント生成", key=f"ai_comment_{i}"):
            with st.spinner("AIがマッチ度を分析中..."):
                try:
                    job_dict = row.to_dict()
                    # スコア列を除外
                    job_dict = {k: v for k, v in job_dict.items() if not k.startswith("score_") and k != "total_score"}
                    comment = generate_match_reasoning(profile, job_dict)
                    st.info(comment)
                except Exception as e:
                    st.error(f"AIコメント生成エラー: {e}")
