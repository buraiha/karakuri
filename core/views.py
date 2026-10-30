from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .access import app_required
from .models import App, AppAccess, User


@never_cache
def login_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "login.html", {"google_configured": settings.GOOGLE_AUTH_CONFIGURED})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("account_login")


@login_required
def home(request):
    if request.user.approval != User.Approval.APPROVED:
        return redirect("status")
    apps = App.objects.annotate(allowed=Exists(AppAccess.objects.filter(
        user=request.user, app=OuterRef("pk"), allowed=True))).order_by("id")
    return render(request, "home.html", {"apps": apps})


@login_required
def status(request):
    return render(request, "status.html")


@app_required
def app_entry(request, slug):
    return render(request, "app.html", {"app": App.objects.get(slug=slug)})


@app_required
def app_api(request, slug):
    return JsonResponse({"app": slug, "implemented": False})


def google_endpoint(view):
    def wrapped(request, *args, **kwargs):
        if not settings.GOOGLE_AUTH_CONFIGURED:
            return HttpResponse("Google認証の設定準備中です。", status=503)
        return view(request, *args, **kwargs)
    return wrapped


def login_cancelled(request):
    return render(request, "socialaccount/login_cancelled.html")
