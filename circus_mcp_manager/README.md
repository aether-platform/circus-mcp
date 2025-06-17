# Circus MCP Manager

Circus + MCPプロトコル対応プロセス管理システム

## 概要

Circus MCP Managerは、開発用Webアプリケーション（1-5個）をCircusで管理し、MCPプロトコルを通じてコーディングエージェントから制御可能なシステムです。

## 主要機能

- **プロセス管理**: Circusを使用したプロセスの起動・停止・再起動・ステータス管理
- **MCPプロトコル対応**: Model Context Protocolを通じた外部制御
- **リアルタイムログ監視**: ログパターン分類とストリーミング
- **標準入出力制御**: プロセスへのコマンド送信と出力監視

## システム要件

- Python 3.8以上
- Circus プロセス管理システム
- ZeroMQ (pyzmq)

## インストール

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

または開発環境の場合：

```bash
pip install -e .[dev]
```

### 2. プロジェクト構造の初期化

```bash
python main.py init --create-dirs
```

### 3. 設定ファイルの確認

以下の設定ファイルが正しく配置されていることを確認してください：

- `config/circus.ini` - Circus設定
- `config/log_patterns.yaml` - ログパターン定義
- `config/mcp_config.json` - MCP設定

## 使用方法

### サーバーの起動

```bash
python main.py start
```

### ステータス確認

```bash
python main.py status
```

### 設定の検証

```bash
python main.py validate
```

### ヘルプ

```bash
python main.py --help
```

## 設定

### Circus設定 (config/circus.ini)

```ini
[circus]
check_delay = 5
endpoint = tcp://127.0.0.1:5555
pubsub_endpoint = tcp://127.0.0.1:5556

[watcher:webapp1]
cmd = python app.py
working_dir = /path/to/webapp1
numprocesses = 1
stdout_stream.class = FileStream
stdout_stream.filename = /var/log/webapp1.log
```

### MCP設定 (config/mcp_config.json)

MCPツールとリソースの設定を含みます。詳細は設定ファイルを参照してください。

### ログパターン (config/log_patterns.yaml)

ログ分類用の正規表現パターンを定義します。

## アーキテクチャ

システムは以下の4層構造で構成されています：

1. **MCP Server Layer**: MCPプロトコル処理
2. **Process Management Layer**: Circus管理とログ処理
3. **I/O Controller Layer**: 入出力制御
4. **Circus Core Layer**: プロセス実行環境

## MCPツール

以下のMCPツールが利用可能です：

- `process_control`: プロセスの起動・停止・再起動
- `get_status`: プロセス状態の取得
- `send_input`: プロセスへの標準入力送信
- `get_logs`: ログの取得とフィルタリング

## MCPリソース

以下のMCPリソースが利用可能です：

- `circus://processes`: 管理対象プロセス一覧
- `circus://logs/{process_name}`: プロセス別ログストリーム
- `circus://stats`: システム統計情報
- `circus://config`: 現在の設定情報

## 開発

### テストの実行

```bash
pytest
```

### コードフォーマット

```bash
black src/
```

### 型チェック

```bash
mypy src/
```

## ログ

ログファイルは以下の場所に出力されます：

- `logs/circus_mcp_manager.log`: メインログ
- プロセス別ログ: Circus設定に従って出力

## トラブルシューティング

### Circusデーモンに接続できない

1. Circusデーモンが起動していることを確認
2. `config/circus.ini`のエンドポイント設定を確認
3. ファイアウォール設定を確認

### MCPプロトコルエラー

1. MCP設定ファイルの構文を確認
2. クライアント側の実装を確認
3. ログでエラー詳細を確認

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

## サポート

問題や質問がある場合は、GitHubのIssuesページで報告してください。