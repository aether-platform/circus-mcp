"""
Main application entry point - Circus MCP Manager
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from circus.client import CircusClient

from src.controller.mcp_controller import MCPController
from src.service.process_service import ProcessService
from src.service.log_service import LogService
from src.domain.process import ProcessDomainService, LogDomainService
from src.infrastructure.repositories import (
    InMemoryProcessRepository,
    InMemoryLogRepository,
)
from src.utils.exceptions import CircusManagerError, MCPServerError


# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(
            sys.stderr
        ),  # MCPはstdoutを使用するため、ログはstderrに出力
    ],
)

logger = logging.getLogger(__name__)


class CircusMCPApplication:
    """Circus MCP Manager メインアプリケーション"""

    def __init__(self, circus_endpoint: str = "tcp://127.0.0.1:5555"):
        self.circus_endpoint = circus_endpoint

        # 依存関係を初期化
        self._setup_dependencies()

    def _setup_dependencies(self) -> None:
        """依存関係を設定（DI）"""
        # インフラストラクチャ層
        self.circus_client = CircusClient(endpoint=self.circus_endpoint)
        self.process_repo = InMemoryProcessRepository()
        self.log_repo = InMemoryLogRepository()

        # ドメインサービス
        self.process_domain_service = ProcessDomainService(self.process_repo)
        self.log_domain_service = LogDomainService(self.log_repo)

        # アプリケーションサービス
        self.process_service = ProcessService(
            circus_client=self.circus_client,
            process_repo=self.process_repo,
            domain_service=self.process_domain_service,
        )

        self.log_service = LogService(
            log_repo=self.log_repo, domain_service=self.log_domain_service
        )

        # コントローラー
        self.mcp_controller = MCPController(
            process_service=self.process_service, log_service=self.log_service
        )

    async def start(self) -> None:
        """アプリケーションを開始"""
        try:
            logger.info("Starting Circus MCP Manager")

            # バックグラウンドログ処理を開始
            await self.log_service.start_background_processing()

            # MCPサーバーを開始（メインループ）
            await self.mcp_controller.start()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """リソースをクリーンアップ"""
        try:
            logger.info("Cleaning up resources")

            # バックグラウンド処理を停止
            await self.log_service.stop_background_processing()

            # MCPサーバーを停止
            await self.mcp_controller.stop()

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def get_status(self) -> dict:
        """アプリケーション状態を取得"""
        return {
            "circus_endpoint": self.circus_endpoint,
            "mcp_server": self.mcp_controller.get_server_info(),
            "process_service": self.process_service.get_performance_stats(),
            "log_service": self.log_service.get_processing_stats(),
        }


async def main():
    """メイン関数"""
    # コマンドライン引数からCircusエンドポイントを取得
    circus_endpoint = "tcp://127.0.0.1:5555"
    if len(sys.argv) > 1:
        circus_endpoint = sys.argv[1]

    # アプリケーションを作成して開始
    app = CircusMCPApplication(circus_endpoint=circus_endpoint)

    try:
        await app.start()
    except (CircusManagerError, MCPServerError) as e:
        logger.error(f"Application failed to start: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # asyncioイベントループでメイン関数を実行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
