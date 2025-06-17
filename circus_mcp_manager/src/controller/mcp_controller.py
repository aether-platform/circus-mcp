"""
MCP Controller - MCPプロトコルのメインコントローラー
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..service.process_service import ProcessService
from ..service.log_service import LogService
from ..domain.process import ProcessConfig, LogLevel
from ..utils.exceptions import MCPServerError, ProcessNotFoundError
from ..utils.helpers import load_config


logger = logging.getLogger(__name__)


class MCPController:
    """MCPプロトコルのメインコントローラー"""

    def __init__(
        self,
        process_service: ProcessService,
        log_service: LogService,
        config_path: Optional[Path] = None,
    ):
        self.process_service = process_service
        self.log_service = log_service
        self.config_path = config_path or Path("config/mcp_config.json")

        # MCP設定を読み込み
        self.config = self._load_mcp_config()

        # サーバー状態
        self._running = False
        self._client_capabilities: Optional[Dict[str, Any]] = None

        # メッセージハンドラーを登録
        self._handlers = self._register_handlers()

    def _load_mcp_config(self) -> Dict[str, Any]:
        """MCP設定を読み込み"""
        try:
            if self.config_path.exists():
                config = load_config(self.config_path, "json")
                logger.info(f"Loaded MCP configuration from {self.config_path}")
                return config
            else:
                logger.warning(f"MCP config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            raise MCPServerError(f"Failed to load MCP configuration: {str(e)}")

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルトMCP設定を取得"""
        return {
            "server": {
                "name": "circus-mcp-manager",
                "version": "1.0.0",
                "description": "Circus Process Manager with MCP Protocol Support",
            },
            "transport": {"type": "stdio"},
        }

    def _register_handlers(self) -> Dict[str, Any]:
        """MCPメッセージハンドラーを登録"""
        return {
            # 初期化
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            # ツール
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            # リソース
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            # ログ
            "logging/setLevel": self._handle_logging_set_level,
        }

    async def start(self) -> None:
        """MCPサーバーを開始"""
        if self._running:
            logger.warning("MCP Server is already running")
            return

        self._running = True
        logger.info("Starting MCP Server")

        try:
            # メインメッセージループを開始
            await self._message_loop()
        except Exception as e:
            logger.error(f"MCP Server error: {str(e)}")
            raise MCPServerError(f"Server error: {str(e)}")
        finally:
            self._running = False

    async def stop(self) -> None:
        """MCPサーバーを停止"""
        self._running = False
        logger.info("MCP Server stopped")

    async def _message_loop(self) -> None:
        """メインメッセージ処理ループ"""
        while self._running:
            try:
                # stdinからメッセージを読み取り
                line = await self._read_message()
                if not line:
                    break

                # JSON-RPCメッセージを解析
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as e:
                    await self._send_error_response(
                        None, -32700, f"Parse error: {str(e)}"
                    )
                    continue

                # メッセージを処理
                await self._process_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message loop: {str(e)}")
                await self._send_error_response(
                    None, -32603, f"Internal error: {str(e)}"
                )

    async def _read_message(self) -> Optional[str]:
        """stdinからメッセージを読み取り"""
        try:
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, sys.stdin.readline)
            return line.strip() if line else None
        except Exception as e:
            logger.error(f"Error reading message: {str(e)}")
            return None

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """受信したMCPメッセージを処理"""
        message_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if not method:
            await self._send_error_response(
                message_id, -32600, "Invalid request: missing method"
            )
            return

        # ハンドラーを検索
        handler = self._handlers.get(method)
        if not handler:
            await self._send_error_response(
                message_id, -32601, f"Method not found: {method}"
            )
            return

        try:
            # ハンドラーを実行
            result = await handler(params)

            # レスポンスを送信
            if message_id is not None:  # 通知には応答しない
                await self._send_response(message_id, result)

        except Exception as e:
            logger.error(f"Handler error for {method}: {str(e)}")
            await self._send_error_response(
                message_id, -32603, f"Internal error: {str(e)}"
            )

    async def _send_response(self, message_id: Any, result: Any) -> None:
        """成功レスポンスを送信"""
        response = {"jsonrpc": "2.0", "id": message_id, "result": result}
        await self._send_message(response)

    async def _send_error_response(
        self, message_id: Any, code: int, message: str
    ) -> None:
        """エラーレスポンスを送信"""
        response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code, "message": message},
        }
        await self._send_message(response)

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """stdoutにメッセージを送信"""
        try:
            json_str = json.dumps(message)
            print(json_str, flush=True)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    # メッセージハンドラー

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """初期化リクエストを処理"""
        self._client_capabilities = params.get("capabilities", {})

        server_config = self.config.get("server", {})

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "logging": {},
            },
            "serverInfo": {
                "name": server_config.get("name", "circus-mcp-manager"),
                "version": server_config.get("version", "1.0.0"),
            },
        }

    async def _handle_initialized(self, params: Dict[str, Any]) -> None:
        """初期化完了通知を処理"""
        logger.info("MCP Server initialized")

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """利用可能なツール一覧を返す"""
        tools = [
            {
                "name": "start_process",
                "description": "Start a process",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Process name"}
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "stop_process",
                "description": "Stop a process",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Process name"}
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "restart_process",
                "description": "Restart a process",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Process name"}
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "get_process_status",
                "description": "Get process status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Process name (optional)",
                        }
                    },
                },
            },
            {
                "name": "get_logs",
                "description": "Get process logs",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "process_name": {
                            "type": "string",
                            "description": "Process name",
                        },
                        "level": {"type": "string", "description": "Log level filter"},
                        "limit": {
                            "type": "integer",
                            "description": "Number of logs to return",
                        },
                    },
                },
            },
            {
                "name": "add_process",
                "description": "Add a new process configuration",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Process name"},
                        "command": {"type": "string", "description": "Command to run"},
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory",
                        },
                        "num_processes": {
                            "type": "integer",
                            "description": "Number of processes",
                        },
                    },
                    "required": ["name", "command", "working_dir"],
                },
            },
        ]

        return {"tools": tools}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ツール呼び出しを処理"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise MCPServerError("Tool name is required")

        # ツールを実行
        result = await self._execute_tool(tool_name, arguments)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, ensure_ascii=False),
                }
            ]
        }

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """利用可能なリソース一覧を返す"""
        resources = [
            {
                "uri": "circus://processes",
                "name": "Process List",
                "description": "List of all managed processes",
                "mimeType": "application/json",
            },
            {
                "uri": "circus://system/stats",
                "name": "System Statistics",
                "description": "System performance statistics",
                "mimeType": "application/json",
            },
            {
                "uri": "circus://logs/recent",
                "name": "Recent Logs",
                "description": "Recent log entries from all processes",
                "mimeType": "application/json",
            },
        ]

        return {"resources": resources}

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """リソースを読み取り"""
        uri = params.get("uri")

        if not uri:
            raise MCPServerError("Resource URI is required")

        # URIに基づいてリソースを取得
        if uri == "circus://processes":
            content = await self.process_service.get_process_status()
        elif uri == "circus://system/stats":
            content = self.process_service.get_system_stats().to_dict()
        elif uri == "circus://logs/recent":
            logs = self.log_service.get_logs(limit=50)
            content = [log.to_dict() for log in logs]
        else:
            raise MCPServerError(f"Unknown resource URI: {uri}")

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(content, indent=2, ensure_ascii=False),
                }
            ]
        }

    async def _handle_logging_set_level(self, params: Dict[str, Any]) -> None:
        """ログレベルを設定"""
        level = params.get("level", "INFO")

        # ログレベルを設定
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger().setLevel(numeric_level)

        logger.info(f"Logging level set to {level}")

    async def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ツールを実行"""
        try:
            if tool_name == "start_process":
                name = arguments.get("name")
                if not name:
                    return {"error": "Process name is required"}

                success = await self.process_service.start_process(name)
                return {
                    "success": success,
                    "message": f"Process {name} {'started' if success else 'failed to start'}",
                }

            elif tool_name == "stop_process":
                name = arguments.get("name")
                if not name:
                    return {"error": "Process name is required"}

                success = await self.process_service.stop_process(name)
                return {
                    "success": success,
                    "message": f"Process {name} {'stopped' if success else 'failed to stop'}",
                }

            elif tool_name == "restart_process":
                name = arguments.get("name")
                if not name:
                    return {"error": "Process name is required"}

                success = await self.process_service.restart_process(name)
                return {
                    "success": success,
                    "message": f"Process {name} {'restarted' if success else 'failed to restart'}",
                }

            elif tool_name == "get_process_status":
                name = arguments.get("name")
                status = await self.process_service.get_process_status(name)
                return {"status": status}

            elif tool_name == "get_logs":
                process_name = arguments.get("process_name")
                level_str = arguments.get("level")
                limit = arguments.get("limit", 100)

                level = None
                if level_str:
                    try:
                        level = LogLevel(level_str.lower())
                    except ValueError:
                        return {"error": f"Invalid log level: {level_str}"}

                logs = self.log_service.get_logs(
                    process_name=process_name, level=level, limit=limit
                )

                return {"logs": [log.to_dict() for log in logs]}

            elif tool_name == "add_process":
                name = arguments.get("name")
                command = arguments.get("command")
                working_dir = arguments.get("working_dir")
                num_processes = arguments.get("num_processes", 1)

                if not all([name, command, working_dir]):
                    return {"error": "name, command, and working_dir are required"}

                config = ProcessConfig(
                    name=name,
                    command=command,
                    working_dir=Path(working_dir),
                    num_processes=num_processes,
                )

                success = await self.process_service.add_process(name, config)
                return {
                    "success": success,
                    "message": f"Process {name} {'added' if success else 'failed to add'}",
                }

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except ProcessNotFoundError as e:
            return {"error": f"Process not found: {str(e)}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": f"Tool execution failed: {str(e)}"}

    def get_server_info(self) -> Dict[str, Any]:
        """サーバー情報を取得"""
        server_config = self.config.get("server", {})

        return {
            "name": server_config.get("name", "circus-mcp-manager"),
            "version": server_config.get("version", "1.0.0"),
            "description": server_config.get("description", ""),
            "running": self._running,
            "client_capabilities": self._client_capabilities,
        }
