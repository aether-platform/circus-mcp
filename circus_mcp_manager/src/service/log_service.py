"""
Log processing service - ログ処理のアプリケーションサービス
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta

from ..domain.process import LogEntry, LogLevel, LogRepository, LogDomainService
from ..utils.exceptions import LogParserError


logger = logging.getLogger(__name__)


class LogService:
    """ログ処理サービス"""
    
    def __init__(
        self,
        log_repo: LogRepository,
        domain_service: LogDomainService
    ):
        self.log_repo = log_repo
        self.domain_service = domain_service
        
        # コールバック管理
        self._callbacks: List[Callable[[LogEntry], None]] = []
        
        # パフォーマンス統計
        self._processing_stats = {
            "total_processed": 0,
            "processing_errors": 0,
            "start_time": datetime.now(),
            "level_counts": {},
            "process_counts": {},
            "processing_rate": 0.0,
        }
        
        # バックグラウンド処理
        self._processing_queue = asyncio.Queue(maxsize=1000)
        self._processing_task: Optional[asyncio.Task] = None
        self._last_stats_update = datetime.now()
    
    async def process_log_line(
        self,
        log_line: str,
        process_name: str = "unknown",
        timestamp: Optional[datetime] = None
    ) -> Optional[LogEntry]:
        """
        ログ行を処理
        
        Args:
            log_line: 生ログ行
            process_name: プロセス名
            timestamp: ログタイムスタンプ
            
        Returns:
            処理されたログエントリ
        """
        try:
            # ログ行をクリーンアップ
            cleaned_line = log_line.strip()
            if not cleaned_line:
                return None
            
            # タイムスタンプが指定されていない場合は現在時刻を使用
            if timestamp is None:
                timestamp = datetime.now()
            
            # ドメインサービスでログレベルを分類
            level = self.domain_service.classify_log_level(cleaned_line)
            
            # ログエントリを作成
            log_entry = LogEntry(
                timestamp=timestamp,
                level=level,
                message=cleaned_line,
                process_name=process_name,
                matched_patterns=[],  # パターンマッチングは後で実装
            )
            
            # リポジトリに保存
            self.log_repo.save_log_entry(log_entry)
            
            # 統計を更新
            self._update_processing_stats(log_entry)
            
            # コールバックを通知
            await self._notify_callbacks(log_entry)
            
            # アラートが必要かチェック
            if self.domain_service.should_alert(log_entry):
                await self._handle_alert(log_entry)
            
            return log_entry
            
        except Exception as e:
            self._processing_stats["processing_errors"] += 1
            logger.error(f"Error processing log line: {str(e)}")
            raise LogParserError(f"Failed to process log line: {str(e)}")
    
    async def process_log_batch(
        self,
        log_lines: List[str],
        process_name: str = "unknown"
    ) -> List[LogEntry]:
        """
        ログ行のバッチを処理
        
        Args:
            log_lines: 生ログ行のリスト
            process_name: プロセス名
            
        Returns:
            処理されたログエントリのリスト
        """
        processed_entries = []
        
        for line in log_lines:
            try:
                entry = await self.process_log_line(line, process_name)
                if entry:
                    processed_entries.append(entry)
            except LogParserError:
                # エラーログを出力済みなので、処理を続行
                continue
        
        return processed_entries
    
    async def process_log_stream(
        self,
        log_stream: asyncio.StreamReader,
        process_name: str = "unknown"
    ) -> None:
        """
        ログストリームを継続的に処理
        
        Args:
            log_stream: 非同期ストリームリーダー
            process_name: プロセス名
        """
        try:
            while True:
                line = await log_stream.readline()
                if not line:
                    break
                
                try:
                    decoded_line = line.decode('utf-8', errors='replace')
                    await self.process_log_line(decoded_line, process_name)
                except Exception as e:
                    logger.error(f"Error processing stream line: {str(e)}")
                    continue
                    
        except asyncio.CancelledError:
            logger.info(f"Log stream processing cancelled for {process_name}")
        except Exception as e:
            logger.error(f"Error in log stream processing: {str(e)}")
            raise LogParserError(f"Stream processing failed: {str(e)}")
    
    def get_logs(
        self,
        process_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """
        ログを取得
        
        Args:
            process_name: プロセス名フィルター
            level: ログレベルフィルター
            start_time: 開始時刻フィルター
            end_time: 終了時刻フィルター
            limit: 取得件数制限
            
        Returns:
            フィルターされたログエントリのリスト
        """
        return self.log_repo.get_logs(
            process_name=process_name,
            level=level,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    def get_log_summary(self, process_name: Optional[str] = None) -> Dict[str, Any]:
        """
        ログサマリーを取得
        
        Args:
            process_name: プロセス名フィルター
            
        Returns:
            ログサマリー統計
        """
        return self.domain_service.get_log_summary(process_name)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        処理統計を取得
        
        Returns:
            処理統計情報
        """
        current_time = datetime.now()
        uptime = current_time - self._processing_stats["start_time"]
        
        stats = self._processing_stats.copy()
        stats.update({
            "uptime_seconds": uptime.total_seconds(),
            "callbacks_registered": len(self._callbacks),
        })
        
        return stats
    
    def add_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """
        ログ処理コールバックを追加
        
        Args:
            callback: コールバック関数
        """
        self._callbacks.append(callback)
        logger.debug(f"Added log callback: {callback.__name__}")
    
    def remove_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """
        ログ処理コールバックを削除
        
        Args:
            callback: 削除するコールバック関数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Removed log callback: {callback.__name__}")
    
    async def start_background_processing(self) -> None:
        """バックグラウンド処理を開始"""
        if self._processing_task and not self._processing_task.done():
            logger.warning("Background processing already running")
            return
        
        self._processing_task = asyncio.create_task(self._background_processor())
        logger.info("Started background log processing")
    
    async def stop_background_processing(self) -> None:
        """バックグラウンド処理を停止"""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Stopped background log processing")
    
    async def queue_log_for_processing(
        self,
        log_line: str,
        process_name: str = "unknown",
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        ログをバックグラウンド処理キューに追加
        
        Args:
            log_line: 生ログ行
            process_name: プロセス名
            timestamp: ログタイムスタンプ
            
        Returns:
            キューに追加できた場合True
        """
        try:
            self._processing_queue.put_nowait((log_line, process_name, timestamp))
            return True
        except asyncio.QueueFull:
            logger.warning("Processing queue is full, dropping log entry")
            return False
    
    def reset_stats(self) -> None:
        """処理統計をリセット"""
        self._processing_stats = {
            "total_processed": 0,
            "processing_errors": 0,
            "start_time": datetime.now(),
            "level_counts": {},
            "process_counts": {},
            "processing_rate": 0.0,
        }
        logger.info("Log processing statistics reset")
    
    async def _background_processor(self) -> None:
        """バックグラウンド処理ループ"""
        try:
            while True:
                try:
                    # キューからログデータを取得
                    log_data = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=1.0
                    )
                    
                    log_line, process_name, timestamp = log_data
                    
                    # ログを処理
                    await self.process_log_line(log_line, process_name, timestamp)
                    
                    # タスク完了をマーク
                    self._processing_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # タイムアウトは正常、処理を続行
                    continue
                except Exception as e:
                    logger.error(f"Error in background processor: {str(e)}")
                    continue
                    
        except asyncio.CancelledError:
            logger.info("Background processor cancelled")
        except Exception as e:
            logger.error(f"Background processor error: {str(e)}")
    
    async def _notify_callbacks(self, log_entry: LogEntry) -> None:
        """
        コールバックに通知
        
        Args:
            log_entry: ログエントリ
        """
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(log_entry)
                else:
                    callback(log_entry)
            except Exception as e:
                logger.error(f"Error in log callback {callback.__name__}: {str(e)}")
    
    def _update_processing_stats(self, log_entry: LogEntry) -> None:
        """
        処理統計を更新
        
        Args:
            log_entry: 処理されたログエントリ
        """
        # 総処理数を更新
        self._processing_stats["total_processed"] += 1
        
        # レベル別カウントを更新
        level = log_entry.level.value
        self._processing_stats["level_counts"][level] = \
            self._processing_stats["level_counts"].get(level, 0) + 1
        
        # プロセス別カウントを更新
        process_name = log_entry.process_name
        self._processing_stats["process_counts"][process_name] = \
            self._processing_stats["process_counts"].get(process_name, 0) + 1
        
        # 処理レートを更新（10秒ごと）
        now = datetime.now()
        if (now - self._last_stats_update).total_seconds() >= 10:
            elapsed = (now - self._processing_stats["start_time"]).total_seconds()
            if elapsed > 0:
                self._processing_stats["processing_rate"] = \
                    self._processing_stats["total_processed"] / elapsed
            self._last_stats_update = now
    
    async def _handle_alert(self, log_entry: LogEntry) -> None:
        """
        アラートを処理
        
        Args:
            log_entry: アラート対象のログエントリ
        """
        # アラート処理の実装（メール送信、Slack通知など）
        logger.warning(f"ALERT: {log_entry.level.value.upper()} in {log_entry.process_name}: {log_entry.message}")
        
        # 将来的にはここで外部通知システムと連携
        # await self.notification_service.send_alert(log_entry)