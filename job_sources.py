"""求人取得ソースのアダプター層"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlparse
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import JOB_COLUMNS
JOB_FIELDS = set(JOB_COLUMNS)


@dataclass
class JobSearchQuery:
    keyword: str
    location: str = ""
    pages: int = 1
    company_sites: list[str] | None = None
    csv_path: str | None = None


class JobSource(Protocol):
    source_id: str
    label: str

    def search(self, query: JobSearchQuery) -> list[dict]:
        ...


def _normalize_job(job: dict, default_source: str) -> dict:
    normalized = {}
    for key in JOB_FIELDS:
        if key in job:
            normalized[key] = job.get(key)
    normalized["source"] = job.get("source") or default_source
    return normalized


class SampleCsvJobSource:
    source_id = "csv_seed"
    label = "ローカルCSV (ブロック耐性高)"

    def search(self, query: JobSearchQuery) -> list[dict]:
        csv_path = query.csv_path or "data/sample_jobs.csv"
        df = pd.read_csv(csv_path)

        kw = (query.keyword or "").strip()
        loc = (query.location or "").strip()

        filtered = df.copy()
        if kw:
            mask_kw = (
                filtered.get("求人タイトル", pd.Series(dtype=str)).fillna("").astype(str).str.contains(kw, case=False)
                | filtered.get("職種", pd.Series(dtype=str)).fillna("").astype(str).str.contains(kw, case=False)
                | filtered.get("仕事内容", pd.Series(dtype=str)).fillna("").astype(str).str.contains(kw, case=False)
            )
            filtered = filtered[mask_kw]

        if loc and "勤務地" in filtered.columns:
            filtered = filtered[filtered["勤務地"].fillna("").astype(str).str.contains(loc, case=False)]

        jobs = []
        for _, r in filtered.iterrows():
            jobs.append(
                _normalize_job(
                    {
                        "company_name": r.get("会社名"),
                        "job_title": r.get("求人タイトル"),
                        "job_type": r.get("職種"),
                        "salary_min": r.get("年収下限（万円）") or r.get("年収下限"),
                        "salary_max": r.get("年収上限（万円）") or r.get("年収上限"),
                        "location": r.get("勤務地"),
                        "overtime_hours": r.get("残業時間"),
                        "work_schedule": r.get("雇用形態"),
                        "description": r.get("仕事内容"),
                        "requirements": r.get("応募条件"),
                        "benefits": r.get("福利厚生"),
                        "source_url": r.get("source_url"),
                        "source": "csv_seed",
                    },
                    "csv_seed",
                )
            )
        return jobs


class CompanySiteJobSource:
    source_id = "company_site"
    label = "企業公式採用ページ"

    _RE_JOB_LINK = re.compile(r"(採用|求人|募集|career|careers|job|jobs|ポジション)", re.IGNORECASE)

    def search(self, query: JobSearchQuery) -> list[dict]:
        sites = [s.strip() for s in (query.company_sites or []) if s.strip()]
        if not sites:
            return []

        keywords = [t for t in re.split(r"[\s　]+", query.keyword or "") if len(t) >= 2]
        rows: list[dict] = []
        seen_urls: set[str] = set()

        for site in sites:
            base = site if site.startswith(("http://", "https://")) else f"https://{site}"
            company_name = self._guess_company_name(base)
            for target in self._candidate_urls(base):
                html = self._safe_get(target)
                if not html:
                    continue
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("a[href]"):
                    href = a.get("href", "").strip()
                    text = a.get_text(" ", strip=True)
                    if not href:
                        continue
                    full_url = urljoin(target, href)
                    if full_url in seen_urls:
                        continue

                    combined = f"{text} {href}"
                    if not self._RE_JOB_LINK.search(combined):
                        continue
                    if keywords and not any(k.lower() in combined.lower() for k in keywords):
                        continue

                    seen_urls.add(full_url)
                    rows.append(
                        _normalize_job(
                            {
                                "company_name": company_name,
                                "job_title": text or "採用ページ",
                                "location": query.location or None,
                                "source_url": full_url,
                                "description": "企業公式サイトから検出",
                                "source": "company_site",
                            },
                            "company_site",
                        )
                    )

        return rows

    def _candidate_urls(self, base: str) -> list[str]:
        paths = ["", "/recruit", "/recruit/", "/careers", "/careers/", "/jobs", "/jobs/"]
        return [urljoin(base, p) for p in paths]

    def _safe_get(self, url: str) -> str | None:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code >= 400:
                return None
            return resp.text
        except requests.RequestException:
            return None

    def _guess_company_name(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host


_SOURCES: dict[str, JobSource] = {
    SampleCsvJobSource.source_id: SampleCsvJobSource(),
}


def list_sources() -> list[tuple[str, str]]:
    return [(sid, src.label) for sid, src in _SOURCES.items()]


def search_jobs_with_sources(query: JobSearchQuery, source_ids: list[str]) -> tuple[list[dict], dict[str, str]]:
    jobs: list[dict] = []
    errors: dict[str, str] = {}

    for sid in source_ids:
        source = _SOURCES.get(sid)
        if source is None:
            errors[sid] = "未対応のソースです"
            continue
        try:
            jobs.extend(source.search(query))
        except Exception as e:
            errors[sid] = str(e)

    # source_url優先で重複除去
    deduped: list[dict] = []
    seen: set[str] = set()
    for job in jobs:
        key = str(job.get("source_url") or "") + "|" + str(job.get("job_title") or "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)

    return deduped, errors
