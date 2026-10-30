from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from .models import App, AppAccess, AuditEvent, User


def is_manager(request):
    user = request.user
    return (user.is_authenticated and user.is_active and user.is_staff
            and user.approval == User.Approval.APPROVED)


class GoogleAdminSite(AdminSite):
    site_header = "Karakuri 管理"
    site_title = "Karakuri 管理"
    index_title = "利用者とアプリの管理"

    def has_permission(self, request):
        return is_manager(request)

    def login(self, request, extra_context=None):
        if request.user.is_authenticated:
            if self.has_permission(request):
                return redirect("admin:index")
            return HttpResponseForbidden("管理者のみ利用できます。")
        return redirect(reverse("account_login"))

    def logout(self, request, extra_context=None):
        if request.method != "POST":
            return HttpResponseForbidden("POSTが必要です。")
        logout(request)
        return redirect("account_login")


site = GoogleAdminSite(name="admin")


class ManagerAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return is_manager(request)

    def has_view_permission(self, request, obj=None):
        return is_manager(request)

    def has_change_permission(self, request, obj=None):
        return is_manager(request)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        fields = self.audit_fields
        before = {}
        if change:
            old = type(obj).objects.get(pk=obj.pk)
            before = {field: getattr(old, field) for field in fields}
        super().save_model(request, obj, form, change)
        AuditEvent.objects.create(actor=request.user, target=f"{obj._meta.label}:{obj.pk}",
                                  before=before, after={field: getattr(obj, field) for field in fields})


@admin.register(User, site=site)
class UserAdmin(ManagerAdmin):
    fields = ["email", "username", "date_joined", "last_login", "is_staff", "approval"]
    readonly_fields = ["email", "username", "date_joined", "last_login", "is_staff"]
    list_display = ["email", "approval", "is_staff", "date_joined"]
    list_filter = ["approval", "is_staff"]
    search_fields = ["email", "username"]
    audit_fields = ["approval"]


@admin.register(AppAccess, site=site)
class AppAccessAdmin(ManagerAdmin):
    fields = ["user", "app", "charged", "allowed"]
    list_display = ["user", "app", "charged", "allowed"]
    list_filter = ["app", "charged", "allowed"]
    search_fields = ["user__email"]
    audit_fields = ["user_id", "app_id", "charged", "allowed"]

    def get_readonly_fields(self, request, obj=None):
        return ["user", "app"] if obj else []

    def has_add_permission(self, request):
        return is_manager(request)


@admin.register(AuditEvent, site=site)
class AuditAdmin(ManagerAdmin):
    list_display = ["created_at", "actor", "target"]
    readonly_fields = ["created_at", "actor", "target", "before", "after"]

    def has_change_permission(self, request, obj=None):
        return False
