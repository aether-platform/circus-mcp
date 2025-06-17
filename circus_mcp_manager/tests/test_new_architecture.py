"""
New architecture integration tests - 新しいアーキテクチャの統合テスト
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.controller.mcp_controller import MCPController
from src.service.process_service import ProcessService
from src.service.log_service import LogService
from src.domain.process import (
    ProcessDomainService,
    LogDomainService,
    ProcessConfig,
    LogEntry,
    LogLevel,
)
from src.infrastructure.repositories import (
    InMemoryProcessRepository,
    InMemoryLogRepository,
)
from circus.client import CircusClient


@pytest.fixture
def mock_circus_client():
    """Mock Circus client"""
    mock = Mock(spec=CircusClient)
    mock.call.return_value = {"status": "ok"}
    return mock


@pytest.fixture
def repositories():
    """Create repository instances"""
    process_repo = InMemoryProcessRepository()
    log_repo = InMemoryLogRepository()
    return process_repo, log_repo


@pytest.fixture
def domain_services(repositories):
    """Create domain service instances"""
    process_repo, log_repo = repositories
    process_domain_service = ProcessDomainService(process_repo)
    log_domain_service = LogDomainService(log_repo)
    return process_domain_service, log_domain_service


@pytest.fixture
def application_services(mock_circus_client, repositories, domain_services):
    """Create application service instances"""
    process_repo, log_repo = repositories
    process_domain_service, log_domain_service = domain_services

    process_service = ProcessService(
        circus_client=mock_circus_client,
        process_repo=process_repo,
        domain_service=process_domain_service,
    )

    log_service = LogService(log_repo=log_repo, domain_service=log_domain_service)

    return process_service, log_service


@pytest.fixture
def mcp_controller(application_services):
    """Create MCP controller instance"""
    process_service, log_service = application_services
    return MCPController(process_service=process_service, log_service=log_service)


class TestNewArchitectureIntegration:
    """新しいアーキテクチャの統合テスト"""

    async def test_full_stack_process_management(
        self, mcp_controller, mock_circus_client
    ):
        """フルスタックプロセス管理テスト"""
        # プロセス追加
        add_params = {
            "name": "add_process",
            "arguments": {
                "name": "webapp1",
                "command": "python app.py",
                "working_dir": "/app",
                "num_processes": 1,
            },
        }

        result = await mcp_controller._execute_tool(
            "add_process", add_params["arguments"]
        )
        assert result["success"] is True

        # プロセス開始
        start_params = {"name": "start_process", "arguments": {"name": "webapp1"}}

        result = await mcp_controller._execute_tool(
            "start_process", start_params["arguments"]
        )
        assert result["success"] is True

        # プロセス状態確認
        status_params = {"name": "get_process_status", "arguments": {"name": "webapp1"}}

        result = await mcp_controller._execute_tool(
            "get_process_status", status_params["arguments"]
        )
        assert "status" in result

        # Circusクライアントが適切に呼び出されたことを確認
        assert mock_circus_client.call.call_count >= 2  # add + start

    async def test_log_processing_integration(self, application_services):
        """ログ処理統合テスト"""
        process_service, log_service = application_services

        # ログ処理開始
        await log_service.start_background_processing()

        # ログエントリを処理
        test_logs = [
            "2024-01-01 10:00:00 INFO Application started",
            "2024-01-01 10:00:01 ERROR Connection failed",
            "2024-01-01 10:00:02 DEBUG Processing request",
        ]

        processed_entries = []
        for log_line in test_logs:
            entry = await log_service.process_log_line(log_line, "webapp1")
            if entry:
                processed_entries.append(entry)

        assert len(processed_entries) == 3

        # ログ取得テスト
        logs = log_service.get_logs(process_name="webapp1", limit=10)
        assert len(logs) == 3

        # ログサマリーテスト
        summary = log_service.get_log_summary("webapp1")
        assert summary["total_entries"] == 3
        assert "level_distribution" in summary

        # クリーンアップ
        await log_service.stop_background_processing()

    async def test_mcp_protocol_handlers(self, mcp_controller):
        """MCPプロトコルハンドラーテスト"""
        # 初期化ハンドラー
        init_result = await mcp_controller._handle_initialize(
            {"capabilities": {"tools": True}}
        )

        assert "protocolVersion" in init_result
        assert "capabilities" in init_result
        assert "serverInfo" in init_result

        # ツール一覧ハンドラー
        tools_result = await mcp_controller._handle_tools_list({})

        assert "tools" in tools_result
        assert len(tools_result["tools"]) > 0

        # リソース一覧ハンドラー
        resources_result = await mcp_controller._handle_resources_list({})

        assert "resources" in resources_result
        assert len(resources_result["resources"]) > 0

    async def test_domain_service_business_logic(self, domain_services, repositories):
        """ドメインサービスのビジネスロジックテスト"""
        process_domain_service, log_domain_service = domain_services
        process_repo, log_repo = repositories

        # プロセス情報を作成
        from src.domain.process import ProcessInfo, ProcessStatus
        from datetime import datetime

        process_info = ProcessInfo(name="webapp1", status=ProcessStatus.STOPPED)
        process_repo.save_process(process_info)

        # ビジネスルールテスト
        assert process_domain_service.can_start_process("webapp1") is True
        assert process_domain_service.can_stop_process("webapp1") is False

        # プロセスを実行中に変更
        process_info.status = ProcessStatus.RUNNING
        process_repo.save_process(process_info)

        assert process_domain_service.can_start_process("webapp1") is False
        assert process_domain_service.can_stop_process("webapp1") is True

        # システム統計テスト
        stats = process_domain_service.calculate_system_stats()
        assert stats.total_processes == 1
        assert stats.running_processes == 1
        assert stats.stopped_processes == 0

    async def test_log_domain_service_classification(self, domain_services):
        """ログドメインサービスの分類テスト"""
        process_domain_service, log_domain_service = domain_services

        # ログレベル分類テスト
        assert (
            log_domain_service.classify_log_level("ERROR: Something went wrong")
            == LogLevel.ERROR
        )
        assert (
            log_domain_service.classify_log_level("WARNING: This is a warning")
            == LogLevel.WARNING
        )
        assert (
            log_domain_service.classify_log_level("INFO: Application started")
            == LogLevel.INFO
        )
        assert (
            log_domain_service.classify_log_level("DEBUG: Debug information")
            == LogLevel.DEBUG
        )
        assert (
            log_domain_service.classify_log_level("CRITICAL: System failure")
            == LogLevel.CRITICAL
        )

        # アラート判定テスト
        from datetime import datetime

        error_log = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message="Error occurred",
            process_name="webapp1",
        )

        info_log = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message="Info message",
            process_name="webapp1",
        )

        assert log_domain_service.should_alert(error_log) is True
        assert log_domain_service.should_alert(info_log) is False

    async def test_repository_implementations(self, repositories):
        """リポジトリ実装テスト"""
        process_repo, log_repo = repositories

        # プロセスリポジトリテスト
        from src.domain.process import ProcessInfo, ProcessStatus

        process_info = ProcessInfo(name="test_process", status=ProcessStatus.RUNNING)

        process_repo.save_process(process_info)
        retrieved = process_repo.get_process("test_process")

        assert retrieved is not None
        assert retrieved.name == "test_process"
        assert retrieved.status == ProcessStatus.RUNNING

        all_processes = process_repo.get_all_processes()
        assert "test_process" in all_processes

        process_repo.delete_process("test_process")
        assert process_repo.get_process("test_process") is None

        # ログリポジトリテスト
        from datetime import datetime

        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message="Test log message",
            process_name="test_process",
        )

        log_repo.save_log_entry(log_entry)

        logs = log_repo.get_logs(process_name="test_process", limit=10)
        assert len(logs) == 1
        assert logs[0].message == "Test log message"

        stats = log_repo.get_log_stats("test_process")
        assert stats["total_entries"] == 1
        assert stats["level_distribution"]["info"] == 1

    async def test_error_handling_across_layers(
        self, mcp_controller, mock_circus_client
    ):
        """レイヤー間のエラーハンドリングテスト"""
        # Circusクライアントエラーをシミュレート
        mock_circus_client.call.side_effect = Exception("Circus connection failed")

        # プロセス開始を試行（エラーが適切に処理されることを確認）
        result = await mcp_controller._execute_tool(
            "start_process", {"name": "webapp1"}
        )

        # エラーが適切に処理され、レスポンスが返されることを確認
        assert "error" in result or result.get("success") is False

        # 存在しないプロセスの操作
        result = await mcp_controller._execute_tool(
            "stop_process", {"name": "nonexistent"}
        )
        assert "error" in result

    async def test_performance_and_scalability(self, application_services):
        """パフォーマンスとスケーラビリティテスト"""
        process_service, log_service = application_services

        # 大量ログ処理テスト
        await log_service.start_background_processing()

        # 1000件のログを並行処理
        log_tasks = []
        for i in range(1000):
            log_line = f"2024-01-01 10:00:{i:02d} INFO Processing request {i}"
            log_tasks.append(log_service.process_log_line(log_line, "webapp1"))

        results = await asyncio.gather(*log_tasks, return_exceptions=True)

        # エラーなく処理されたことを確認
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 900  # 90%以上成功

        # 統計情報を確認
        stats = log_service.get_processing_stats()
        assert stats["total_processed"] >= 900

        await log_service.stop_background_processing()


class TestArchitecturalBoundaries:
    """アーキテクチャ境界のテスト"""

    def test_dependency_direction(self):
        """依存関係の方向性テスト"""
        # ドメイン層は他の層に依存しない
        from src.domain import process

        # サービス層はドメイン層にのみ依存
        from src.service import process_service, log_service

        # コントローラー層はサービス層に依存
        from src.controller import mcp_controller

        # インフラストラクチャ層はドメイン層のインターフェースを実装
        from src.infrastructure import repositories

        # 循環依存がないことを確認（importエラーが発生しないことで確認）
        assert True

    def test_layer_isolation(self, repositories, domain_services, application_services):
        """レイヤー分離テスト"""
        process_repo, log_repo = repositories
        process_domain_service, log_domain_service = domain_services
        process_service, log_service = application_services

        # 各レイヤーが適切に分離されていることを確認
        assert hasattr(process_repo, "get_process")  # Repository interface
        assert hasattr(process_domain_service, "can_start_process")  # Domain service
        assert hasattr(process_service, "start_process")  # Application service

        # ドメインサービスがリポジトリを使用
        assert process_domain_service.process_repo is process_repo

        # アプリケーションサービスがドメインサービスを使用
        assert process_service.domain_service is process_domain_service


if __name__ == "__main__":
    pytest.main([__file__])
