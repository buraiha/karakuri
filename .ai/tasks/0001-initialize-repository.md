# Karakuriリポジトリの再作成

- Status: completed
- Depends on: none

## 目的と要求
2026-10-30のユーザー依頼に従い、既存karakuriを最新AIハーネスに基づく新規ローカルGitリポジトリへ置き換える。

## 変更対象
AGENTS.md、.ai/、README.md、.gitignore、新しいGit管理情報。
旧要件・旧履歴は引き継がない。テンプレート保守taskはコピーしない。

## 対象外
アプリ実装、要件の再定義、GitHubの変更、コミット・push・デプロイ。

## 受け入れ条件と検証
共通ハーネスが最新mainと一致し、project.mdが現状を記述し、ローカルリンクが有効で、新規Gitリポジトリに旧履歴がないこと。

## 実施・検証結果

- 最新main c1e83e8と共通ファイル10件のバイト一致を確認。
- Markdownの相対リンクの参照先を確認。
- 新規mainブランチ、コミットなし、remoteなしを確認。
- 旧内容は /private/tmp/karakuri-before-rebuild-20261030.tar.gz に退避。
- アプリ実装がなく、ビルド・動作テストは対象外。
