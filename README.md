# Karakuri

最新AI Development Harnessを基に初期化した開発リポジトリ。
iPhoneで音声入力した文章をPCのブラウザへ送り、コピーして利用する機能を最初に提供するWebアプリ。利用にはGoogle認証と管理者承認を必須とし、管理者が利用者ごとのアプリ利用権限をデータベースで管理する。管理者はユーザー・アプリ別の課金状態と利用可否も管理する。課金運用の詳細と決済自動化は未決。

ユーザー指定のPRDを要件定義へ反映済み。設計前提・提案・未決事項は区別して管理している。アプリは未実装で、技術構成・開発・テスト・ビルド手順は未整備。

AIの作業入口は [AGENTS.md](AGENTS.md)、プロジェクト固有情報は [.ai/project.md](.ai/project.md)。
要件の正本は [docs/requirements.md](docs/requirements.md)。
画面遷移と管理・データの基本構成は [docs/design.md](docs/design.md)。

## ハーネス導入記録

- 導入日: 2026-10-30
- 取得元: https://github.com/buraiha/ai-development-harness-template
- 最新main確認・導入コミット: `c1e83e834bf1169c498578da2f78872c0b9b1948`
- 共通のAGENTS.md、.ai/README.md、common.md、guides/、tasks/README.mdと.gitignoreを導入。
- README.mdと.ai/project.mdはKarakuri向けに作成。テンプレート自身の保守taskとGit履歴は導入しない。
- 旧リポジトリの要件書・履歴は引き継がず、新しく初期化した。
