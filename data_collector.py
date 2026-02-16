import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from github import Github


BOT_PATTERNS = ["bot", "dependabot", "renovate", "snyk", "codecov", "github-actions"]
CACHE_DIR = Path(__file__).parent / "cache"


def get_github_client():
    token = st.secrets.get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        st.error("GitHub token not found. Set GITHUB_TOKEN in secrets or environment.")
        st.stop()
    return Github(token, per_page=100)


def is_bot(username: str) -> bool:
    lower = username.lower()
    return any(pattern in lower for pattern in BOT_PATTERNS)


def save_to_file(pr_df: pd.DataFrame, reviews_df: pd.DataFrame, impact_df: pd.DataFrame, days: int):
    CACHE_DIR.mkdir(exist_ok=True)
    metadata = {"fetched_at": datetime.now(timezone.utc).isoformat(), "days": days}
    pr_df.to_json(CACHE_DIR / "pr_data.json", orient="records", date_format="iso")
    reviews_df.to_json(CACHE_DIR / "reviews_data.json", orient="records")
    impact_df.to_json(CACHE_DIR / "impact_results.json", orient="records")
    (CACHE_DIR / "metadata.json").write_text(json.dumps(metadata))


def load_from_file():
    try:
        pr_df = pd.read_json(CACHE_DIR / "pr_data.json", orient="records")
        reviews_df = pd.read_json(CACHE_DIR / "reviews_data.json", orient="records")
        impact_df = pd.read_json(CACHE_DIR / "impact_results.json", orient="records")
        metadata = json.loads((CACHE_DIR / "metadata.json").read_text())
        for col in ["created_at", "merged_at"]:
            if col in pr_df.columns:
                pr_df[col] = pd.to_datetime(pr_df[col], utc=True)
        return pr_df, reviews_df, impact_df, metadata
    except (FileNotFoundError, ValueError):
        return None


def fetch_posthog_data(days: int = 180) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = get_github_client()
    repo = g.get_repo("PostHog/posthog")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pr_records = []
    review_records = []

    pulls = repo.get_pulls(state="closed", sort="updated", direction="desc")

    progress = st.progress(0, text="Fetching PRs from GitHub...")
    count = 0

    for pr in pulls:
        if pr.updated_at < cutoff:
            break

        if not pr.merged_at or pr.merged_at < cutoff:
            continue

        author = pr.user.login if pr.user else None
        if not author or is_bot(author):
            continue

        if (pr.additions + pr.deletions) < 5:
            continue

        pr_records.append({
            "pr_number": pr.number,
            "title": pr.title,
            "author": author,
            "html_url": pr.html_url,
            "created_at": pr.created_at,
            "merged_at": pr.merged_at,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "comments": pr.comments + pr.review_comments,
        })

        try:
            for review in pr.get_reviews():
                reviewer = review.user.login if review.user else None
                if not reviewer or is_bot(reviewer) or reviewer == author:
                    continue
                review_records.append({
                    "pr_number": pr.number,
                    "reviewer": reviewer,
                    "state": review.state,
                })
        except Exception:
            pass

        count += 1
        if count % 10 == 0:
            progress.progress(min(count / 500, 1.0), text=f"Fetched {count} PRs...")

        if count % 100 == 0:
            time.sleep(0.5)

    progress.empty()

    pr_df = pd.DataFrame(pr_records)
    reviews_df = pd.DataFrame(review_records)

    if not pr_df.empty:
        pr_df["created_at"] = pd.to_datetime(pr_df["created_at"], utc=True)
        pr_df["merged_at"] = pd.to_datetime(pr_df["merged_at"], utc=True)

    return pr_df, reviews_df
