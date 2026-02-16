from datetime import datetime, timezone, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from data_collector import fetch_posthog_data, load_from_file, save_to_file
from metrics import compute_pr_metrics, compute_total_impact

st.set_page_config(page_title="PostHog Engineering Impact", layout="wide")

st.title("PostHog Engineering Impact Dashboard")

with st.sidebar:
    days = st.slider("Time range (days)", min_value=3, max_value=30, value=3, step=1)

    if st.button("Refresh Data"):
        with st.spinner("Fetching data from GitHub..."):
            pr_df, reviews_df = fetch_posthog_data(days=days)
        if not pr_df.empty:
            pr_metrics = compute_pr_metrics(pr_df, reviews_df)
            impact_df = compute_total_impact(pr_metrics, reviews_df)
            save_to_file(pr_df, reviews_df, impact_df, days)
            st.success("Data refreshed!")
            st.rerun()

    with st.expander("Methodology"):
        st.markdown("""
**PR Complexity** = size (lines/100, max 10) + breadth (files×0.5, max 10) + discussion (comments/5, max 5) + unique reviewer count

**Efficiency** = complexity / days to merge

**Author Impact** = Σ(complexity × efficiency) for authored PRs

**Reviewer Impact** = Σ(PR complexity × review depth) for reviews given

**Total Impact** = (author × 2) + (reviewer × 3)

Reviewer impact is weighted higher because thorough code review amplifies team-wide quality.
""")

st.caption(f"Top 5 most impactful engineers in PostHog/posthog — past {days} days")

cached = load_from_file()

if cached is None:
    st.info("No cached data found. Click **Refresh Data** in the sidebar to fetch from GitHub.")
    st.stop()

pr_df, reviews_df, impact_df, metadata = cached

fetched_at = datetime.fromisoformat(metadata["fetched_at"])
age = datetime.now(timezone.utc) - fetched_at
age_hours = age.total_seconds() / 3600
if age_hours < 1:
    age_str = f"{int(age.total_seconds() / 60)} minutes ago"
elif age_hours < 24:
    age_str = f"{age_hours:.0f} hours ago"
else:
    age_str = f"{age_hours / 24:.0f} days ago"

with st.sidebar:
    st.caption(f"Last updated: {age_str}")
    st.caption(f"Cached with {metadata['days']}-day range")

cutoff = datetime.now(timezone.utc) - timedelta(days=days)
filtered_prs = pr_df[pr_df["merged_at"] >= cutoff].copy()
filtered_reviews = reviews_df[reviews_df["pr_number"].isin(filtered_prs["pr_number"])] if not reviews_df.empty else reviews_df

if filtered_prs.empty:
    st.warning(f"No merged PRs found in the last {days} days.")
    st.stop()

if days != metadata.get("days"):
    pr_metrics = compute_pr_metrics(filtered_prs, filtered_reviews)
    impact_df = compute_total_impact(pr_metrics, filtered_reviews)
else:
    pr_metrics = compute_pr_metrics(filtered_prs, filtered_reviews)

top5 = impact_df.head(5)

st.subheader("Top 5 Engineers by Total Impact")
fig_total = px.bar(
    top5, x="engineer", y="total_impact",
    color="engineer",
    hover_data=["author_impact", "reviewer_impact", "prs_authored", "prs_reviewed"],
    labels={"total_impact": "Total Impact Score", "engineer": "Engineer"},
)
fig_total.update_layout(showlegend=False, xaxis_tickangle=-30)
st.plotly_chart(fig_total, use_container_width=True)

st.subheader("Author Impact vs Reviewer Impact")
chart_data = top5.melt(
    id_vars="engineer",
    value_vars=["author_impact", "reviewer_impact"],
    var_name="Impact Type",
    value_name="Score",
)
chart_data["Impact Type"] = chart_data["Impact Type"].map({
    "author_impact": "Author Impact",
    "reviewer_impact": "Reviewer Impact",
})
fig_grouped = px.bar(
    chart_data, x="engineer", y="Score", color="Impact Type",
    barmode="group",
    labels={"engineer": "Engineer", "Score": "Impact Score"},
)
fig_grouped.update_layout(xaxis_tickangle=-30)
st.plotly_chart(fig_grouped, use_container_width=True)

st.subheader("Engineer Metrics")
cols = st.columns(len(top5))
for i, (_, row) in enumerate(top5.iterrows()):
    with cols[i]:
        st.metric(row["engineer"], f"{row['total_impact']:.0f}")
        st.caption(f"PRs authored: {int(row['prs_authored'])}")
        st.caption(f"PRs reviewed: {int(row['prs_reviewed'])}")
        st.caption(f"Avg complexity: {row['avg_complexity']:.1f}")
        st.caption(f"Avg efficiency: {row['avg_efficiency']:.1f}")

st.subheader("Top PRs by Engineer")
for _, row in top5.iterrows():
    engineer = row["engineer"]
    engineer_prs = pr_metrics[pr_metrics["author"] == engineer].nlargest(10, "complexity")

    if engineer_prs.empty:
        continue

    with st.expander(f"{engineer} — Top PRs"):
        display = engineer_prs[["title", "html_url", "complexity", "efficiency", "days_to_merge", "merged_at"]].copy()
        display["PR"] = display.apply(lambda r: f"[{r['title'][:80]}]({r['html_url']})", axis=1)
        display["merged_at"] = display["merged_at"].dt.strftime("%Y-%m-%d")
        display = display.rename(columns={
            "complexity": "Complexity",
            "efficiency": "Efficiency",
            "days_to_merge": "Days to Merge",
            "merged_at": "Merged",
        })
        st.markdown(
            display[["PR", "Complexity", "Efficiency", "Days to Merge", "Merged"]]
            .to_markdown(index=False, floatfmt=".1f"),
            unsafe_allow_html=True,
        )
