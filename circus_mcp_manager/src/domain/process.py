"""
Process domain model - プロセス管理のコアビジネスロジック
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path


class ProcessStatus(Enum):
    """プロセスの状態"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    FAILED = "failed"


class LogLevel(Enum):
    """ログレベル"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ProcessConfig:
    """プロセス設定"""

    name: str
    command: str
    working_dir: Path
    num_processes: int = 1
    environment: Dict[str, str] = field(default_factory=dict)
    auto_restart: bool = True
    max_restarts: int = 3
    stdout_log: Optional[Path] = None
    stderr_log: Optional[Path] = None

    def to_circus_config(self) -> Dict[str, Any]:
        """Circus設定形式に変換"""
        config = {
            "cmd": self.command,
            "working_dir": str(self.working_dir),
            "numprocesses": self.num_processes,
            "autostart": True,
            "autorestart": self.auto_restart,
            "max_age": self.max_restarts,
        }

        if self.environment:
            config["env"] = self.environment

        if self.stdout_log:
            config["stdout_stream.class"] = "FileStream"
            config["stdout_stream.filename"] = str(self.stdout_log)

        if self.stderr_log:
            config["stderr_stream.class"] = "FileStream"
            config["stderr_stream.filename"] = str(self.stderr_log)

        return config


@dataclass
class ProcessInfo:
    """プロセス情報"""

    name: str
    status: ProcessStatus
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    restart_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    config: Optional[ProcessConfig] = None

    @property
    def uptime(self) -> Optional[float]:
        """稼働時間（秒）"""
        if self.started_at and self.status == ProcessStatus.RUNNING:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """実行中かどうか"""
        return self.status == ProcessStatus.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "status": self.status.value,
            "pid": self.pid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "restart_count": self.restart_count,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "uptime": self.uptime,
            "is_running": self.is_running,
        }


@dataclass
class LogEntry:
    """ログエントリ"""

    timestamp: datetime
    level: LogLevel
    message: str
    process_name: str
    source: str = "stdout"  # stdout, stderr
    matched_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "process_name": self.process_name,
            "source": self.source,
            "matched_patterns": self.matched_patterns,
            "metadata": self.metadata,
        }


@dataclass
class SystemStats:
    """システム統計情報"""

    total_processes: int
    running_processes: int
    stopped_processes: int
    failed_processes: int
    total_cpu_usage: float
    total_memory_usage: float
    uptime: float
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "total_processes": self.total_processes,
            "running_processes": self.running_processes,
            "stopped_processes": self.stopped_processes,
            "failed_processes": self.failed_processes,
            "total_cpu_usage": self.total_cpu_usage,
            "total_memory_usage": self.total_memory_usage,
            "uptime": self.uptime,
            "last_updated": self.last_updated.isoformat(),
        }


class ProcessRepository:
    """プロセス情報のリポジトリインターフェース"""

    def get_process(self, name: str) -> Optional[ProcessInfo]:
        """プロセス情報を取得"""
        raise NotImplementedError

    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """全プロセス情報を取得"""
        raise NotImplementedError

    def save_process(self, process_info: ProcessInfo) -> None:
        """プロセス情報を保存"""
        raise NotImplementedError

    def delete_process(self, name: str) -> None:
        """プロセス情報を削除"""
        raise NotImplementedError


class LogRepository:
    """ログ情報のリポジトリインターフェース"""

    def save_log_entry(self, log_entry: LogEntry) -> None:
        """ログエントリを保存"""
        raise NotImplementedError

    def get_logs(
        self,
        process_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """ログエントリを取得"""
        raise NotImplementedError

    def get_log_stats(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """ログ統計を取得"""
        raise NotImplementedError


class ProcessDomainService:
    """プロセス管理のドメインサービス"""

    def __init__(self, process_repo: ProcessRepository):
        self.process_repo = process_repo

    def can_start_process(self, name: str) -> bool:
        """プロセスを開始できるかチェック"""
        process = self.process_repo.get_process(name)
        if not process:
            return False

        return process.status in [ProcessStatus.STOPPED, ProcessStatus.FAILED]

    def can_stop_process(self, name: str) -> bool:
        """プロセスを停止できるかチェック"""
        process = self.process_repo.get_process(name)
        if not process:
            return False

        return process.status in [ProcessStatus.RUNNING, ProcessStatus.STARTING]

    def should_restart_process(self, name: str) -> bool:
        """プロセスを再起動すべきかチェック"""
        process = self.process_repo.get_process(name)
        if not process or not process.config:
            return False

        return (
            process.status == ProcessStatus.FAILED
            and process.config.auto_restart
            and process.restart_count < process.config.max_restarts
        )

    def calculate_system_stats(self) -> SystemStats:
        """システム統計を計算"""
        processes = self.process_repo.get_all_processes()

        total_processes = len(processes)
        running_processes = sum(
            1 for p in processes.values() if p.status == ProcessStatus.RUNNING
        )
        stopped_processes = sum(
            1 for p in processes.values() if p.status == ProcessStatus.STOPPED
        )
        failed_processes = sum(
            1 for p in processes.values() if p.status == ProcessStatus.FAILED
        )

        total_cpu_usage = sum(p.cpu_usage for p in processes.values())
        total_memory_usage = sum(p.memory_usage for p in processes.values())

        # システム稼働時間（最初に開始されたプロセスから計算）
        running_processes_list = [p for p in processes.values() if p.started_at]
        if running_processes_list:
            earliest_start = min(p.started_at for p in running_processes_list)
            uptime = (datetime.now() - earliest_start).total_seconds()
        else:
            uptime = 0.0

        return SystemStats(
            total_processes=total_processes,
            running_processes=running_processes,
            stopped_processes=stopped_processes,
            failed_processes=failed_processes,
            total_cpu_usage=total_cpu_usage,
            total_memory_usage=total_memory_usage,
            uptime=uptime,
        )


class LogDomainService:
    """ログ管理のドメインサービス"""

    def __init__(self, log_repo: LogRepository):
        self.log_repo = log_repo

    def classify_log_level(self, message: str) -> LogLevel:
        """ログメッセージからレベルを分類"""
        message_lower = message.lower()

        if any(
            keyword in message_lower
            for keyword in ["error", "exception", "traceback", "failed"]
        ):
            return LogLevel.ERROR
        elif any(keyword in message_lower for keyword in ["warning", "warn"]):
            return LogLevel.WARNING
        elif any(keyword in message_lower for keyword in ["debug"]):
            return LogLevel.DEBUG
        elif any(keyword in message_lower for keyword in ["critical", "fatal"]):
            return LogLevel.CRITICAL
        else:
            return LogLevel.INFO

    def should_alert(self, log_entry: LogEntry) -> bool:
        """アラートを送信すべきかチェック"""
        return log_entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]

    def get_log_summary(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """ログサマリーを取得"""
        return self.log_repo.get_log_stats(process_name)
