from django.contrib import admin
from .models import Repository, PullRequest, Commit

admin.site.register(Repository)
admin.site.register(PullRequest)
admin.site.register(Commit)
