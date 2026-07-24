from datetime import timedelta

from django.db import models
from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone

from github_integration.models import PullRequest, Commit


def sprint_velocity(team, start_date, end_date):
    prs = PullRequest.objects.filter(
        repository__team=team,
        state="merged",
        merged_at__date__gte=start_date,
        merged_at__date__lte=end_date,
    )
    aggregate = prs.aggregate(
        merged_pr_count=Count("id"),
        total_additions=Sum("additions"),
        total_deletions=Sum("deletions"),
    )
    return {
        "team": team.name,
        "start_date": start_date,
        "end_date": end_date,
        "merged_pr_count": aggregate["merged_pr_count"] or 0,
        "total_additions": aggregate["total_additions"] or 0,
        "total_deletions": aggregate["total_deletions"] or 0,
    }


def average_pr_turnaround(repository, days=30):
    since = timezone.now() - timedelta(days=days)
    prs = PullRequest.objects.filter(
        repository=repository,
        created_at__gte=since,
        first_review_at__isnull=False,
    )
    turnaround_hours = [
        (pr.first_review_at - pr.created_at).total_seconds() / 3600 for pr in prs
    ]
    avg_hours = round(sum(turnaround_hours) / len(turnaround_hours), 2) if turnaround_hours else None

    return {
        "repository": repository.full_name,
        "period_days": days,
        "reviewed_pr_count": len(turnaround_hours),
        "average_turnaround_hours": avg_hours,
    }


def code_churn(repository, days=30):
    since = timezone.now() - timedelta(days=days)
    prs = PullRequest.objects.filter(
        repository=repository, state="merged", merged_at__gte=since
    )
    aggregate = prs.aggregate(
        total_additions=Sum("additions"),
        total_deletions=Sum("deletions"),
        merged_pr_count=Count("id"),
    )
    additions = aggregate["total_additions"] or 0
    deletions = aggregate["total_deletions"] or 0
    return {
        "repository": repository.full_name,
        "period_days": days,
        "merged_pr_count": aggregate["merged_pr_count"] or 0,
        "total_additions": additions,
        "total_deletions": deletions,
        "net_churn": additions + deletions,
    }


def contributor_activity(team, days=30):
    since = timezone.now() - timedelta(days=days)

    commit_counts = (
        Commit.objects.filter(repository__team=team, authored_at__gte=since)
        .values("author_username")
        .annotate(commit_count=Count("id"))
    )
    pr_counts = (
        PullRequest.objects.filter(repository__team=team, state="merged", merged_at__gte=since)
        .values("author_username")
        .annotate(merged_pr_count=Count("id"))
    )

    activity = {}
    for row in commit_counts:
        author = row["author_username"] or "unknown"
        activity.setdefault(author, {"author": author, "commit_count": 0, "merged_pr_count": 0})
        activity[author]["commit_count"] = row["commit_count"]
    for row in pr_counts:
        author = row["author_username"] or "unknown"
        activity.setdefault(author, {"author": author, "commit_count": 0, "merged_pr_count": 0})
        activity[author]["merged_pr_count"] = row["merged_pr_count"]

    return {
        "team": team.name,
        "period_days": days,
        "contributors": sorted(activity.values(), key=lambda x: -x["commit_count"]),
    }


def compare_contributors(team, usernames, days=3650):
    since = timezone.now() - timedelta(days=days)
    results = []
    for username in usernames:
        commit_count = Commit.objects.filter(
            repository__team=team, author_username=username, authored_at__gte=since
        ).count()
        pr_stats = PullRequest.objects.filter(
            repository__team=team, author_username=username, created_at__gte=since
        ).aggregate(
            merged=Count("id", filter=models.Q(state="merged")),
            total=Count("id"),
            additions=Sum("additions"),
            deletions=Sum("deletions"),
        )
        results.append({
            "username": username,
            "commit_count": commit_count,
            "prs_opened": pr_stats["total"] or 0,
            "prs_merged": pr_stats["merged"] or 0,
            "lines_added": pr_stats["additions"] or 0,
            "lines_removed": pr_stats["deletions"] or 0,
        })
    return {"team": team.name, "period_days": days, "comparison": results}


def commit_timeline(repository, days=180):
    since = timezone.now() - timedelta(days=days)
    weekly = (
        Commit.objects.filter(repository=repository, authored_at__gte=since)
        .annotate(week=TruncWeek("authored_at"))
        .values("week")
        .annotate(commit_count=Count("id"))
        .order_by("week")
    )
    return {
        "repository": repository.full_name,
        "period_days": days,
        "weekly_commits": [
            {"week_start": row["week"].date().isoformat(), "commit_count": row["commit_count"]}
            for row in weekly
        ],
    }


def my_stats(user, days=3650):
    from teams.models import Team
    from github_integration.models import Repository

    github_username = getattr(user.profile, "github_username", "") or ""
    since = timezone.now() - timedelta(days=days)
    my_teams = Team.objects.filter(memberships__user=user).distinct()

    if not github_username:
        return {
            "github_username": None,
            "has_github_username": False,
            "message": "Add your GitHub username in settings to see your personal stats.",
        }

    repos = Repository.objects.filter(team__in=my_teams)
    per_repo = []
    total_commits = 0
    for repo in repos:
        commit_count = Commit.objects.filter(
            repository=repo, author_username=github_username, authored_at__gte=since
        ).count()
        pr_stats = PullRequest.objects.filter(
            repository=repo, author_username=github_username, created_at__gte=since
        ).aggregate(
            merged=Count("id", filter=models.Q(state="merged")),
            total=Count("id"),
        )
        if commit_count or pr_stats["total"]:
            per_repo.append({
                "repository": repo.full_name,
                "commits": commit_count,
                "prs_opened": pr_stats["total"] or 0,
                "prs_merged": pr_stats["merged"] or 0,
            })
            total_commits += commit_count

    all_authors = (
        Commit.objects.filter(repository__team__in=my_teams, authored_at__gte=since)
        .values("author_username").annotate(c=Count("id"))
    )
    author_count = all_authors.count() or 1
    team_total_commits = sum(a["c"] for a in all_authors)
    team_avg_commits = round(team_total_commits / author_count, 1)

    return {
        "github_username": github_username,
        "has_github_username": True,
        "period_days": days,
        "total_commits": total_commits,
        "team_average_commits": team_avg_commits,
        "per_repository": per_repo,
    }


def team_flags(team, days=30):
    """
    Auto-generated, supportive check-in prompts for a manager —
    framed as coaching nudges, not punitive callouts. Capped for readability.
    """
    since = timezone.now() - timedelta(days=days)
    flags = []
    repos = team.repositories.all()

    for repo in repos:
        stale_prs = PullRequest.objects.filter(
            repository=repo, state="open", first_review_at__isnull=True,
            created_at__lte=timezone.now() - timedelta(days=3)
        )
        for pr in stale_prs:
            age_days = (timezone.now() - pr.created_at).days
            flags.append({
                "severity": "high" if age_days >= 7 else "medium",
                "type": "stale_pr",
                "message": f"PR #{pr.number} \"{pr.title}\" in {repo.full_name} could use a review — it's been waiting {age_days} days.",
            })

    two_weeks_ago = timezone.now() - timedelta(days=14)
    four_weeks_ago = timezone.now() - timedelta(days=28)
    for repo in repos:
        previously_active = set(
            Commit.objects.filter(repository=repo, authored_at__gte=four_weeks_ago, authored_at__lt=two_weeks_ago)
            .values_list("author_username", flat=True)
        )
        recently_active = set(
            Commit.objects.filter(repository=repo, authored_at__gte=two_weeks_ago)
            .values_list("author_username", flat=True)
        )
        gone_quiet = previously_active - recently_active
        for author in gone_quiet:
            flags.append({
                "severity": "medium",
                "type": "inactive_contributor",
                "message": f"{author} was active on {repo.full_name} recently but has gone quiet the last 2 weeks — might be worth a quick check-in, they could be blocked on something.",
            })

    for repo in repos:
        recent = average_pr_turnaround(repo, days=14)
        older = average_pr_turnaround(repo, days=30)
        if recent["average_turnaround_hours"] and older["average_turnaround_hours"]:
            if recent["average_turnaround_hours"] > older["average_turnaround_hours"] * 1.3:
                flags.append({
                    "severity": "medium",
                    "type": "slow_reviews",
                    "message": f"Reviews on {repo.full_name} are taking a bit longer lately ({recent['average_turnaround_hours']}h vs {older['average_turnaround_hours']}h before) — might be worth checking if reviewers need support.",
                })

    for repo in repos:
        last_merge = PullRequest.objects.filter(repository=repo, state="merged").order_by("-merged_at").first()
        if last_merge and last_merge.merged_at:
            days_since = (timezone.now() - last_merge.merged_at).days
            if days_since >= 7:
                flags.append({
                    "severity": "high" if days_since >= 14 else "medium",
                    "type": "no_recent_merges",
                    "message": f"It's been {days_since} days since the last merge on {repo.full_name} — worth checking if the team's blocked on something.",
                })

    flags.sort(key=lambda f: 0 if f["severity"] == "high" else 1)

    # Cap the display to the 8 most urgent, but keep the true total count
    total_count = len(flags)
    capped_flags = flags[:8]

    return {
        "team": team.name,
        "flag_count": total_count,
        "flags": capped_flags,
        "showing_capped": total_count > len(capped_flags),
    }


def performance_leaderboard(team, days=30, period_label="This Month"):
    """
    Automatically ranks every contributor on the team by a composite score,
    so the manager never has to manually compare people one at a time.
    Bot accounts (usernames ending in [bot]) are excluded from ranking.
    """
    since = timezone.now() - timedelta(days=days)
    repos = team.repositories.all()

    commit_counts = {}
    merged_pr_counts = {}
    active_weeks = {}

    def is_bot(username):
        return username and username.lower().endswith("[bot]")

    for repo in repos:
        commits = Commit.objects.filter(repository=repo, authored_at__gte=since)
        for c in commits:
            author = c.author_username or "unknown"
            if is_bot(author):
                continue
            commit_counts[author] = commit_counts.get(author, 0) + 1
            week_key = c.authored_at.isocalendar()[:2]
            active_weeks.setdefault(author, set()).add(week_key)

        merged_prs = PullRequest.objects.filter(repository=repo, state="merged", merged_at__gte=since)
        for pr in merged_prs:
            author = pr.author_username or "unknown"
            if is_bot(author):
                continue
            merged_pr_counts[author] = merged_pr_counts.get(author, 0) + 1

    all_authors = set(commit_counts) | set(merged_pr_counts)
    leaderboard = []
    for author in all_authors:
        commits = commit_counts.get(author, 0)
        merged = merged_pr_counts.get(author, 0)
        weeks_active = len(active_weeks.get(author, set()))
        score = (commits * 1) + (merged * 5) + (weeks_active * 3)
        leaderboard.append({
            "author": author, "commits": commits, "merged_prs": merged,
            "active_weeks": weeks_active, "score": score,
        })

    leaderboard.sort(key=lambda x: -x["score"])
    for i, entry in enumerate(leaderboard, start=1):
        entry["rank"] = i

    return {"team": team.name, "period_label": period_label, "period_days": days, "leaderboard": leaderboard}