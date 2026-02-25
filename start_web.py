"""启动 Web 界面"""
import asyncio
from personal_agent.main import PersonalAgentApp

async def main():
    app = PersonalAgentApp(channel_type="web", port=38765)
    try:
        await app.start()
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
