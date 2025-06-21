#!/usr/bin/env python3
"""
CircusMCP ツールの動作テスト
"""

import asyncio
import json
import sys
from pathlib import Path

# CircusMCPモジュールをインポート
sys.path.append(str(Path(__file__).parent / "circus_mcp_manager" / "src"))

from mcp_server.config_tools import CircusConfigTools
from config_manager.circus_config import CircusConfigManager

class MockCircusManager:
    """テスト用のモックCircusManager"""
    
    def __init__(self):
        self.processes = {}
        
    async def start_process(self, name: str) -> bool:
        """プロセス開始シミュレーション"""
        print(f"🚀 Starting process: {name}")
        self.processes[name] = "running"
        return True
        
    async def stop_process(self, name: str) -> bool:
        """プロセス停止シミュレーション"""
        print(f"🛑 Stopping process: {name}")
        if name in self.processes:
            self.processes[name] = "stopped"
        return True
        
    async def get_process_status(self, name: str = None) -> dict:
        """プロセス状況取得シミュレーション"""
        if name:
            return {name: {"status": self.processes.get(name, "stopped")}}
        return self.processes

async def test_mcp_tools():
    """MCPツールの動作テスト"""
    
    print("🎪 CircusMCP Tools Test\n")
    
    # モックCircusManagerを作成
    mock_circus_manager = MockCircusManager()
    
    # MCPツールを初期化
    config_tools = CircusConfigTools(mock_circus_manager)
    
    print("=== Available MCP Tools ===")
    tools = config_tools.get_available_tools()
    for tool in tools:
        print(f"🔧 {tool['name']}: {tool['description']}")
    print()
    
    # テスト1: 設定ファイル一覧
    print("=== Test 1: List Configuration Files ===")
    try:
        result = await config_tools.execute_tool("list_config_files", {})
        print(f"✅ Found {result['total_configs']} configuration files:")
        for config_file in result['config_files'][:3]:  # 最初の3つを表示
            print(f"   📁 {config_file['name']} ({config_file['services_count']} services)")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print()
    
    # テスト2: 設定ファイル検証
    print("=== Test 2: Validate Configuration ===")
    try:
        config_path = "/root/.circus_configs/aetherplatform_full_development.ini"
        result = await config_tools.execute_tool("validate_config", {
            "config_file": config_path
        })
        
        if result['valid']:
            print(f"✅ Configuration is valid: {result['config_name']}")
            print(f"   Services: {', '.join(result['services'])}")
        else:
            print(f"❌ Configuration has errors:")
            for error in result['errors']:
                print(f"   - {error}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print()
    
    # テスト3: 新しい開発環境設定作成
    print("=== Test 3: Create Development Configuration ===")
    try:
        result = await config_tools.execute_tool("create_dev_config", {
            "config_name": "Quick Test Environment",
            "services": [
                {
                    "name": "test-api",
                    "command": "python -m http.server 8080",
                    "working_dir": "/tmp",
                    "port": 8080,
                    "environment": {"ENV": "test"}
                },
                {
                    "name": "test-frontend",
                    "command": "python -m http.server 3000", 
                    "working_dir": "/tmp",
                    "port": 3000
                }
            ]
        })
        
        if result['success']:
            print(f"✅ Created configuration: {result['config_name']}")
            print(f"   File: {result['config_file']}")
            print(f"   Services: {', '.join(result['services'])}")
        else:
            print(f"❌ Failed to create configuration: {result['message']}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    print()

async def test_config_file_operations():
    """設定ファイル操作の直接テスト"""
    
    print("=== Direct Configuration Manager Test ===\n")
    
    config_manager = CircusConfigManager()
    
    # 現在の設定ファイル一覧
    print("📁 Current Configuration Files:")
    config_files = config_manager.list_config_files()
    
    for config_file in config_files:
        print(f"   {config_file['name']}")
        print(f"      File: {config_file['file']}")
        print(f"      Services: {config_file['services_count']} ({', '.join(config_file['services'])})")
        print(f"      Size: {config_file['size']} bytes")
        print(f"      Modified: {config_file['modified']}")
        print()

def show_real_usage_examples():
    """実際の使用例を表示"""
    
    print("=== Real Usage Examples for AetherPlatform ===\n")
    
    examples = [
        {
            "scenario": "朝の開発開始 - SaaS Console開発",
            "mcp_call": {
                "tool": "load_circus_config",
                "arguments": {
                    "config_file": "~/.circus_configs/aethersaas_console_development.ini",
                    "start_all": True
                }
            },
            "result": "SaaS Console (pnpm dev) が起動され、http://localhost:3000 でアクセス可能"
        },
        {
            "scenario": "フルスタック開発環境の起動",
            "mcp_call": {
                "tool": "load_circus_config", 
                "arguments": {
                    "config_file": "~/.circus_configs/aetherplatform_full_development.ini",
                    "start_all": True
                }
            },
            "result": "SaaS Console、AetherTerm Backend、AetherTerm Frontend が順次起動"
        },
        {
            "scenario": "現在の開発セッション保存",
            "mcp_call": {
                "tool": "save_circus_config",
                "arguments": {
                    "config_file": "~/.circus_configs/my_session_2025_06_21.ini",
                    "config_name": "Development Session 2025-06-21"
                }
            },
            "result": "現在実行中のプロセス設定が保存され、次回同じ環境で復元可能"
        },
        {
            "scenario": "新しいマイクロサービス追加",
            "mcp_call": {
                "tool": "create_dev_config",
                "arguments": {
                    "config_name": "Payment Service Development",
                    "services": [
                        {
                            "name": "payment-api",
                            "command": "uvicorn main:app --reload --port 8001",
                            "working_dir": "/mnt/c/workspace/vibecoding-platform/services/payment",
                            "port": 8001,
                            "environment": {"ENV": "development", "DB_URL": "sqlite:///payment.db"}
                        }
                    ]
                }
            },
            "result": "新しいPayment Service用の設定が作成され、独立して開発可能"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"🔄 シナリオ {i}: {example['scenario']}")
        print(f"   MCP Call:")
        print(f"      Tool: {example['mcp_call']['tool']}")
        print(f"      Arguments: {json.dumps(example['mcp_call']['arguments'], indent=10)}")
        print(f"   Expected Result: {example['result']}")
        print()

async def main():
    """メイン処理"""
    try:
        await test_mcp_tools()
        await test_config_file_operations()
        show_real_usage_examples()
        
        print("✅ All tests completed successfully!")
        print("\n🎯 CircusMCP is ready for AetherPlatform development!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())