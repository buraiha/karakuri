# 開発・認証設定

## 現在の構成

Python＋Django 5.2 LTS、django-allauth、SQLite（初期運用。PostgreSQL 17・MySQL 8.4へ切り替え可）、Django Templatesを使用する。アプリ依存は `requirements.lock` に固定する。初期検証環境はPython 3.14.3。Python 3.12〜3.14を設定上許容するが、他バージョンは未検証。

## ローカル起動

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cp .env.example .env
chmod 600 .env
```

`.env` の `DJANGO_SECRET_KEY` を十分長いランダム値へ変更する。`.env` はGit対象外。実値をチャット、画面共有、ログへ貼らない。既存の `.env` をコピーで上書きしない。

初期運用はSQLite。`DB_BACKEND=sqlite`（未指定時もSQLite）、`SQLITE_PATH=.data/db.sqlite3` を使う。相対パスはプロジェクトルート基準。親ディレクトリは必要時に作成する。DBと関連ジャーナルを含む `.data/` はGit対象外。PostgreSQL用パスワードやDBコンテナは不要。

```sh
.venv/bin/python manage.py migrate
chmod 600 .data/db.sqlite3
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

### PostgreSQLへ切り替える場合

`.env` を `DB_BACKEND=postgresql` に変更し、`POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_HOST`、`POSTGRES_PORT` を設定して再起動する。パスワードは `DJANGO_SECRET_KEY` と別のランダム値を使う。

```sh
docker compose up -d db
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Podman Composeがない場合は、次の専用DBを使用できる。

```sh
podman run -d --name karakuri-task0004-db --env-file .env \
  -p 127.0.0.1:55434:5432 \
  -v karakuri_task0004_pgdata:/var/lib/postgresql/data docker.io/library/postgres:17
```

既存コンテナがあれば `podman start karakuri-task0004-db` を使う。ComposeのDBと同時に起動しない。ボリューム削除を伴う停止コマンドは使用しない。

**接続先の切り替えだけではデータは移らない。** DBごとのデータは独立する。稼働中に両方へ分散して書き込まない。接続失敗・不正設定時に別DBへ自動フォールバックしない。

### MySQLへ切り替える場合

Django標準のMySQLバックエンドとmysqlclientを使用する。現在はMySQL 8.4で検証しており、MariaDBや他系列は未検証。SQLite利用時にはMySQLドライバーや開発ライブラリは不要。

MySQL用ドライバーを使う環境には、Cコンパイラー・pkg-config・MySQLクライアント開発ライブラリを用意してからインストールする。Debian/Ubuntuなら `build-essential pkg-config default-libmysqlclient-dev`、macOSならHomebrewの `mysql-client pkg-config` が基本。詳しくは [mysqlclientの公式手順](https://pypi.org/project/mysqlclient/) を参照する。

```sh
.venv/bin/python -m pip install -r requirements-mysql.lock
```

`.env` に次を設定する（秘密値は自身のローカル設定へ保存する）。

```dotenv
DB_BACKEND=mysql
MYSQL_DATABASE=karakuri
MYSQL_USER=karakuri
MYSQL_PASSWORD=replace-with-a-random-mysql-password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=53306
MYSQL_ROOT_PASSWORD=replace-with-another-random-mysql-root-password
```

`MYSQL_ROOT_PASSWORD`は開発コンテナの初期化用であり、Djangoの接続には使わない。ComposeでMySQLだけ起動する場合:

```sh
docker compose --profile mysql up -d mysql
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

SQLiteの`.env`にMySQLパスワードを設定する必要はない。Composeの対象DBを起動する際は、そのDB用の秘密値を設定する。空のパスワードではDB初期化に失敗する。

MySQLデータベースはutf8mb4を使う。接続ごとにstrict modeと新規テーブルのInnoDBを指定し、切り捨て・非トランザクションテーブルによる問題を避ける。既存MySQLのテーブルエンジンを自動変換する処理はない。

**既知のDB差:** allauthのEmailAddressにある条件付き一意制約はMySQLでは作成されず、`models.W036`が2件出る。警告は抑制していない。現在のGoogle専用経路ではUser.emailとSocialAccountのprovider/uidに通常のDB一意制約を適用し、別Google識別子をメール一致だけで紐付けない。これらの重複拒否は実MySQLで試験済み。将来メール変更・複数メール管理を追加する際はEmailAddressの制約差も再評価する。[Django公式のDB仕様](https://docs.djangoproject.com/en/5.2/ref/databases/)

MySQLのテストは別DB `test_karakuri` を作成・削除する。開発用のDB管理者がテストユーザーに、そのDBだけの作成・削除権限を付与する。本番ユーザーにテストDB作成権限を付けない。設定切り替えだけでSQLiteデータは移らない。

### MySQL検証コンテナ

ホストに開発ライブラリを追加せず試験するため、`Dockerfile.mysql-test` を用意している。ビルドコンテキストはロックファイル等に限定し、秘密値・実DB・バックアップをイメージへ含めない。

今回の検証では専用ネットワーク `karakuri-task0004-mysql-net`、専用MySQLコンテナ `karakuri-task0004-mysql`、ボリューム `karakuri_task0004_mysqldata` を使用した。検証完了後、MySQL試験コンテナは停止している（ボリュームは保持）。テスト専用の環境変数ファイルは `.secrets/mysql-test.env`（600、Git対象外）。アプリのGoogleシークレットは渡していない。

```sh
podman build -f Dockerfile.mysql-test -t localhost/karakuri-mysql-test:task0004 .
podman start karakuri-task0004-mysql
podman run --rm --network karakuri-task0004-mysql-net \
  --env-file .secrets/mysql-test.env \
  -v "$PWD/config:/app/config:ro" -v "$PWD/core:/app/core:ro" \
  -v "$PWD/templates:/app/templates:ro" -v "$PWD/static:/app/static:ro" \
  -v "$PWD/manage.py:/app/manage.py:ro" \
  localhost/karakuri-mysql-test:task0004
```

この手順は作成済みの今回のローカル検証環境を再利用するもの。新しい環境では別途専用ネットワーク・DB・テスト権限・秘密設定を準備する。ソースの必要なディレクトリだけを読み取り専用でマウントし、`.env`や`.data/`、`.secrets/`全体をコンテナへマウントしない。

### 現在のSQLiteデータとバックアップ

2026-10-30に書き込みを停止してPostgreSQLから移行した。利用者・Google紐付け・アプリ権限・課金状態・監査・管理操作記録・セッションを含む全エクスポートレコードの一致、SQLite整合性と外部キーを確認済み。元のPostgreSQLと `.secrets/db-backups/postgresql-before-sqlite-20261030-190312.json`（600）を保持している。セッションの14日固定期限も維持している。

今後PostgreSQLへ戻す場合、保持したPostgreSQLはこの切り替え時点の状態であり、その後のSQLite更新は入っていない。書き込みを止め、現在のDBと移行先をバックアップし、新規の移行先へデータを移して整合性を検証してから接続先を切り替える。既存DBへ無条件に `loaddata` しない。

SQLiteの定期バックアップはPythonの `sqlite3.Connection.backup()` など整合性を保つ方法で取得する。稼働中のDB本体だけの単純コピーをバックアップ手順としない。SQLiteは単一ホスト・永続ディスクでの小規模運用を前提とし、同時書き込みが増える場合はPostgreSQLを検討する。

開発サーバーは [ログイン画面](http://127.0.0.1:8000/login/) から利用する。Google設定が空ならログイン不可の案内を表示する。認証を省略する方法は提供しない。

## Google側の登録

開発用は `karakuri-dev`（プロジェクトID: `karakuri-dev-513209`）を使用する。本番用 `karakuri-prd` はリリース時に別途作成する（ユーザー指定）。アプリのホスティング先をGoogle Cloudにする決定ではない。

1. [Google Cloudの開発プロジェクト](https://console.cloud.google.com/auth/overview?project=karakuri-dev-513209) を選択する。リリース時は別途本番用プロジェクトを作成する。
2. Google Auth Platformでアプリ名・サポート連絡先・対象ユーザーを設定する。個人Googleアカウントも許容するため外部向けを基本とする。組織ポリシーは別途確認する。
3. OAuthクライアントを「ウェブアプリケーション」で作成する。
4. 承認済みリダイレクトURIへ `http://127.0.0.1:8000/accounts/google/login/callback/` を登録する。`localhost`でも開く場合は `http://localhost:8000/accounts/google/login/callback/` を別途登録する。ホスト名・ポート・末尾スラッシュまで一致させる。
5. スコープは `openid email profile` の認証に必要な範囲に留める。Gmail・Drive等へのアクセスは要求しない。公開状態やGoogle側の要件に応じてテストユーザー等を設定する。
6. クライアントIDとシークレットをローカル `.env` の `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET` へ保存してサーバーを再起動する。秘密値をGitへ保存しない。
7. 実Googleアカウントでログインし、初回は「承認待ち」になることを確認する。

認証JSONのバックアップは `.secrets/google-oauth-dev.json`（ディレクトリ700、ファイル600、Git対象外）に保存している。`.env`も600にする。Downloadsへ複製を残さない。

本番・共有環境はHTTPSの正式ドメインと別のOAuthクライアントを使う方針。公開先が未決のため本番用URIはまだ登録しない。Googleの登録・公開操作が終わったことと、実認証試験の合格を分けて記録する。

## 初期管理者

Google認証済みアカウントに限り、Google subject（allauthのSocialAccount.uid）を指定して管理者化する。最初のログイン者を自動で管理者にしない。Web管理画面から管理者権限は変更できない。

運用者はローカルで `manage.py shell` を開き、対象のGoogle紐付けを確認する。

```python
from allauth.socialaccount.models import SocialAccount
list(SocialAccount.objects.filter(provider="google").values("uid", "user__email"))
```

対象を確認して以下を実行する。`SUBJECT` は同じ値を2箇所に指定する。

```sh
.venv/bin/python manage.py bootstrap_admin SUBJECT --confirm-subject SUBJECT
```

この操作は全体承認と管理者フラグを設定し、操作記録を残す。パスワードは利用不可にする。アプリ権限は自動付与しない。[管理画面](http://127.0.0.1:8000/admin/) へGoogle認証済みブラウザでアクセスする。

## 検証

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test core --noinput
.venv/bin/python -m pip check
```

テストは選択したDBバックエンドで実行する。SQLiteでは独立したインメモリDBを使い、`.data/db.sqlite3`を変更しない。PostgreSQL・MySQLでは別DB `test_karakuri` を作成・削除するため、テスト実行ユーザーにテストDB作成権限が必要。本番のDB認証情報を使わない。認証の架空状態やGoogle応答のモックはテストコード内に限定する。Googleへの実通信がない試験を、実Google認証済みとは扱わない。

各バックエンドで確認する場合（対応するDB・ドライバー・テストDB権限が必要）:

```sh
DB_BACKEND=sqlite .venv/bin/python manage.py test core --noinput
DB_BACKEND=postgresql .venv/bin/python manage.py test core --noinput
DB_BACKEND=mysql .venv/bin/python manage.py test core --noinput
```

本番相当の設定チェック:

```sh
DJANGO_DEBUG=0 .venv/bin/python manage.py check --deploy
```

本番ではHTTPSリダイレクト、Secure Cookie、HSTSを有効化する。サブドメイン全体のHTTPSと正式ドメインが未確定なのでHSTSのincludeSubDomains・preloadは無効であり、W005・W021は現時点の未決事項として残る。リバースプロキシの信頼設定、ASGI/WSGIサーバー、静的ファイル配信、バックアップはデプロイ前に別途設計・検証する。`runserver`を本番公開しない。

## 更新・脆弱性対応

- Django 5.2のサポート期限とPython・allauthの互換性を確認し、サポート終了前に次系列へ移行する。LTSでもセキュリティパッチ更新は継続する。
- 独立したツール用仮想環境で `pip-audit -r requirements.lock` を実行し、指摘されたバージョンと利用箇所を確認する。
- 更新はローカル仮想環境で行い、`pip freeze > requirements.lock` で固定し直す。変更差分・依存整合と上記テストを確認する。
- Google認証・管理者操作をステージングでも確認し、DB変更とバックアップ・復旧手順を確認したうえで配布する。ロックファイルの更新だけで本番修正済みとは扱わない。

## task0004の検証状態

- PostgreSQL・SQLite・MySQLの空DBからマイグレーション実行済み。
- 認証の模擬往復、アクセス制御、課金と利用許可の独立性、14日固定期限・OAuthアクセスログの秘匿・DB選択設定・日本語と絵文字/JSON・メールとGoogle識別子のDB重複拒否など3DBで各42件の自動テスト合格。
- ローカルのログイン画面（Google未設定時の案内）をブラウザで確認。
- 開発用Google OAuth登録・実Google認証・初回承認待ち表示・初期管理者設定・再ログインをSafariで確認済み。
- 管理画面で開発用アカウントの文章連携アプリを「課金なし・利用許可あり」に設定し、アプリ入口へ進めることを確認済み。
- サーバー再起動後、およびPostgreSQLからSQLiteへのデータ移行後も、既存Googleセッション・利用許可・管理画面アクセスが維持されることを確認済み。
- 保存できなかった初回シークレットは、ユーザー承認を得て無効化済み。現在のローカル設定用シークレットのみ有効。
- 重複したGoogle Cloudプロジェクト `Karakuri` はユーザー指示でシャットダウン済み。削除保留中で2026-11-29以降に完全削除予定。
- 対象iPhone・Windows PCでの操作、本番用登録とデプロイは未確認・未実施。
