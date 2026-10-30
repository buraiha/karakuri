from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import User
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class GoogleOnlyAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False

    def login(self, request, user):
        if not getattr(request, "_google_authenticated", False):
            raise PermissionDenied("Google認証が必要です。")
        super().login(request, user)
        expires = timezone.now() + timedelta(days=14)
        request.session["google_authenticated"] = True
        request.session["absolute_expires_at"] = expires.timestamp()
        request.session.set_expiry(expires)


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.account.provider != "google":
            raise PermissionDenied("Google認証が必要です。")
        verified = any(e.verified and e.email for e in sociallogin.email_addresses)
        if not verified:
            raise PermissionDenied("Googleの検証済みメールアドレスが必要です。")
        if not sociallogin.is_existing and User.objects.filter(email__iexact=sociallogin.user.email).exists():
            raise PermissionDenied("同じメールアドレスのアカウントがあります。管理者にお問い合わせください。")
        request._google_authenticated = True

    def is_open_for_signup(self, request, sociallogin):
        return getattr(request, "_google_authenticated", False)
