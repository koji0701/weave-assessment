# Engineering Impact Dashboard - PRD

## Project Overview
Build an interactive dashboard analyzing the top 5 most impactful engineers in the PostHog GitHub repository (https://github.com/PostHog/posthog). Target audience: Engineering leaders who need quick insights without reading every PR.

**Time Limit**: 1 hour  
**Deliverable**: One hosted URL with interactive dashboard

---

## Technical Stack (Recommended)
- **Language**: Python 3.9+
- **Data Collection**: PyGithub library
- **Analysis**: Pandas
- **Visualization**: Plotly or Altair
- **Dashboard**: Streamlit
- **Hosting**: Streamlit Cloud (free tier)
- **Package Manager**: uv (never use pip)

---

## Data Collection Requirements

### 1. GitHub API Setup
- Use PyGithub library: `uv add PyGithub`
- Repository: `PostHog/posthog`
- Time window: **Last 6 months** (to keep data manageable)
- GitHub token: Use personal access token for higher rate limits

### 2. Data to Fetch

**Pull Requests:**
- Author
- Title & description
- State (merged only)
- Created date, merged date
- Files changed (list of file paths)
- Additions + deletions (lines of code)
- Number of comments
- Number of reviewers
- Reviews (who reviewed)

**Code Reviews:**
- Reviewer name
- PR being reviewed
- Number of review comments left
- Review state (approved/commented/changes requested)

### 3. Data Filtering
- **Only merged PRs** in last 6 months
- Exclude bots (usernames containing "bot", "dependabot", etc.)
- Exclude PRs with <5 lines changed (likely config/minor fixes)

---

## Impact Metrics Definition

### Metric 1: PR Complexity Score
```python
def calculate_pr_complexity(pr):
    """
    Returns complexity score (0-30 range typically)
    """
    score = 0
    
    # 1. Size component (capped at 10 points)
    lines_changed = pr.additions + pr.deletions
    score += min(lines_changed / 100, 10)
    
    # 2. Breadth - cross-functional work (2 points per unique directory)
    file_paths = [f.filename for f in pr.files]
    unique_dirs = len(set([path.split('/')[0] for path in file_paths]))
    score += unique_dirs * 2
    
    # 3. Discussion intensity (capped at 5 points)
    score += min(pr.comments / 5, 5)
    
    # 4. Review count (1 point per reviewer)
    score += pr.reviews.totalCount
    
    return score
```

### Metric 2: Efficiency Score
```python
def calculate_efficiency(pr):
    """
    Complexity delivered per day
    """
    days_to_merge = (pr.merged_at - pr.created_at).days
    days_to_merge = max(days_to_merge, 0.5)  # Avoid division by zero
    
    complexity = calculate_pr_complexity(pr)
    return complexity / days_to_merge
```

### Metric 3: Author Impact
```python
def calculate_author_impact(engineer_prs):
    """
    Sum of (complexity × efficiency) for all authored PRs
    """
    return sum(
        calculate_pr_complexity(pr) * calculate_efficiency(pr) 
        for pr in engineer_prs
    )
```

### Metric 4: Reviewer Impact
```python
def calculate_reviewer_impact(review_activities):
    """
    Weighted by complexity of PRs reviewed × depth of review
    """
    score = 0
    for review in review_activities:
        pr_complexity = calculate_pr_complexity(review.pr)
        review_depth = review.num_comments  # How thorough was the review
        score += pr_complexity * review_depth
    return score
```

### Metric 5: Total Impact Score
```python
def calculate_total_impact(engineer):
    """
    Weighted composite: authorship weighted 2x, reviewing 3x
    (Reviewing shows leadership/mentorship)
    """
    author_score = calculate_author_impact(engineer.authored_prs)
    reviewer_score = calculate_reviewer_impact(engineer.reviews)
    
    return (author_score * 2) + (reviewer_score * 3)
```

---

## Dashboard Requirements

### Layout Structure
```
Title: "PostHog Engineering Impact Dashboard"
Subtitle: "Top 5 Most Impactful Engineers (Last 6 Months)"

[Filters]
- Date range selector (default: last 6 months)

[Main Visualization]
1. Bar chart: Top 5 engineers by Total Impact Score
   - X-axis: Engineer name
   - Y-axis: Impact score
   - Color-coded bars

2. Breakdown chart: For each top 5 engineer
   - Stacked bar showing: Author Impact vs Reviewer Impact
   - Tooltip: Show actual numbers

3. Metrics cards for each engineer:
   - Total PRs authored
   - Total PRs reviewed
   - Avg complexity of authored PRs
   - Avg complexity of reviewed PRs
   - Efficiency score (avg)

[Details Section]
4. Expandable table: Recent high-impact PRs for each engineer
   - Columns: PR title, complexity score, efficiency, merged date
   - Link to GitHub PR
```

### Interactivity
- Hover tooltips on all charts
- Click on engineer → filter view to show their details
- Clickable PR titles → open in new tab

---

## Implementation Steps (Recommended Order)

1. **Setup** (5 min)
   - Install dependencies
   - Set up GitHub token
   - Create project structure

2. **Data Collection** (15 min)
   - Fetch PRs from last 6 months
   - Fetch review data
   - Store in pandas DataFrame

3. **Data Processing** (15 min)
   - Calculate complexity scores
   - Calculate efficiency scores
   - Aggregate by engineer
   - Rank top 5

4. **Dashboard Creation** (15 min)
   - Streamlit app layout
   - Plotly charts
   - Tables and metrics

5. **Deployment** (10 min)
   - Push to GitHub repo
   - Deploy to Streamlit Cloud
   - Test URL

---

## Deliverables

### 1. Hosted Dashboard URL
- Must be publicly accessible
- No login required

### 2. Approach Description (max 300 characters)
Template:
```
"Analyzed 6 months of PostHog PRs using multi-factor complexity scoring: 
code size, cross-functional breadth, discussion intensity, and review depth. 
Impact combines authorship efficiency with review leadership (3x weighted). 
Built with Python, Plotly, Streamlit."
```

### 3. Code Export
- Share the coding session/code files
- Clean, commented code

---

## Edge Cases to Handle

1. **No data for engineer**: Skip, don't show
2. **Division by zero**: Use max(days, 0.5) for time calculations
3. **Bot accounts**: Filter out usernames containing "bot"
4. **Deleted PRs**: Skip if data incomplete
5. **Rate limiting**: Use authenticated GitHub token, add sleep if needed

---

## Success Criteria

✅ Dashboard loads in <5 seconds  
✅ Shows exactly 5 engineers  
✅ Charts are interactive  
✅ Metrics make intuitive sense  
✅ URL is publicly accessible  
✅ Code is clean and commented  

---

## Example Code Structure

```
engineering-impact-dashboard/
├── app.py                 # Streamlit dashboard
├── data_collector.py      # GitHub API calls
├── metrics.py            # All metric calculations
├── requirements.txt      # Dependencies
└── README.md            # Setup instructions
```

---

## Optional Enhancements (If Time Permits)

- Add time-series trend: Impact over time
- Show team distribution: frontend vs backend engineers
- Add "Rising Star" metric: Engineers with increasing impact
- Export data as CSV

---

## Notes for Implementation

- **Prioritize working over perfect**: Get basic version working first
- **Use caching**: Cache GitHub API responses to avoid re-fetching
- **Test with small dataset first**: Try 100 PRs before processing all
- **Keep it simple**: Don't over-engineer for 1 hour

---

**End of PRD**