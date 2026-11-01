# Karakuri Project Contract

## 概要と開発状態

- プロジェクト名: Karakuri。
- Python＋Django 5.2 LTSを採用。django-allauthのGoogle認証、Django Templates／Admin、SQLiteで初期運用し、PostgreSQL 17・MySQL 8.4へも切り替え可能な共通基盤を実装中。文章送受信は未実装。開発環境で実Google認証とSafariでの管理操作を確認済み。iPhone・Windows実機試験は未確認。
- 再作成後、ユーザーが指定した2026-10-29版PRDを要件正本へ反映した。名称はKarakuriに統一。元資料の設計前提・提案を確定要件へ昇格させない。
- 全機能の利用にGoogle認証を必須とする。全体の利用承認とアプリ別利用権限を分離し、管理者が利用者ごとのアプリ権限をDBで管理する。管理者によるユーザー・アプリ別の課金状態管理と利用可否への反映を含む。課金運用の詳細と決済自動化は未決。基本経路はログイン→アプリ選択→各アプリの機能画面。
- 要件正本は [docs/requirements.md](../docs/requirements.md)。確定要件、設計前提・具体化、提案、未決事項と要件ID・受け入れ条件を管理する。製品動作は未検証。

## 構成と検証

- `AGENTS.md` と `.ai/` はAIの仕事の進め方、`README.md` は概要と導入記録を管理する。
- 個別作業は `.ai/tasks/` に記録する。
- 文書変更では相対リンク、内容の整合、差分の空白エラーを確認する。
- コードは `config/` と `core/`、画面は `templates/` と `static/`。依存は `requirements.lock`。既定DBはSQLite（`.data/db.sqlite3`）、PostgreSQL・MySQL用の開発DBは `compose.yaml`。MySQLドライバーは任意依存 `requirements-mysql.lock`。初期マイグレーションからカスタムUserを使用する。
- セットアップ・Google登録・管理者設定・更新手順は [開発ガイド](../docs/development.md) を参照する。
- 検証: `.venv/bin/python manage.py check`、`makemigrations --check --dry-run`、`test core --noinput`、`pip check`。3バックエンドでテストする。SQLiteは独立したインメモリDB、PostgreSQL・MySQLは専用テストDBを使う。MySQLではallauthの条件付き一意制約にW036が出るため、メール・Google識別子の重複拒否も試験し、警告と制約差を開発ガイドに記録する。
- 14日固定の絶対期限はサーバー側でも検証する。DEBUGやOAuth未設定を理由に認証を回避しない。テストの架空セッションはテストコード内に限定する。
- 課金状態とアプリ利用許可は別項目。課金状態だけで権限を自動付与しない。承認・権限は保護対象リクエストごとにDBで確認し、管理者にも無条件のアプリ権限を付けない。
- Google Cloudは開発用 `karakuri-dev` を使用。本番用 `karakuri-prd` はリリース時に作成する。開発用OAuthクライアントはlocalhost限定。`.env` と `.secrets/` は秘密値のローカル保存先でGit対象外。
- Google登録と実認証試験、自動テストと対象端末での試験は区別する。未実施の検証を完了と報告しない。

## 保護対象と外部操作

- 認証情報、秘密鍵、環境変数の実値、実運用データをリポジトリへ保存しない。
- 公開先は `https://github.com/buraiha/karakuri`。2026-10-30の明示的な依頼で、初期文書・設定のコミットとmainへのpushが承認された。デプロイやGitHub設定変更は含まない。
- コミット、push、デプロイ、通知、課金、外部サービスへの書き込みは明示的な依頼に従う。

## ハーネス参照元

取得元と導入コミット、独自調整は [README.md](../README.md#ハーネス導入記録) を参照する。

## AIによるリリースの窓口

- AIによるリリース専用チャット: 未指定。AIによるリリース前にユーザーへ指定を求める。通常の開発チャットをAIの判断で専用チャットとして扱わない。
- 専用チャットでも対象・操作内容・影響を復唱し、そのリリースへの許可を得てから実行する。
- 人が自分で行う手動リリースはこの規則の対象外。AIが操作を代行する場合は共通規則の対象。
