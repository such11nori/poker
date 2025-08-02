# テキサスホールデム ポーカーゲーム 🃏

Django製のリアルタイムテキサスホールデムポーカーゲームです。AIプレイヤーと対戦可能！

## 🌟 主な機能

- **完全なテキサスホールデム実装** - プリフロップ、フロップ、ターン、リバー、ショーダウン
- **AIプレイヤー対応** 🤖 - 1人でも楽しめる高度なAI
- **正確なゲーム進行** - UTGから時計回り、正しいポジション管理
- **リアルタイムゲーム** - 自動更新でスムーズなプレイ
- **ユーザー認証** - 登録・ログイン機能
- **チップシステム** - 初期チップ1000でスタート

## 🚀 デプロイ情報

このアプリはRender.comにデプロイされています：
- **本番環境**: PostgreSQL使用
- **開発環境**: SQLite使用
- **静的ファイル**: WhiteNoise使用

## セットアップ

1. 仮想環境をアクティベート:
```bash
.venv\Scripts\activate
```

2. 依存パッケージのインストール:
```bash
pip install django pillow
```

3. データベースマイグレーション:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. 管理者ユーザー作成:
```bash
python manage.py createsuperuser
```

5. サーバー起動:
```bash
python manage.py runserver
```

## 📋 使用方法

### オンライン版 
1. [デプロイされたサイト](your-render-url)にアクセス
2. 新規登録またはログイン
3. ゲームを作成または参加
4. **「AI追加」ボタン**でCOMプレイヤーを追加 🤖
5. 最低2人が参加したらゲーム開始
6. ポーカーをお楽しみください！

### ローカル開発

### AI機能 🤖
- **一人でも遊べる**: AIプレイヤーを追加して1人でポーカーを楽しめます
- **スマートなAI**: ハンド強度に基づいた戦略的な判断
- **自動行動**: あなたのアクション後、AIが自動的に行動します
- **複数AI対応**: 複数のAIプレイヤーと同時対戦可能

## 🎮 ゲームルール

- **テキサスホールデム**: 世界で最も人気のポーカーバリアント
- **手札**: 各プレイヤーに2枚の手札
- **コミュニティカード**: 5枚（フロップ3枚 + ターン1枚 + リバー1枚）
- **勝利条件**: 最高の5枚の組み合わせで勝負
- **初期チップ**: 1000チップでスタート
- **ポジション**: 正確なディーラー、SB、BB、UTGの実装

## 🛠 技術スタック

- **バックエンド**: Python 3.13+ / Django 5.2+
- **フロントエンド**: Bootstrap 5 / JavaScript
- **データベース**: PostgreSQL (本番) / SQLite (開発)
- **デプロイ**: Render.com
- **静的ファイル**: WhiteNoise

## 📁 プロジェクト構造

```
poker_pj/
├── manage.py
├── requirements.txt         # 依存パッケージ
├── render.yaml             # Render設定
├── build.sh               # ビルドスクリプト
├── poker_game/            # Django設定
│   ├── settings.py        # 本番/開発環境対応
│   ├── urls.py
│   └── wsgi.py
├── poker/                 # メインアプリ
│   ├── models.py          # ゲーム、プレイヤー、ラウンドモデル
│   ├── views.py           # ゲームロジック
│   ├── services/          # 🔧 サービス層
│   │   ├── game_service.py    # ゲーム管理
│   │   ├── betting_service.py # ベット処理
│   │   ├── ai_service.py      # AI戦略
│   │   └── card_service.py    # カード処理
│   ├── utils/             # ユーティリティ
│   │   └── position_manager.py # ポジション管理
│   └── templates/poker/   # HTMLテンプレート
└── staticfiles/          # 静的ファイル（本番用）
```

## 🚀 デプロイ手順

### 1. GitHubリポジトリ準備
```bash
git add .
git commit -m "Update for Render deployment"
git push origin main
```

### 2. Renderでのデプロイ
1. [Render.com](https://render.com)にログイン
2. **"New +" → "Blueprint"** を選択
3. GitHubリポジトリを選択
4. **YAML file**: `render.yaml` を指定
5. **Apply** をクリック

### 3. 環境変数（自動設定）
- `SECRET_KEY`: 自動生成
- `DATABASE_URL`: PostgreSQL自動連携
- `RENDER`: true

## 🔮 今後の拡張予定

- 🌐 **WebSocketsによるリアルタイム更新**
- 🧠 **高度なAIアルゴリズム**（ブラフ、ポジション戦略）
- 🏆 **トーナメント機能**
- 📊 **詳細な統計情報**
- 💬 **チャット機能**
- ⚙️ **AI難易度設定**
- 🎨 **UI/UXの改善**

## 🐛 既知の問題・修正済み

- ✅ ターン順序の修正（UTG→時計回り）
- ✅ フォールド時の早期終了実装
- ✅ AIの行動ループ最適化
- ✅ ベッティングラウンド完了判定の改善

## 📄 ライセンス

MIT License

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

---

**楽しいポーカーライフを！** 🎰✨
