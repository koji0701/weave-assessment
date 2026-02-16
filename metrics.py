import pandas as pd


def compute_pr_metrics(pr_df: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
    if pr_df.empty:
        return pr_df.copy()

    df = pr_df.copy()
    lines_changed = df["additions"] + df["deletions"]
    df["size_score"] = (lines_changed / 100).clip(upper=10)
    df["breadth_score"] = (df["changed_files"] * 0.5).clip(upper=10)
    df["discussion_score"] = (df["comments"] / 5).clip(upper=5)

    reviewer_counts = (
        reviews_df.groupby("pr_number")["reviewer"].nunique()
        if not reviews_df.empty
        else pd.Series(dtype=float)
    )
    df["reviewer_count"] = df["pr_number"].map(reviewer_counts).fillna(0)

    df["complexity"] = df["size_score"] + df["breadth_score"] + df["discussion_score"] + df["reviewer_count"]

    days_to_merge = (df["merged_at"] - df["created_at"]).dt.total_seconds() / 86400
    df["days_to_merge"] = days_to_merge.clip(lower=0.5)
    df["efficiency"] = df["complexity"] / df["days_to_merge"]

    return df


def compute_author_impact(pr_metrics: pd.DataFrame) -> pd.DataFrame:
    if pr_metrics.empty:
        return pd.DataFrame(columns=["author", "author_impact", "prs_authored", "avg_complexity", "avg_efficiency"])

    grouped = pr_metrics.groupby("author").agg(
        author_impact=("complexity", lambda x: (x * pr_metrics.loc[x.index, "efficiency"]).sum()),
        prs_authored=("pr_number", "count"),
        avg_complexity=("complexity", "mean"),
        avg_efficiency=("efficiency", "mean"),
    ).reset_index()

    return grouped


def compute_reviewer_impact(pr_metrics: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
    if reviews_df.empty:
        return pd.DataFrame(columns=["reviewer", "reviewer_impact", "prs_reviewed"])

    review_depth = reviews_df.groupby(["pr_number", "reviewer"]).size().reset_index(name="review_depth")

    complexity_map = pr_metrics.set_index("pr_number")["complexity"]
    review_depth["pr_complexity"] = review_depth["pr_number"].map(complexity_map).fillna(0)
    review_depth["review_score"] = review_depth["pr_complexity"] * review_depth["review_depth"]

    grouped = review_depth.groupby("reviewer").agg(
        reviewer_impact=("review_score", "sum"),
        prs_reviewed=("pr_number", "nunique"),
    ).reset_index()

    return grouped


def compute_total_impact(pr_metrics: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
    author_df = compute_author_impact(pr_metrics)
    reviewer_df = compute_reviewer_impact(pr_metrics, reviews_df)

    merged = pd.merge(
        author_df, reviewer_df,
        left_on="author", right_on="reviewer",
        how="outer",
    )

    merged["engineer"] = merged["author"].fillna(merged["reviewer"])
    merged = merged.drop(columns=["author", "reviewer"], errors="ignore")

    for col in ["author_impact", "prs_authored", "avg_complexity", "avg_efficiency", "reviewer_impact", "prs_reviewed"]:
        merged[col] = merged[col].fillna(0)

    merged["total_impact"] = (merged["author_impact"] * 2) + (merged["reviewer_impact"] * 3)
    merged = merged.sort_values("total_impact", ascending=False).reset_index(drop=True)

    return merged
