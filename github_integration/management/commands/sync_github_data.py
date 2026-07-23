from django.core.management.base import BaseCommand, CommandError

from github_integration.models import Repository
from github_integration.services import sync_repository, GitHubAPIError


class Command(BaseCommand):
    help = "Sync pull requests and commits from GitHub for one or all repositories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            type=str,
            help="Sync only this repository (its full_name, e.g. 'razorpay/checkout'). "
                 "If omitted, syncs every repository in the DB.",
        )

    def handle(self, *args, **options):
        repo_name = options.get("repo")
        repositories = (
            Repository.objects.filter(full_name=repo_name) if repo_name else Repository.objects.all()
        )

        if repo_name and not repositories.exists():
            raise CommandError(f"No repository registered with full_name='{repo_name}'")

        for repo in repositories:
            self.stdout.write(f"Syncing {repo.full_name} ...")
            try:
                summary = sync_repository(repo)
                self.stdout.write(self.style.SUCCESS(f"  Done: {summary}"))
            except GitHubAPIError as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))
