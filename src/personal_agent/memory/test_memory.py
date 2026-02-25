"""
测试记忆系统功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.unified_memory import UnifiedMemory, UserProfile, UserPreference, ImportantEvent
from memory.memory_learner import MemoryLearner
from memory.memory_manager_enhanced import EnhancedMemoryManager


def test_unified_memory():
    """测试统一记忆系统"""
    print("\n" + "=" * 60)
    print("测试统一记忆系统")
    print("=" * 60)
    
    memory = UnifiedMemory(user_id="test_user")
    
    print("\n1. 测试用户档案")
    memory.update_user_profile("name", "用户")
    memory.update_user_profile("nickname", "测试用户")
    memory.update_user_profile("city", "北京")
    memory.update_user_profile("email", "test@example.com")
    
    profile = memory.user_profile.to_dict()
    print(f"   用户档案: {profile}")
    
    print("\n2. 测试用户偏好")
    memory.update_preference("language", "中文", confidence=0.9)
    memory.update_preference("communication_style", "简洁回复", confidence=0.8)
    
    pref = memory.get_preference("language")
    print(f"   语言偏好: {pref}")
    
    print("\n3. 测试重要事件")
    event_id = memory.add_important_event(
        title="项目上线",
        event_date="2024-03-15",
        event_type="work",
        description="智能体项目正式上线"
    )
    print(f"   添加事件: {event_id}")
    
    upcoming = memory.get_upcoming_events(days=30)
    print(f"   即将到来的事件: {len(upcoming)} 个")
    
    print("\n4. 测试记忆笔记")
    memory.add_memory_note("用户喜欢简洁的回复", priority=7)
    memory.add_memory_note("用户正在开发智能体项目", priority=8)
    
    print("\n5. 测试MEMORY.md生成")
    memory_md = memory.generate_memory_md()
    print("   MEMORY.md 内容:")
    print("-" * 40)
    print(memory_md[:500] + "..." if len(memory_md) > 500 else memory_md)
    print("-" * 40)
    
    print("\n6. 测试记忆搜索")
    results = memory.search_memory("项目")
    print(f"   搜索'项目'结果: {len(results)} 条")
    for r in results:
        print(f"   - {r}")
    
    print("\n7. 测试记忆统计")
    stats = memory.get_stats()
    print(f"   统计: {stats}")
    
    print("\n✅ 统一记忆系统测试完成")


def test_memory_learner():
    """测试记忆学习器"""
    print("\n" + "=" * 60)
    print("测试记忆学习器")
    print("=" * 60)
    
    memory = UnifiedMemory(user_id="test_learner")
    learner = MemoryLearner(memory)
    
    print("\n1. 测试提取用户信息")
    test_messages = [
        "我叫张三",
        "我在北京工作",
        "我的邮箱是 zhangsan@example.com",
        "我的生日是3月15日",
        "我喜欢简洁的回复"
    ]
    
    for msg in test_messages:
        result = learner.learn_from_message("user", msg)
        if result.get("learned"):
            print(f"   消息: '{msg}'")
            print(f"   学习结果: {result}")
    
    print("\n2. 检查学习后的用户档案")
    profile = memory.user_profile.to_dict()
    print(f"   用户档案: {profile}")
    
    print("\n3. 检查学习后的偏好")
    for key, pref in memory.preferences.items():
        print(f"   {pref.key}: {pref.value} (置信度: {pref.confidence})")
    
    print("\n✅ 记忆学习器测试完成")


def test_enhanced_memory_manager():
    """测试增强记忆管理器"""
    print("\n" + "=" * 60)
    print("测试增强记忆管理器")
    print("=" * 60)
    
    manager = EnhancedMemoryManager(max_items=100)
    
    print("\n1. 测试添加记忆")
    memory_ids = []
    for i in range(10):
        mid = manager.add_memory(
            content=f"测试记忆 {i+1}",
            category="test",
            priority=i % 5 + 1
        )
        memory_ids.append(mid)
    print(f"   添加了 {len(memory_ids)} 条记忆")
    
    print("\n2. 测试搜索记忆")
    results = manager.search_memories("测试", limit=5)
    print(f"   搜索'测试'结果: {len(results)} 条")
    for r in results:
        print(f"   - {r.content} (重要性: {r.importance:.3f})")
    
    print("\n3. 测试获取重要记忆")
    important = manager.get_important_memories(min_priority=3)
    print(f"   重要记忆: {len(important)} 条")
    
    print("\n4. 测试记忆统计")
    stats = manager.get_stats()
    print(f"   统计: {stats}")
    
    print("\n5. 测试记忆压缩")
    for i in range(5):
        manager.add_memory(
            content=f"测试记忆 测试记忆 测试记忆",
            category="duplicate",
            priority=5
        )
    
    compressed = manager.compress_memories("duplicate")
    print(f"   压缩了 {compressed} 条相似记忆")
    
    print("\n✅ 增强记忆管理器测试完成")


def test_memory_integration():
    """测试记忆系统集成"""
    print("\n" + "=" * 60)
    print("测试记忆系统集成")
    print("=" * 60)
    
    from memory.manager import MemoryManager
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoryManager(
            session_id="test_session",
            db_path=Path(tmpdir) / "memory",
            enable_learning=True
        )
        
        print("\n1. 测试对话添加")
        import asyncio
        
        async def test_async():
            await manager.add_conversation("user", "我叫李四")
            await manager.add_conversation("assistant", "你好，李四！")
            await manager.add_conversation("user", "我在上海工作")
            
            context = await manager.get_context()
            print(f"   对话上下文: {len(context)} 条")
            
            print("\n2. 测试记忆获取")
            memory_for_llm = manager.get_memory_for_llm()
            print(f"   LLM记忆内容长度: {len(memory_for_llm)} 字符")
            
            print("\n3. 测试记忆统计")
            stats = manager.get_memory_stats()
            print(f"   统计: {stats}")
            
            print("\n4. 测试导出导入")
            exported = manager.export_all_memory()
            print(f"   导出数据: {len(str(exported))} 字符")
        
        asyncio.run(test_async())
    
    print("\n✅ 记忆系统集成测试完成")


if __name__ == "__main__":
    test_unified_memory()
    test_memory_learner()
    test_enhanced_memory_manager()
    test_memory_integration()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
