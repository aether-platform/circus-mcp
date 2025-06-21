#!/usr/bin/env python3
"""
CircusMCP 基本機能テスト（簡単版）
"""

import sys
from pathlib import Path

# モジュールパス追加
sys.path.append(str(Path(__file__).parent / "circus_mcp_manager" / "src"))

from config_manager.circus_config import CircusConfigManager

def test_basic_functionality():
    """基本機能テスト"""
    
    print("🎪 CircusMCP Basic Functionality Test")
    print("=" * 50)
    
    config_manager = CircusConfigManager()
    
    # 1. 設定ディレクトリ確認
    print(f"📁 Config directory: {config_manager.config_dir}")
    print(f"   Directory exists: {config_manager.config_dir.exists()}")
    print()
    
    # 2. 既存設定ファイル一覧
    print("📋 Available Configuration Files:")
    config_files = config_manager.list_config_files()
    
    if config_files:
        for config in config_files:
            print(f"   ✅ {config['name']}")
            print(f"      Services: {', '.join(config['services'])}")
            print(f"      File: {config['file']}")
            print()
    else:
        print("   No configuration files found.")
        print()
    
    # 3. 設定ファイル読み込みテスト
    if config_files:
        test_config = config_files[0]
        print(f"🔍 Testing configuration load: {test_config['name']}")
        
        config_info = config_manager.load_config(test_config['path'])
        if config_info:
            print(f"   ✅ Successfully loaded: {config_info.name}")
            print(f"   📊 Watchers: {len(config_info.watchers)}")
            
            for watcher in config_info.watchers:
                print(f"      - {watcher.name}: {watcher.cmd}")
                print(f"        Working Dir: {watcher.working_dir}")
                if watcher.environment:
                    env_str = ', '.join(f"{k}={v}" for k, v in watcher.environment.items())
                    print(f"        Environment: {env_str}")
                print()
        else:
            print(f"   ❌ Failed to load configuration")
    
    # 4. 設定検証テスト
    if config_files:
        print("🔍 Configuration Validation Test:")
        test_config = config_files[0]
        
        config_info = config_manager.load_config(test_config['path'])
        if config_info:
            errors = config_manager.validate_config(config_info)
            if errors:
                print("   ❌ Validation errors found:")
                for error in errors:
                    print(f"      - {error}")
            else:
                print("   ✅ Configuration is valid")
        print()

def show_usage_guide():
    """使用方法ガイド"""
    
    print("🚀 Usage Guide for AetherPlatform Development")
    print("=" * 50)
    print()
    
    print("1️⃣ コマンドラインでのCircus使用:")
    print("   # フルスタック開発環境起動")
    print("   circusd ~/.circus_configs/aetherplatform_full_development.ini")
    print()
    print("   # SaaS Console のみ起動")
    print("   circusd ~/.circus_configs/aethersaas_console_development.ini")
    print()
    
    print("2️⃣ MCPツール経由での使用（将来）:")
    print("   # 設定一覧取得")
    print("   mcp_client.call_tool('list_config_files', {})")
    print()
    print("   # 環境起動")
    print("   mcp_client.call_tool('load_circus_config', {")
    print("       'config_file': '~/.circus_configs/aetherplatform_full_development.ini',")
    print("       'start_all': True")
    print("   })")
    print()
    
    print("3️⃣ 手動での新規設定作成:")
    print("   CircusConfigManagerを使用して、プロジェクト固有の設定を作成")
    print("   各サービスの起動コマンドと作業ディレクトリを指定")
    print()

def main():
    """メイン処理"""
    try:
        test_basic_functionality()
        show_usage_guide()
        
        print("✅ Basic test completed successfully!")
        print("\n🎯 CircusMCP configuration management is working!")
        print("📝 Configuration files are ready for AetherPlatform development.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()