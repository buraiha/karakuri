from django.urls import path
from allauth.socialaccount.providers.google.views import oauth2_callback, oauth2_login
from core import views
from core.admin import site

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_page, name="account_login"),
    path("logout/", views.logout_view, name="account_logout"),
    path("status/", views.status, name="status"),
    path("accounts/google/login/", views.google_endpoint(oauth2_login), name="google_login"),
    path("accounts/google/login/callback/", views.google_endpoint(oauth2_callback), name="google_callback"),
    path("accounts/social/cancelled/", views.login_cancelled, name="socialaccount_login_cancelled"),
    path("apps/<slug:slug>/", views.app_entry, name="app_entry"),
    path("api/apps/<slug:slug>/", views.app_api, name="app_api"),
    path("admin/", site.urls),
]
