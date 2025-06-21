#!/usr/bin/env python3
"""
aether-platformプロジェクト用のCircus設定作成テスト
"""

import asyncio
import json
from pathlib import Path
import sys

# CircusMCPモジュールをインポート
sys.path.append(str(Path(__file__).parent / "circus_mcp_manager" / "src"))

from config_manager.circus_config import CircusConfigManager, CircusConfigInfo, WatcherConfig

async def create_aether_platform_configs():
    """aether-platformプロジェクト用の設定を作成"""
    
    config_manager = CircusConfigManager()
    workspace_root = "/mnt/c/workspace/vibecoding-platform"
    
    # 1. SaaS Console開発環境
    saas_services = [
        {
            "name": "saas-console",
            "command": "pnpm dev", 
            "working_dir": f"{workspace_root}/console/frontend",
            "port": 3000,
            "environment": {"NODE_ENV": "development"}
        }
    ]
    
    saas_config = config_manager.create_config_from_services(
        saas_services, 
        "AetherSaaS Console Development"
    )
    
    # 2. IDE Extension開発環境  
    ide_services = [
        {
            "name": "vscode-extension",
            "command": "npm run watch",
            "working_dir": f"{workspace_root}/ide/ide/extension", 
            "environment": {"NODE_ENV": "development"}
        }
    ]
    
    ide_config = config_manager.create_config_from_services(
        ide_services,
        "AetherCoding IDE Extension Development"  
    )
    
    # 3. Terminal (AetherTerm) 開発環境
    terminal_services = [
        {
            "name": "aetherterm-backend",
            "command": "python -m aetherterm.main",
            "working_dir": f"{workspace_root}/ide/terminal/butterfly-with-ai",
            "port": 8765,
            "environment": {"PYTHONPATH": "src"}
        },
        {
            "name": "aetherterm-frontend", 
            "command": "npm run dev",
            "working_dir": f"{workspace_root}/ide/terminal/butterfly-with-ai/frontend",
            "port": 5173
        }
    ]
    
    terminal_config = config_manager.create_config_from_services(
        terminal_services,
        "AetherTerm Development"
    )
    
    # 4. フルスタック開発環境（全体）
    fullstack_services = [
        {
            "name": "saas-console",
            "command": "pnpm dev",
            "working_dir": f"{workspace_root}/console/frontend", 
            "port": 3000,
            "environment": {"NODE_ENV": "development"}
        },
        {
            "name": "aetherterm-backend",
            "command": "python -m aetherterm.main",
            "working_dir": f"{workspace_root}/ide/terminal/butterfly-with-ai",
            "port": 8765,
            "environment": {"PYTHONPATH": "src"}
        },
        {
            "name": "aetherterm-frontend",
            "command": "npm run dev", 
            "working_dir": f"{workspace_root}/ide/terminal/butterfly-with-ai/frontend",
            "port": 5173
        }
    ]
    
    fullstack_config = config_manager.create_config_from_services(
        fullstack_services,
        "AetherPlatform Full Development"
    )
    
    # 設定を保存
    configs = [
        (saas_config, "SaaS Console"),
        (ide_config, "IDE Extension"), 
        (terminal_config, "AetherTerm"),
        (fullstack_config, "Full Stack")
    ]
    
    print("=== Creating AetherPlatform Circus Configurations ===\n")
    
    for config_info, description in configs:
        # 設定検証
        errors = config_manager.validate_config(config_info)
        if errors:
            print(f"❌ {description}: Validation errors:")
            for error in errors:
                print(f"   - {error}")
            continue
            
        # 設定保存
        success = config_manager.save_config(config_info)
        if success:
            print(f"✅ {description}: {config_info.file_path}")
            print(f"   Services: {', '.join(w.name for w in config_info.watchers)}")
        else:
            print(f"❌ {description}: Failed to save")
        print()
    
    # 保存された設定一覧を表示
    print("=== Available Configuration Files ===")
    config_files = config_manager.list_config_files()
    
    for config_file in config_files:
        print(f"📁 {config_file['name']}")
        print(f"   File: {config_file['file']}")
        print(f"   Services: {', '.join(config_file['services'])}")
        print(f"   Modified: {config_file['modified']}")
        print()

async def test_config_loading():
    """設定ファイルの読み込みテスト"""
    config_manager = CircusConfigManager()
    
    print("=== Testing Configuration Loading ===\n")
    
    # 設定ファイル一覧から最初のものを読み込み
    config_files = config_manager.list_config_files()
    if not config_files:
        print("No configuration files found to test.")
        return
    
    test_config_path = config_files[0]['path']
    print(f"Testing config: {test_config_path}")
    
    # 設定読み込み
    config_info = config_manager.load_config(test_config_path)
    if config_info:
        print(f"✅ Loaded: {config_info.name}")
        print(f"   Circus endpoint: {config_info.circus_endpoint}")
        print(f"   Watchers: {len(config_info.watchers)}")
        
        for watcher in config_info.watchers:
            print(f"   - {watcher.name}: {watcher.cmd}")
            if watcher.environment:
                env_vars = ', '.join(f"{k}={v}" for k, v in watcher.environment.items())
                print(f"     Environment: {env_vars}")
    else:
        print(f"❌ Failed to load config: {test_config_path}")

def show_example_usage():
    """CircusMCPツールの使用例を表示"""
    print("=== CircusMCP Tool Usage Examples ===\n")
    
    examples = [
        {
            "title": "Load SaaS Console Development Environment",
            "tool": "load_circus_config",
            "arguments": {
                "config_file": "~/.circus_configs/aethersaas_console_development.ini",
                "start_all": True
            }
        },
        {
            "title": "Save Current Development Session", 
            "tool": "save_circus_config",
            "arguments": {
                "config_file": "~/.circus_configs/my_current_session.ini",
                "config_name": "Current Development Session"
            }
        },
        {
            "title": "List Available Configurations",
            "tool": "list_config_files", 
            "arguments": {}
        },
        {
            "title": "Create Custom Development Environment",
            "tool": "create_dev_config",
            "arguments": {
                "config_name": "Custom API Development",
                "services": [
                    {
                        "name": "custom-api",
                        "command": "python app.py",
                        "working_dir": "/path/to/api",
                        "port": 8000
                    }
                ]
            }
        }
    ]
    
    for example in examples:
        print(f"🔧 {example['title']}")
        print(f"   Tool: {example['tool']}")
        print(f"   Arguments: {json.dumps(example['arguments'], indent=6)}")
        print()

async def main():
    """メイン処理"""
    print("🎪 CircusMCP - AetherPlatform Configuration Test\n")
    
    try:
        # 設定作成
        await create_aether_platform_configs()
        
        # 設定読み込みテスト
        await test_config_loading()
        
        # 使用例表示
        show_example_usage()
        
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())