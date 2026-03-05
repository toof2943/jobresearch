"""Ollama（ローカルLLM）でメモ→構造化JSON変換"""
import json
import requests
from config import PROMPTS_DIR

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "gemma3:4b"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _call_ollama(system_prompt: str, user_text: str, max_tokens: int = 2048) -> str:
    """Ollamaにリクエストを送信してテキストを返す"""
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.3},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _call_ollama_json(system_prompt: str, user_text: str) -> dict:
    """Ollamaにリクエストを送信してJSONを返す"""
    text = _call_ollama(system_prompt, user_text)
    # マークダウンコードブロックを除去
    if "```" in text:
        # ```json ... ``` のパターンを抽出
        start = text.find("```")
        end = text.rfind("```")
        if start != end:
            inner = text[start:end + 3]
            inner = inner.split("\n", 1)[1].rsplit("```", 1)[0]
            text = inner
    # JSON部分だけ抽出（前後に余計なテキストがある場合）
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]
    return json.loads(text)


def parse_candidate_memo(memo: str) -> dict:
    """面談メモから候補者プロフィールを抽出"""
    prompt = _load_prompt("extraction_prompt.txt")
    return _call_ollama_json(prompt, memo)


def parse_job_page(page_text: str) -> dict:
    """求人ページのテキストから構造化データを抽出"""
    prompt = _load_prompt("job_parse_prompt.txt")
    return _call_ollama_json(prompt, page_text)


def generate_match_reasoning(candidate: dict, job: dict) -> str:
    """候補者と求人のマッチ理由を生成"""
    system = "あなたは人材紹介エージェントのアシスタントです。候補者と求人のマッチ度について、簡潔に日本語で説明してください。良い点と懸念点の両方を挙げてください。3-5行程度で。"
    user_text = f"【候補者】\n{json.dumps(candidate, ensure_ascii=False, indent=2)}\n\n【求人】\n{json.dumps(job, ensure_ascii=False, indent=2)}"
    return _call_ollama(system, user_text, max_tokens=512)


def generate_search_keywords(candidate: dict) -> list[str]:
    """候補者プロフィールから検索キーワードを生成"""
    system = 'あなたは求人検索のアシスタントです。候補者のプロフィールから、Indeed等の求人サイトで検索するのに最適なキーワードを3つ生成してください。必ずJSON配列のみを返してください。例: ["一般事務 東京 正社員", "営業事務 神奈川", "事務 未経験歓迎"]'
    user_text = json.dumps(candidate, ensure_ascii=False, indent=2)
    text = _call_ollama(system, user_text, max_tokens=256)
    # JSON配列を抽出
    if "```" in text:
        text = text.split("\n", 1)[1].rsplit("```", 1)[0] if text.startswith("```") else text
    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end != -1:
        text = text[bracket_start:bracket_end + 1]
    return json.loads(text)
