# ポーカーゲーム（Django）

Djangoで作成されたテキサスホールデムポーカーゲームです。

## 機能

- ユーザー認証（ログイン・新規登録）
- ゲーム作成と参加
- **AIプレイヤー機能** 🤖
- リアルタイムポーカーゲーム
- テキサスホールデムルール
- チップシステム
- ハンド評価
- ゲーム退出機能

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

## 使用方法

1. ブラウザで `http://127.0.0.1:8001` にアクセス
2. 新規登録またはログイン（テスト用: admin/admin123）
3. ホームページでゲームを作成または参加
4. **「AI追加」ボタンでCOMプレイヤーを追加** 🤖
5. 最低2人が参加したらゲーム開始
6. ポーカーをお楽しみください！

### AI機能 🤖
- **一人でも遊べる**: AIプレイヤーを追加して1人でポーカーを楽しめます
- **スマートなAI**: ハンド強度に基づいた戦略的な判断
- **自動行動**: あなたのアクション後、AIが自動的に行動します
- **複数AI対応**: 複数のAIプレイヤーと同時対戦可能

## ゲームルール

- テキサスホールデムポーカー
- 各プレイヤーに2枚の手札
- 5枚のコミュニティカード（フロップ、ターン、リバー）
- 最高の5枚の組み合わせで勝負
- 初期チップ: 1000

## 管理者情報

- ユーザー名: admin
- パスワード: admin123

## プロジェクト構造

```
poker_pj/
├── manage.py
├── poker_game/          # プロジェクト設定
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── poker/               # ポーカーアプリ
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── models.py        # ゲーム、プレイヤー、カードのモデル
    ├── views.py         # ゲームロジックとビュー
    ├── urls.py
    ├── migrations/
    └── templates/poker/ # HTMLテンプレート
        ├── base.html
        ├── home.html
        ├── create_game.html
        └── game_detail.html
```

## 技術仕様

- Python 3.13+
- Django 5.2+
- Bootstrap 5（フロントエンド）
- SQLite（データベース）

## 今後の拡張予定

- WebSocketsによるリアルタイム更新
- より高度なAIアルゴリズム（ブラフ、ポジション戦略）
- トーナメント機能
- より詳細な統計情報
- チャット機能
- AIの難易度設定
