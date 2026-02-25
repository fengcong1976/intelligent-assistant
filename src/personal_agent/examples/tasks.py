"""
Example scheduled tasks for the agent
"""
from datetime import datetime, timedelta


async def example_daily_report():
    print(f"[{datetime.now()}] 执行每日报告任务")
    return "每日报告已生成"


async def example_backup():
    print(f"[{datetime.now()}] 执行备份任务")
    return "备份完成"


async def example_reminder():
    print(f"[{datetime.now()}] 发送提醒")
    return "提醒已发送"


TASK_EXAMPLES = [
    {
        "name": "每日报告",
        "description": "每天早上9点生成报告",
        "trigger_type": "cron",
        "trigger_config": {"hour": 9, "minute": 0},
        "action": "daily_report",
        "action_params": {}
    },
    {
        "name": "定时备份",
        "description": "每小时执行一次备份",
        "trigger_type": "interval",
        "trigger_config": {"hours": 1},
        "action": "backup",
        "action_params": {}
    },
    {
        "name": "喝水提醒",
        "description": "每2小时提醒喝水",
        "trigger_type": "interval",
        "trigger_config": {"hours": 2},
        "action": "reminder",
        "action_params": {"message": "该喝水了！"}
    }
]
