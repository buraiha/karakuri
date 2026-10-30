import math
from django.contrib.auth import logout
from django.utils import timezone
from django.utils.cache import patch_cache_control


class GoogleSessionMiddleware:
    """Googleログインの証跡と絶対期限を全リクエストで確認する。DEBUGで省略しない。"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            expires = request.session.get("absolute_expires_at")
            valid_deadline = (type(expires) in (int, float) and math.isfinite(expires)
                              and expires > timezone.now().timestamp())
            if not request.session.get("google_authenticated") or not valid_deadline:
                logout(request)
        response = self.get_response(request)
        if request.user.is_authenticated or request.path.startswith(("/admin/", "/api/", "/apps/", "/status/")):
            patch_cache_control(response, private=True, no_store=True)
        return response
