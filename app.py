"""求人マッチングツール - メインエントリ"""
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from db import init_db

load_dotenv(Path(__file__).parent / ".env", override=True)
init_db()

st.set_page_config(
    page_title="求人マッチングツール",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("求人マッチングツール")
st.sidebar.markdown("人材エージェント向け個人ツール")
st.sidebar.markdown("---")

st.title("求人マッチングツール")
st.markdown("""
### 使い方
1. **候補者登録** - 面談メモを貼り付けてAI解析
2. **求人検索** - 外部サイトから求人を検索・取込
3. **求人管理** - ローカルDBの求人を管理
4. **マッチング** - 候補者と求人のマッチング結果表示

左のサイドバーからページを選択してください。
""")

# セッション状態の初期化
if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = None
if "raw_memo" not in st.session_state:
    st.session_state.raw_memo = ""
