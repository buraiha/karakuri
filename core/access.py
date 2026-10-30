from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import AppAccess, User


def can_use_app(user, slug):
    return (user.is_authenticated and user.is_active and user.approval == User.Approval.APPROVED
            and AppAccess.objects.filter(user=user, app__slug=slug, allowed=True).exists())


def app_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, slug, *args, **kwargs):
        if not can_use_app(request.user, slug):
            raise PermissionDenied("このアプリの利用権限がありません。")
        return view(request, slug, *args, **kwargs)
    return wrapped
