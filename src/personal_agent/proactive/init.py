"""
Proactive System Initialization - 主动系统初始化
将主动智能体集成到多智能体系统
"""
from loguru import logger

from ..agents.proactive_agent import ProactiveAgent


def init_proactive_system(multi_agent_system):
    """初始化主动系统"""
    try:
        # 创建主动智能体
        proactive_agent = ProactiveAgent()

        # 注册到主智能体
        multi_agent_system.master.register_sub_agent(proactive_agent)

        # 启动主动智能体
        import asyncio
        asyncio.create_task(proactive_agent.start())

        logger.info("🧠 主动系统已初始化")
        return proactive_agent
    except Exception as e:
        logger.error(f"❌ 主动系统初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# 示例：如何使用主动系统

def example_usage():
    """示例：如何使用主动系统"""
    print("""
主动智能系统使用示例：

1. 保存用户档案：
   proactive_agent.assign_task(Task(
       type="save_user_profile",
       content="保存用户档案",
       params={
           "user_id": "gui_user",
           "name": "张三",
           "email": "zhangsan@example.com",
           "phone": "13800138000",
           "city": "北京",
           "address": "朝阳区",
           "birthday": "1990-01-01",
           "preferences": {
               "language": "zh",
               "theme": "dark"
           }
       }
   ))

2. 保存重要事件（生日）：
   proactive_agent.assign_task(Task(
       type="save_important_event",
       content="保存生日事件",
       params={
           "user_id": "gui_user",
           "event_type": "birthday",
           "event_date": "1990-01-01",
           "title": "张三",
           "description": "生日",
           "is_recurring": True,
           "recurring_type": "yearly"
       }
   ))

3. 保存重要事件（纪念日）：
   proactive_agent.assign_task(Task(
       type="save_important_event",
       content="保存纪念日事件",
       params={
           "user_id": "gui_user",
           "event_type": "anniversary",
           "event_date": "2015-05-20",
           "title": "结婚纪念日",
           "description": "结婚5周年",
           "is_recurring": True,
           "recurring_type": "yearly"
       }
   ))

4. 保存重要事件（提醒）：
   proactive_agent.assign_task(Task(
       type="save_important_event",
       content="保存提醒事件",
       params={
           "user_id": "gui_user",
           "event_type": "reminder",
           "event_date": "2026-02-20",
           "title": "项目截止日期",
           "description": "记得提交项目报告",
           "is_recurring": False
       }
   ))

5. 获取即将到来的事件：
   proactive_agent.assign_task(Task(
       type="get_upcoming_events",
       content="获取即将到来的事件",
       params={
           "user_id": "gui_user",
           "days": 7
       }
   ))

6. 获取用户洞察：
   proactive_agent.assign_task(Task(
       type="get_user_insights",
       content="获取用户洞察",
       params={
           "user_id": "gui_user",
           "insight_type": "preference"
       }
   ))

主动智能体会：
- 每小时主动思考一次
- 分析即将到来的事件
- 在生日当天自动发送祝福邮件
- 在生日前一天发送提醒
- 每天早上9点发送日程提醒
- 每周一早上9点发送周目标提醒
- 每月1号早上9点发送月目标提醒
- 根据用户偏好主动推送信息
    """)
