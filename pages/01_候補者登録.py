"""候補者登録ページ - メモ入力 → AI解析 → 編集可能プロフィール"""
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from config import CANDIDATE_FIELDS
from ai_parser import parse_candidate_memo

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

st.set_page_config(page_title="候補者登録", page_icon="👤", layout="wide")
st.title("候補者登録")

# セッション状態初期化
if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = None
if "raw_memo" not in st.session_state:
    st.session_state.raw_memo = ""

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("面談メモ入力")
    memo = st.text_area(
        "メモを貼り付けてください",
        value=st.session_state.raw_memo,
        height=500,
        placeholder="例: 木の前職の同期、部署は違うけど...\n\n■状況\n└転職は年内に...",
    )
    st.session_state.raw_memo = memo

    if st.button("AI解析実行", type="primary", disabled=not memo.strip()):
        with st.spinner("AIがメモを解析中..."):
            try:
                profile = parse_candidate_memo(memo)
                st.session_state.candidate_profile = profile
                st.success("解析完了！右側で結果を確認・編集してください。")
            except Exception as e:
                st.error(f"解析エラー: {e}")

with col_right:
    st.subheader("抽出結果")

    if st.session_state.candidate_profile is None:
        st.info("左側にメモを入力して「AI解析実行」を押してください。")
    else:
        profile = st.session_state.candidate_profile

        with st.form("edit_profile"):
            edited = {}
            for key, field in CANDIDATE_FIELDS.items():
                val = profile.get(key, "") or ""
                if field["type"] == "textarea":
                    edited[key] = st.text_area(field["label"], value=str(val), height=100)
                elif field["type"] == "number":
                    edited[key] = st.number_input(
                        field["label"],
                        value=int(val) if val and str(val).isdigit() else 0,
                        min_value=0,
                    )
                else:
                    edited[key] = st.text_input(field["label"], value=str(val))

            col_save, col_match = st.columns(2)
            with col_save:
                if st.form_submit_button("プロフィール保存"):
                    st.session_state.candidate_profile = edited
                    st.success("保存しました！")
            with col_match:
                if st.form_submit_button("マッチング実行 →"):
                    st.session_state.candidate_profile = edited
                    st.switch_page("pages/04_マッチング.py")
