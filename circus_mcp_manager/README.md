# Circus MCP Manager - 新しいアーキテクチャ

Circus + MCP プロトコルベースのプロセス管理システム（Domain-Driven Design アーキテクチャ）

## 🏗️ アーキテクチャ概要

このプロジェクトは、Domain-Driven Design (DDD) の原則に基づいて設計された、レイヤー化アーキテクチャを採用しています。

### レイヤー構成

```
circus_mcp_manager/
├── app.py                          # メインアプリケーション（エントリーポイント）
├── src/
│   ├── controller/                 # コントローラー層
│   │   ├── __init__.py
│   │   └── mcp_controller.py       # MCP プロトコル制御
│   ├── service/                    # アプリケーションサービス層
│   │   ├── __init__.py
│   │   ├── process_service.py      # プロセス管理サービス
│   │   └── log_service.py          # ログ処理サービス
│   ├── domain/                     # ドメイン層
│   │   ├── __init__.py
│   │   └── process.py              # ドメインモデル・ビジネスロジック
│   └── infrastructure/             # インフラストラクチャ層
│       ├── __init__.py
│       └── repositories.py         # データアクセス実装
├── config/
│   └── config.yaml                 # 設定ファイル
├── tests/
│   ├── __init__.py
│   └── test_new_architecture.py    # 統合テスト
└── requirements.txt                # 依存関係
```

### 依存関係の方向

```
Controller → Service → Domain ← Infrastructure
```

- **Controller層**: MCP プロトコルの処理、外部インターフェース
- **Service層**: アプリケーションロジック、ユースケース実装
- **Domain層**: ビジネスロジック、ドメインモデル（他の層に依存しない）
- **Infrastructure層**: データアクセス、外部システム連携

## 🚀 主な機能

### 1. プロセス管理
- **プロセス追加・削除**: Circus watcher の動的管理
- **プロセス制御**: 開始・停止・再起動・リロード
- **状態監視**: リアルタイムステータス取得
- **統計情報**: システム全体の統計とメトリクス

### 2. ログ管理
- **リアルタイム処理**: 非同期バックグラウンド処理
- **ログ分類**: レベル別自動分類（ERROR, WARNING, INFO, DEBUG, CRITICAL）
- **アラート機能**: 重要ログの自動検出
- **統計・分析**: ログレベル分布、エラー率分析

### 3. MCP プロトコル対応
- **ツール提供**: プロセス管理・ログ取得ツール
- **リソース公開**: プロセス情報・ログデータのリソース化
- **JSON-RPC 2.0**: 標準的な MCP プロトコル実装

## 🛠️ 技術スタック

### コア技術
- **Python 3.8+**: メイン言語
- **Circus**: プロセス管理デーモン
- **MCP Protocol**: AI エージェント通信プロトコル
- **asyncio**: 非同期処理

### 主要ライブラリ
- `circus`: 公式 Circus クライアントライブラリ
- `pydantic`: データバリデーション
- `pyyaml`: 設定ファイル処理
- `pytest`: テストフレームワーク

## 📦 インストール・セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Circus デーモンの起動

```bash
# Circus 設定ファイルを作成
cat > circus.ini << EOF
[circus]
endpoint = tcp://127.0.0.1:5555
pubsub_endpoint = tcp://127.0.0.1:5556

[watcher:dummy]
cmd = python -c "import time; [time.sleep(1) for _ in iter(int, 1)]"
numprocesses = 1
EOF

# Circus デーモン起動
circusd circus.ini
```

### 3. MCP サーバーの起動

```bash
python app.py
```

## 🔧 設定

[`config/config.yaml`](config/config.yaml) で詳細な設定が可能です：

### 主要設定項目
- **MCP サーバー設定**: プロトコルバージョン、機能
- **Circus 接続設定**: エンドポイント、タイムアウト
- **ログ処理設定**: バックグラウンド処理、保持期間
- **パフォーマンス設定**: 並行処理数、メモリ制限
- **セキュリティ設定**: 許可コマンド、パス制限

## 🧪 テスト

### 統合テストの実行

```bash
# 全テスト実行
pytest tests/test_new_architecture.py -v

# 特定のテストクラス実行
pytest tests/test_new_architecture.py::TestNewArchitectureIntegration -v

# カバレッジ付きテスト
pytest tests/test_new_architecture.py --cov=src --cov-report=html
```

### テスト内容
- **フルスタック統合テスト**: 全レイヤーを通したエンドツーエンドテスト
- **ログ処理統合テスト**: バックグラウンド処理とパフォーマンステスト
- **MCP プロトコルテスト**: プロトコル準拠性テスト
- **ドメインロジックテスト**: ビジネスルール検証
- **アーキテクチャ境界テスト**: レイヤー分離の検証

## 📚 使用方法

### MCP ツールの使用例

#### 1. プロセス管理

```json
// プロセス追加
{
  "method": "tools/call",
  "params": {
    "name": "add_process",
    "arguments": {
      "name": "webapp1",
      "command": "python app.py",
      "working_dir": "/app",
      "num_processes": 2
    }
  }
}

// プロセス開始
{
  "method": "tools/call",
  "params": {
    "name": "start_process",
    "arguments": {
      "name": "webapp1"
    }
  }
}
```

#### 2. ログ取得

```json
// ログ取得
{
  "method": "tools/call",
  "params": {
    "name": "get_logs",
    "arguments": {
      "process_name": "webapp1",
      "limit": 100,
      "level": "ERROR"
    }
  }
}

// ログ統計
{
  "method": "tools/call",
  "params": {
    "name": "get_log_summary",
    "arguments": {
      "process_name": "webapp1"
    }
  }
}
```

### リソースアクセス例

```json
// プロセス情報リソース
{
  "method": "resources/read",
  "params": {
    "uri": "process://webapp1/info"
  }
}

// ログリソース
{
  "method": "resources/read",
  "params": {
    "uri": "logs://webapp1/recent"
  }
}
```

## 🔍 アーキテクチャの詳細

### Domain層 (`src/domain/process.py`)

**責務**: ビジネスロジックとドメインモデル

- `ProcessInfo`, `ProcessConfig`: ドメインエンティティ
- `LogEntry`, `LogLevel`: ログドメインモデル
- `ProcessDomainService`: プロセス関連ビジネスルール
- `LogDomainService`: ログ関連ビジネスルール
- `ProcessRepository`, `LogRepository`: データアクセスインターフェース

### Service層 (`src/service/`)

**責務**: アプリケーションロジックとユースケース

- `ProcessService`: プロセス管理のユースケース実装
- `LogService`: ログ処理のユースケース実装
- Circus クライアントとの連携
- バックグラウンド処理の管理

### Controller層 (`src/controller/mcp_controller.py`)

**責務**: MCP プロトコル処理と外部インターフェース

- MCP プロトコル準拠の実装
- ツール定義とリソース管理
- JSON-RPC 2.0 メッセージ処理
- エラーハンドリングとレスポンス生成

### Infrastructure層 (`src/infrastructure/repositories.py`)

**責務**: データアクセスと外部システム連携

- `InMemoryProcessRepository`: インメモリデータストレージ
- `InMemoryLogRepository`: インメモリログストレージ
- 将来の拡張: ファイルベース、データベースリポジトリ

## 🚀 パフォーマンス最適化

### 1. 非同期処理
- 全ての I/O 操作を非同期化
- バックグラウンドタスクによる並行処理
- キューイングシステムによる負荷分散

### 2. メモリ管理
- ログエントリの自動クリーンアップ
- 設定可能なメモリ制限
- ガベージコレクション最適化

### 3. 接続管理
- Circus クライアントの接続プール
- 自動再接続機能
- タイムアウト設定

## 🔒 セキュリティ

### 1. コマンド制限
- 許可されたコマンドのホワイトリスト
- パス制限による安全な実行環境
- リソース制限の設定

### 2. 入力検証
- Pydantic による厳密なデータバリデーション
- SQL インジェクション対策
- パス トラバーサル対策

## 🔄 拡張性

### 1. リポジトリパターン
- インターフェースベースの設計
- 複数のストレージバックエンド対応
- プラグイン形式での機能拡張

### 2. 設定駆動
- YAML ベースの柔軟な設定
- 環境別設定の対応
- ホットリロード機能

## 📈 監視・運用

### 1. ログ監視
- 構造化ログ出力
- レベル別ログ分類
- アラート機能

### 2. メトリクス
- プロセス統計情報
- パフォーマンスメトリクス
- リソース使用量監視

## 🤝 貢献

### 開発ガイドライン
1. Domain-Driven Design 原則の遵守
2. レイヤー間の依存関係ルールの維持
3. 包括的なテストの作成
4. 設定駆動の機能実装

### コードスタイル
- PEP 8 準拠
- Type hints の使用
- Docstring の記述
- 適切なエラーハンドリング

## 📄 ライセンス

MIT License

## 📞 サポート

問題や質問がある場合は、GitHub Issues でお知らせください。

---

**注意**: このプロジェクトは、従来の基本実装から Domain-Driven Design アーキテクチャに完全に再構築されました。新しいアーキテクチャにより、保守性、テスト容易性、拡張性が大幅に向上しています。