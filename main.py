#!/usr/bin/env python3
"""
Personal Agent Launcher
智能助手启动器 - 支持 CLI / Web / GUI 模式
"""
import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from personal_agent.main import run as agent_run
from personal_agent.main import main as agent_main


def print_banner():
    """Print welcome banner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🤖 Personal Agent - 个人智能助手                        ║
║                                                          ║
║   支持模式: CLI (命令行) | Web (网页) | GUI (桌面)        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Agent - 个人智能助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 默认启动 GUI 模式
  python main.py --channel gui      # 启动桌面 GUI 模式
  python main.py --channel cli      # 启动命令行模式
  python main.py --channel web      # 启动网页模式 (http://127.0.0.1:8080)
  python main.py -c cli             # 简写方式启动 CLI
        """
    )

    parser.add_argument(
        "--channel", "-c",
        choices=["cli", "web", "gui"],
        default="gui",
        help="选择启动模式 (默认: gui)"
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="显示版本信息"
    )

    args = parser.parse_args()

    if args.version:
        print("Personal Agent v1.0.0")
        return

    print_banner()

    # Set channel via command line
    sys.argv = [sys.argv[0], "--channel", args.channel]

    try:
        agent_run()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
