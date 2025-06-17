"""
Process management service - プロセス管理のアプリケーションサービス
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from circus.client import CircusClient
from circus.exc import CallError

from ..domain.process import (
    ProcessInfo, ProcessConfig, ProcessStatus, SystemStats,
    ProcessRepository, ProcessDomainService
)
from ..utils.exceptions import (
    ProcessNotFoundError, ProcessAlreadyRunningError, 
    ProcessNotRunningError, CircusManagerError
)


logger = logging.getLogger(__name__)


class ProcessService:
    """プロセス管理サービス"""
    
    def __init__(
        self, 
        circus_client: CircusClient,
        process_repo: ProcessRepository,
        domain_service: ProcessDomainService
    ):
        self.circus_client = circus_client
        self.process_repo = process_repo
        self.domain_service = domain_service
        self._performance_stats = {
            "commands_sent": 0,
            "commands_failed": 0,
            "last_activity": None,
        }
    
    async def start_process(self, name: str) -> bool:
        """
        プロセスを開始
        
        Args:
            name: プロセス名
            
        Returns:
            成功した場合True
            
        Raises:
            ProcessNotFoundError: プロセスが見つからない場合
            ProcessAlreadyRunningError: プロセスが既に実行中の場合
        """
        # ドメインサービスでビジネスルールをチェック
        if not self.domain_service.can_start_process(name):
            process = self.process_repo.get_process(name)
            if not process:
                raise ProcessNotFoundError(name)
            if process.is_running:
                raise ProcessAlreadyRunningError(name)
        
        try:
            # Circusにコマンド送信
            response = await self._execute_circus_command("start", name=name)
            
            if response and response.get("status") == "ok":
                # プロセス情報を更新
                process = self.process_repo.get_process(name)
                if process:
                    process.status = ProcessStatus.STARTING
                    process.started_at = datetime.now()
                    self.process_repo.save_process(process)
                
                logger.info(f"Started process: {name}")
                return True
            
            logger.error(f"Failed to start process: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error starting process {name}: {str(e)}")
            return False
    
    async def stop_process(self, name: str) -> bool:
        """
        プロセスを停止
        
        Args:
            name: プロセス名
            
        Returns:
            成功した場合True
            
        Raises:
            ProcessNotFoundError: プロセスが見つからない場合
            ProcessNotRunningError: プロセスが実行中でない場合
        """
        # ドメインサービスでビジネスルールをチェック
        if not self.domain_service.can_stop_process(name):
            process = self.process_repo.get_process(name)
            if not process:
                raise ProcessNotFoundError(name)
            if not process.is_running:
                raise ProcessNotRunningError(name)
        
        try:
            # Circusにコマンド送信
            response = await self._execute_circus_command("stop", name=name)
            
            if response and response.get("status") == "ok":
                # プロセス情報を更新
                process = self.process_repo.get_process(name)
                if process:
                    process.status = ProcessStatus.STOPPING
                    process.stopped_at = datetime.now()
                    self.process_repo.save_process(process)
                
                logger.info(f"Stopped process: {name}")
                return True
            
            logger.error(f"Failed to stop process: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error stopping process {name}: {str(e)}")
            return False
    
    async def restart_process(self, name: str) -> bool:
        """
        プロセスを再起動
        
        Args:
            name: プロセス名
            
        Returns:
            成功した場合True
        """
        try:
            # Circusにコマンド送信
            response = await self._execute_circus_command("restart", name=name)
            
            if response and response.get("status") == "ok":
                # プロセス情報を更新
                process = self.process_repo.get_process(name)
                if process:
                    process.status = ProcessStatus.RESTARTING
                    process.started_at = datetime.now()
                    process.restart_count += 1
                    self.process_repo.save_process(process)
                
                logger.info(f"Restarted process: {name}")
                return True
            
            logger.error(f"Failed to restart process: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error restarting process {name}: {str(e)}")
            return False
    
    async def get_process_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        プロセス状態を取得
        
        Args:
            name: 特定のプロセス名、またはNoneで全プロセス
            
        Returns:
            プロセス状態情報
        """
        if name:
            process = self.process_repo.get_process(name)
            if process:
                return {name: process.to_dict()}
            return {}
        else:
            # 全プロセス
            all_processes = self.process_repo.get_all_processes()
            return {name: info.to_dict() for name, info in all_processes.items()}
    
    async def get_process_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        詳細なプロセス統計を取得
        
        Args:
            name: プロセス名
            
        Returns:
            プロセス統計またはNone
        """
        try:
            stats = await self._execute_circus_command("stats", name=name)
            return stats
        except Exception as e:
            logger.error(f"Failed to get stats for {name}: {str(e)}")
            return None
    
    async def add_process(self, name: str, config: ProcessConfig) -> bool:
        """
        新しいプロセス設定を追加
        
        Args:
            name: プロセス名
            config: プロセス設定
            
        Returns:
            成功した場合True
        """
        try:
            # Circusに設定を追加
            circus_config = config.to_circus_config()
            response = await self._execute_circus_command("add", name=name, **circus_config)
            
            if response and response.get("status") == "ok":
                # プロセス情報をリポジトリに保存
                process_info = ProcessInfo(
                    name=name,
                    status=ProcessStatus.STOPPED,
                    config=config
                )
                self.process_repo.save_process(process_info)
                
                logger.info(f"Added new process: {name}")
                return True
            
            logger.error(f"Failed to add process: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error adding process {name}: {str(e)}")
            return False
    
    async def remove_process(self, name: str) -> bool:
        """
        プロセス設定を削除
        
        Args:
            name: プロセス名
            
        Returns:
            成功した場合True
        """
        try:
            # 実行中の場合は停止
            if self.domain_service.can_stop_process(name):
                await self.stop_process(name)
            
            # Circusから削除
            response = await self._execute_circus_command("rm", name=name)
            
            if response and response.get("status") == "ok":
                # リポジトリからも削除
                self.process_repo.delete_process(name)
                
                logger.info(f"Removed process: {name}")
                return True
            
            logger.error(f"Failed to remove process: {name}")
            return False
            
        except Exception as e:
            logger.error(f"Error removing process {name}: {str(e)}")
            return False
    
    async def get_all_process_info(self) -> Dict[str, Any]:
        """
        全プロセス情報をCircusから取得
        
        Returns:
            プロセス情報辞書
        """
        try:
            # Circusからwatcher一覧を取得
            list_response = await self._execute_circus_command("list")
            if not list_response:
                return {}
            
            watchers = list_response.get("watchers", [])
            process_info = {}
            
            # 各watcherの詳細情報を取得
            for watcher in watchers:
                watcher_name = watcher.get("name")
                if watcher_name:
                    stats = await self.get_process_stats(watcher_name)
                    if stats:
                        process_info[watcher_name] = {
                            "watcher_info": watcher,
                            "stats": stats
                        }
            
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to get all process info: {str(e)}")
            return {}
    
    def get_system_stats(self) -> SystemStats:
        """
        システム統計を取得
        
        Returns:
            システム統計情報
        """
        return self.domain_service.calculate_system_stats()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        パフォーマンス統計を取得
        
        Returns:
            パフォーマンス統計
        """
        return self._performance_stats.copy()
    
    async def _execute_circus_command(self, command: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Circusコマンドを実行
        
        Args:
            command: コマンド名
            **kwargs: コマンド引数
            
        Returns:
            レスポンスまたはNone
        """
        try:
            logger.debug(f"Executing Circus command: {command} with args: {kwargs}")
            
            # Circusクライアントでコマンド実行
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.circus_client.call({"command": command, **kwargs})
            )
            
            # パフォーマンス統計を更新
            self._performance_stats["commands_sent"] += 1
            self._performance_stats["last_activity"] = datetime.now()
            
            logger.debug(f"Command {command} response: {response}")
            return response
            
        except CallError as e:
            self._performance_stats["commands_failed"] += 1
            logger.error(f"Circus command error: {str(e)}")
            return None
        except Exception as e:
            self._performance_stats["commands_failed"] += 1
            logger.error(f"Failed to execute command {command}: {str(e)}")
            return None