"""求人サイトスクレイピング"""
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def search_indeed(keyword: str, location: str = "", pages: int = 2) -> list[dict]:
    """Indeed Japanから求人を検索"""
    results = []
    for page in range(pages):
        params = {"q": keyword, "l": location, "start": page * 10}
        url = f"https://jp.indeed.com/jobs?{urlencode(params)}"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Indeed検索エラー (page {page}): {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job_seen_beacon, div.cardOutline, div.result")

        if not cards:
            # フォールバック: 別のセレクタを試す
            cards = soup.select("[data-jk]")

        for card in cards:
            job = _parse_indeed_card(card)
            if job and job.get("job_title"):
                results.append(job)

        if page < pages - 1:
            time.sleep(1.5)  # レート制限

    return results


def _parse_indeed_card(card) -> dict:
    """Indeed求人カードからデータを抽出"""
    job = {
        "company_name": None,
        "job_title": None,
        "location": None,
        "salary_min": None,
        "salary_max": None,
        "description": None,
        "source_url": None,
        "source": "indeed",
        "job_type": None,
        "overtime_hours": None,
        "work_schedule": None,
        "requirements": None,
        "benefits": None,
    }

    # タイトル
    title_el = card.select_one("h2.jobTitle a, h2 a, a[data-jk]")
    if title_el:
        job["job_title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if href.startswith("/"):
            job["source_url"] = f"https://jp.indeed.com{href}"
        elif href.startswith("http"):
            job["source_url"] = href

    # 会社名
    company_el = card.select_one("[data-testid='company-name'], span.companyName, .company")
    if company_el:
        job["company_name"] = company_el.get_text(strip=True)

    # 勤務地
    location_el = card.select_one("[data-testid='text-location'], div.companyLocation, .location")
    if location_el:
        job["location"] = location_el.get_text(strip=True)

    # 年収
    salary_el = card.select_one(
        "[data-testid='attribute_snippet_testid'], .salary-snippet-container, .salaryText, .metadata .attribute_snippet"
    )
    if salary_el:
        salary_text = salary_el.get_text(strip=True)
        job["salary_min"], job["salary_max"] = _parse_salary(salary_text)

    # 概要
    snippet_el = card.select_one(".job-snippet, [class*='job-snippet'], .summary")
    if snippet_el:
        job["description"] = snippet_el.get_text(strip=True)

    return job


def _parse_salary(text: str) -> tuple:
    """給与テキストから年収の上下限を抽出（万円単位）"""
    if not text:
        return None, None

    # 月給→年収変換
    monthly = re.search(r"月給\s*(\d[\d,]*)", text)
    if monthly:
        val = int(monthly.group(1).replace(",", ""))
        return val * 12 // 10000, None  # 万円換算（概算）

    # 年収レンジ: "400万～600万" や "400万円〜600万円"
    range_match = re.search(r"(\d[\d,]*)\s*万\s*[円～~〜\-－]+\s*(\d[\d,]*)\s*万", text)
    if range_match:
        return int(range_match.group(1).replace(",", "")), int(range_match.group(2).replace(",", ""))

    # 単体: "400万円以上" "年収500万"
    single = re.search(r"(\d[\d,]*)\s*万", text)
    if single:
        return int(single.group(1).replace(",", "")), None

    return None, None


def fetch_job_detail(url: str) -> str:
    """個別求人ページのテキストを取得"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # メインコンテンツを取得
        content = soup.select_one(
            "#jobDescriptionText, .jobsearch-JobComponent-description, "
            "[class*='jobDescription'], main, article"
        )
        if content:
            return content.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)[:5000]
    except requests.RequestException as e:
        return f"ページ取得エラー: {e}"
