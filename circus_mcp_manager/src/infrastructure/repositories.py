"""
Repository implementations - データアクセス層の実装
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict, deque

from ..domain.process import (
    ProcessInfo,
    LogEntry,
    LogLevel,
    ProcessRepository,
    LogRepository,
)


logger = logging.getLogger(__name__)


class InMemoryProcessRepository(ProcessRepository):
    """インメモリプロセスリポジトリ実装"""

    def __init__(self):
        self._processes: Dict[str, ProcessInfo] = {}
        logger.debug("Initialized InMemoryProcessRepository")

    def get_process(self, name: str) -> Optional[ProcessInfo]:
        """プロセス情報を取得"""
        return self._processes.get(name)

    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """全プロセス情報を取得"""
        return self._processes.copy()

    def save_process(self, process_info: ProcessInfo) -> None:
        """プロセス情報を保存"""
        self._processes[process_info.name] = process_info
        logger.debug(f"Saved process info: {process_info.name}")

    def delete_process(self, name: str) -> None:
        """プロセス情報を削除"""
        if name in self._processes:
            del self._processes[name]
            logger.debug(f"Deleted process info: {name}")


class InMemoryLogRepository(LogRepository):
    """インメモリログリポジトリ実装"""

    def __init__(self, max_logs_per_process: int = 10000):
        self._logs: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_logs_per_process)
        )
        self._all_logs: deque = deque(maxlen=max_logs_per_process * 10)  # 全体ログ
        self._max_logs_per_process = max_logs_per_process
        logger.debug("Initialized InMemoryLogRepository")

    def save_log_entry(self, log_entry: LogEntry) -> None:
        """ログエントリを保存"""
        # プロセス別ログに保存
        self._logs[log_entry.process_name].append(log_entry)

        # 全体ログにも保存
        self._all_logs.append(log_entry)

        logger.debug(
            f"Saved log entry for {log_entry.process_name}: {log_entry.level.value}"
        )

    def get_logs(
        self,
        process_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """ログエントリを取得"""
        # ログソースを決定
        if process_name:
            logs = list(self._logs.get(process_name, []))
        else:
            logs = list(self._all_logs)

        # フィルタリング
        filtered_logs = []
        for log in logs:
            # レベルフィルター
            if level and log.level != level:
                continue

            # 時間範囲フィルター
            if start_time and log.timestamp < start_time:
                continue
            if end_time and log.timestamp > end_time:
                continue

            filtered_logs.append(log)

        # 新しい順にソート
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)

        # 制限を適用
        return filtered_logs[:limit]

    def get_log_stats(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """ログ統計を取得"""
        if process_name:
            logs = list(self._logs.get(process_name, []))
        else:
            logs = list(self._all_logs)

        if not logs:
            return {
                "total_entries": 0,
                "level_distribution": {},
                "time_range": {"earliest": None, "latest": None},
            }

        # レベル別カウント
        level_counts = defaultdict(int)
        for log in logs:
            level_counts[log.level.value] += 1

        # 時間範囲
        timestamps = [log.timestamp for log in logs]
        earliest = min(timestamps)
        latest = max(timestamps)

        return {
            "total_entries": len(logs),
            "level_distribution": dict(level_counts),
            "time_range": {
                "earliest": earliest.isoformat(),
                "latest": latest.isoformat(),
            },
        }


class FileBasedProcessRepository(ProcessRepository):
    """ファイルベースプロセスリポジトリ実装（将来の拡張用）"""

    def __init__(self, data_file: str):
        self.data_file = data_file
        self._processes: Dict[str, ProcessInfo] = {}
        self._load_from_file()

    def _load_from_file(self) -> None:
        """ファイルからデータを読み込み"""
        # TODO: JSONファイルからプロセス情報を読み込み
        pass

    def _save_to_file(self) -> None:
        """ファイルにデータを保存"""
        # TODO: JSONファイルにプロセス情報を保存
        pass

    def get_process(self, name: str) -> Optional[ProcessInfo]:
        """プロセス情報を取得"""
        return self._processes.get(name)

    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """全プロセス情報を取得"""
        return self._processes.copy()

    def save_process(self, process_info: ProcessInfo) -> None:
        """プロセス情報を保存"""
        self._processes[process_info.name] = process_info
        self._save_to_file()

    def delete_process(self, name: str) -> None:
        """プロセス情報を削除"""
        if name in self._processes:
            del self._processes[name]
            self._save_to_file()


class DatabaseLogRepository(LogRepository):
    """データベースログリポジトリ実装（将来の拡張用）"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # TODO: データベース接続を初期化

    def save_log_entry(self, log_entry: LogEntry) -> None:
        """ログエントリを保存"""
        # TODO: データベースにログエントリを保存
        pass

    def get_logs(
        self,
        process_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """ログエントリを取得"""
        # TODO: データベースからログエントリを取得
        return []

    def get_log_stats(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """ログ統計を取得"""
        # TODO: データベースからログ統計を取得
        return {}


class CircusConfigRepository:
    """Circus設定リポジトリ"""

    def __init__(self, config_file: str):
        self.config_file = config_file

    def load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        # TODO: circus.iniファイルを読み込み
        pass

    def save_config(self, config: Dict[str, Any]) -> None:
        """設定を保存"""
        # TODO: circus.iniファイルに保存
        pass

    def add_watcher(self, name: str, config: Dict[str, Any]) -> None:
        """watcherを追加"""
        # TODO: 新しいwatcher設定を追加
        pass

    def remove_watcher(self, name: str) -> None:
        """watcherを削除"""
        # TODO: watcher設定を削除
        pass
