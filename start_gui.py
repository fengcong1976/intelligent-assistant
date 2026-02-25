"""启动 GUI 界面"""
import asyncio
import sys

async def main():
    from personal_agent.main import PersonalAgentApp
    app = PersonalAgentApp(channel_type="gui")
    try:
        await app.start()
    except KeyboardInterrupt:
        pass
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
