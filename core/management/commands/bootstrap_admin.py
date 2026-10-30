from allauth.socialaccount.models import SocialAccount
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import AuditEvent, User


class Command(BaseCommand):
    help = "Google認証済み利用者を初期管理者に設定する（Google subjectで明示指定）。"

    def add_arguments(self, parser):
        parser.add_argument("subject")
        parser.add_argument("--confirm-subject", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        subject = options["subject"]
        if subject != options["confirm_subject"]:
            raise CommandError("確認用subjectが一致しません。")
        try:
            account = SocialAccount.objects.select_related("user").get(provider="google", uid=subject)
        except SocialAccount.DoesNotExist:
            raise CommandError("Google認証済みアカウントが見つかりません。")
        user = User.objects.select_for_update().get(pk=account.user_id)
        before = {"is_staff": user.is_staff, "approval": user.approval}
        user.is_staff = True
        user.approval = User.Approval.APPROVED
        user.set_unusable_password()
        user.save(update_fields=["is_staff", "approval", "password"])
        AuditEvent.objects.create(actor=user, target=f"core.User:{user.pk}", before=before,
                                  after={"is_staff": True, "approval": user.approval, "source": "bootstrap_admin"})
        self.stdout.write(self.style.SUCCESS("管理者を設定しました。"))
