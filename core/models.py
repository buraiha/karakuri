from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Approval(models.TextChoices):
        PENDING = "pending", "承認待ち"
        APPROVED = "approved", "承認済み"
        REJECTED = "rejected", "拒否"

    email = models.EmailField(unique=True)
    approval = models.CharField("利用申請", max_length=10, choices=Approval, default=Approval.PENDING)

    class Meta:
        verbose_name = "利用者"
        verbose_name_plural = "利用者・申請"


class App(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField("アプリ名", max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "アプリ"
        verbose_name_plural = "アプリ"


class AppAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="利用者")
    app = models.ForeignKey(App, on_delete=models.PROTECT, verbose_name="アプリ")
    allowed = models.BooleanField("利用許可", default=False)
    charged = models.BooleanField("課金した", default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "app"], name="unique_user_app")]
        verbose_name = "アプリ利用設定"
        verbose_name_plural = "アプリ利用設定・課金状態"

    def __str__(self):
        return f"{self.user} / {self.app}"


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="audit_actions")
    target = models.CharField(max_length=100)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "管理操作記録"
        verbose_name_plural = "管理操作記録"
