"""
Home Assistant Agent - 智能家居控制智能体
支持设备控制、场景执行、状态查询
"""
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
from loguru import logger
from pathlib import Path

from datetime import datetime
from ..base import BaseAgent, Task
from ...config import settings


MOCK_ENTITIES = {
    "light.living_room": {
        "entity_id": "light.living_room",
        "state": "off",
        "attributes": {
            "friendly_name": "客厅灯",
            "brightness": 0,
            "supported_features": 1
        }
    },
    "light.bedroom": {
        "entity_id": "light.bedroom",
        "state": "on",
        "attributes": {
            "friendly_name": "卧室灯",
            "brightness": 180,
            "supported_features": 1
        }
    },
    "light.kitchen": {
        "entity_id": "light.kitchen",
        "state": "off",
        "attributes": {
            "friendly_name": "厨房灯",
            "supported_features": 1
        }
    },
    "switch.tv": {
        "entity_id": "switch.tv",
        "state": "off",
        "attributes": {
            "friendly_name": "电视"
        }
    },
    "switch.air_purifier": {
        "entity_id": "switch.air_purifier",
        "state": "on",
        "attributes": {
            "friendly_name": "空气净化器"
        }
    },
    "climate.living_room": {
        "entity_id": "climate.living_room",
        "state": "cool",
        "attributes": {
            "friendly_name": "客厅空调",
            "temperature": 26,
            "current_temperature": 28,
            "hvac_modes": ["off", "cool", "heat", "auto"],
            "hvac_action": "cooling"
        }
    },
    "climate.bedroom": {
        "entity_id": "climate.bedroom",
        "state": "off",
        "attributes": {
            "friendly_name": "卧室空调",
            "temperature": 24,
            "current_temperature": 25,
            "hvac_modes": ["off", "cool", "heat", "auto"]
        }
    },
    "cover.living_room": {
        "entity_id": "cover.living_room",
        "state": "closed",
        "attributes": {
            "friendly_name": "客厅窗帘",
            "current_position": 0,
            "supported_features": 15
        }
    },
    "cover.bedroom": {
        "entity_id": "cover.bedroom",
        "state": "open",
        "attributes": {
            "friendly_name": "卧室窗帘",
            "current_position": 100,
            "supported_features": 15
        }
    },
    "lock.front_door": {
        "entity_id": "lock.front_door",
        "state": "locked",
        "attributes": {
            "friendly_name": "前门",
            "supported_features": 1
        }
    },
    "fan.living_room": {
        "entity_id": "fan.living_room",
        "state": "off",
        "attributes": {
            "friendly_name": "客厅风扇",
            "speed": "off",
            "speed_list": ["off", "low", "medium", "high"]
        }
    },
    "sensor.temperature": {
        "entity_id": "sensor.temperature",
        "state": "25.5",
        "attributes": {
            "friendly_name": "室内温度",
            "unit_of_measurement": "°C"
        }
    },
    "sensor.humidity": {
        "entity_id": "sensor.humidity",
        "state": "45",
        "attributes": {
            "friendly_name": "室内湿度",
            "unit_of_measurement": "%"
        }
    },
    "scene.good_night": {
        "entity_id": "scene.good_night",
        "state": "unavailable",
        "attributes": {
            "friendly_name": "晚安场景"
        }
    },
    "scene.movie_mode": {
        "entity_id": "scene.movie_mode",
        "state": "unavailable",
        "attributes": {
            "friendly_name": "观影模式"
        }
    }
}


class MockHomeAssistantAPI:
    """模拟 Home Assistant API（用于测试）"""
    
    def __init__(self):
        self.entities = {k: v.copy() for k, v in MOCK_ENTITIES.items()}
        for k, v in self.entities.items():
            if 'attributes' in v:
                v['attributes'] = v['attributes'].copy()
    
    async def get_states(self) -> List[Dict]:
        return list(self.entities.values())
    
    async def get_state(self, entity_id: str) -> Optional[Dict]:
        return self.entities.get(entity_id)
    
    async def call_service(self, domain: str, service: str, entity_id: str = None, **data) -> bool:
        if entity_id and entity_id in self.entities:
            if service == "turn_on":
                self.entities[entity_id]["state"] = "on"
                if domain == "light" and "brightness" in data:
                    self.entities[entity_id]["attributes"]["brightness"] = data["brightness"]
                if domain == "fan" and "speed" in data:
                    self.entities[entity_id]["attributes"]["speed"] = data["speed"]
            elif service == "turn_off":
                self.entities[entity_id]["state"] = "off"
                if domain == "fan":
                    self.entities[entity_id]["attributes"]["speed"] = "off"
            elif service == "toggle":
                current = self.entities[entity_id]["state"]
                new_state = "off" if current == "on" else "on"
                self.entities[entity_id]["state"] = new_state
                if domain == "fan":
                    self.entities[entity_id]["attributes"]["speed"] = new_state if new_state == "on" else "off"
            elif service == "set_temperature" and domain == "climate":
                self.entities[entity_id]["attributes"]["temperature"] = data.get("temperature", 26)
            elif service == "set_hvac_mode" and domain == "climate":
                self.entities[entity_id]["state"] = data.get("hvac_mode", "cool")
            elif service == "open_cover" and domain == "cover":
                self.entities[entity_id]["state"] = "open"
                self.entities[entity_id]["attributes"]["current_position"] = 100
            elif service == "close_cover" and domain == "cover":
                self.entities[entity_id]["state"] = "closed"
                self.entities[entity_id]["attributes"]["current_position"] = 0
            elif service == "toggle_cover" and domain == "cover":
                current = self.entities[entity_id]["state"]
                if current == "open":
                    self.entities[entity_id]["state"] = "closed"
                    self.entities[entity_id]["attributes"]["current_position"] = 0
                else:
                    self.entities[entity_id]["state"] = "open"
                    self.entities[entity_id]["attributes"]["current_position"] = 100
            elif service == "set_cover_position" and domain == "cover" and "position" in data:
                position = data["position"]
                self.entities[entity_id]["attributes"]["current_position"] = position
                self.entities[entity_id]["state"] = "open" if position > 0 else "closed"
            elif service == "lock" and domain == "lock":
                self.entities[entity_id]["state"] = "locked"
            elif service == "unlock" and domain == "lock":
                self.entities[entity_id]["state"] = "unlocked"
            logger.info(f"[模拟] 服务调用: {domain}.{service} entity_id={entity_id} data={data}")
            return True
        return False
    
    async def turn_on(self, entity_id: str, **data) -> bool:
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_on", entity_id, **data)
    
    async def turn_off(self, entity_id: str) -> bool:
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_off", entity_id)
    
    async def toggle(self, entity_id: str) -> bool:
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "toggle", entity_id)
    
    async def set_brightness(self, entity_id: str, brightness: int) -> bool:
        return await self.call_service("light", "turn_on", entity_id, brightness=brightness)
    
    async def set_temperature(self, entity_id: str, temperature: float) -> bool:
        return await self.call_service("climate", "set_temperature", entity_id, temperature=temperature)
    
    async def set_hvac_mode(self, entity_id: str, mode: str) -> bool:
        return await self.call_service("climate", "set_hvac_mode", entity_id, hvac_mode=mode)
    
    async def activate_scene(self, scene_id: str) -> bool:
        logger.info(f"[模拟] 场景激活: {scene_id}")
        return True
    
    async def open_cover(self, entity_id: str) -> bool:
        return await self.call_service("cover", "open_cover", entity_id)
    
    async def close_cover(self, entity_id: str) -> bool:
        return await self.call_service("cover", "close_cover", entity_id)
    
    async def toggle_cover(self, entity_id: str) -> bool:
        return await self.call_service("cover", "toggle_cover", entity_id)
    
    async def set_cover_position(self, entity_id: str, position: int) -> bool:
        return await self.call_service("cover", "set_cover_position", entity_id, position=position)
    
    async def lock(self, entity_id: str) -> bool:
        return await self.call_service("lock", "lock", entity_id)
    
    async def unlock(self, entity_id: str) -> bool:
        return await self.call_service("lock", "unlock", entity_id)
    
    async def set_fan_speed(self, entity_id: str, speed: str) -> bool:
        return await self.call_service("fan", "turn_on", entity_id, speed=speed)
    
    async def close(self):
        pass


class HomeAssistantAPI:
    """Home Assistant API 客户端"""
    
    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_states(self) -> List[Dict]:
        """获取所有实体状态"""
        session = await self._get_session()
        async with session.get(f"{self.url}/api/states") as resp:
            if resp.status == 200:
                return await resp.json()
            return []
    
    async def get_state(self, entity_id: str) -> Optional[Dict]:
        """获取单个实体状态"""
        session = await self._get_session()
        async with session.get(f"{self.url}/api/states/{entity_id}") as resp:
            if resp.status == 200:
                return await resp.json()
            return None
    
    async def call_service(self, domain: str, service: str, entity_id: str = None, **data) -> bool:
        """调用服务"""
        session = await self._get_session()
        url = f"{self.url}/api/services/{domain}/{service}"
        payload = data.copy()
        if entity_id:
            payload["entity_id"] = entity_id
        
        async with session.post(url, json=payload) as resp:
            return resp.status == 200
    
    async def turn_on(self, entity_id: str, **data) -> bool:
        """打开设备"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_on", entity_id, **data)
    
    async def turn_off(self, entity_id: str) -> bool:
        """关闭设备"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_off", entity_id)
    
    async def toggle(self, entity_id: str) -> bool:
        """切换设备状态"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "toggle", entity_id)
    
    async def set_brightness(self, entity_id: str, brightness: int) -> bool:
        """设置亮度 (0-255)"""
        return await self.call_service("light", "turn_on", entity_id, brightness=brightness)
    
    async def set_temperature(self, entity_id: str, temperature: float) -> bool:
        """设置温度"""
        return await self.call_service("climate", "set_temperature", entity_id, temperature=temperature)
    
    async def set_hvac_mode(self, entity_id: str, mode: str) -> bool:
        """设置空调模式"""
        return await self.call_service("climate", "set_hvac_mode", entity_id, hvac_mode=mode)
    
    async def execute_script(self, script_id: str) -> bool:
        """执行脚本"""
        return await self.call_service("script", script_id.replace('script.', ''))
    
    async def activate_scene(self, scene_id: str) -> bool:
        """激活场景"""
        return await self.call_service("scene", "turn_on", scene_id)
    
    async def open_cover(self, entity_id: str) -> bool:
        """打开窗帘"""
        return await self.call_service("cover", "open_cover", entity_id)
    
    async def close_cover(self, entity_id: str) -> bool:
        """关闭窗帘"""
        return await self.call_service("cover", "close_cover", entity_id)
    
    async def toggle_cover(self, entity_id: str) -> bool:
        """切换窗帘状态"""
        return await self.call_service("cover", "toggle_cover", entity_id)
    
    async def set_cover_position(self, entity_id: str, position: int) -> bool:
        """设置窗帘位置"""
        return await self.call_service("cover", "set_cover_position", entity_id, position=position)
    
    async def lock(self, entity_id: str) -> bool:
        """锁门"""
        return await self.call_service("lock", "lock", entity_id)
    
    async def unlock(self, entity_id: str) -> bool:
        """解锁"""
        return await self.call_service("lock", "unlock", entity_id)
    
    async def set_fan_speed(self, entity_id: str, speed: str) -> bool:
        """设置风扇速度"""
        return await self.call_service("fan", "turn_on", entity_id, speed=speed)


class HomeAssistantAgent(BaseAgent):
    """
    Home Assistant 智能家居控制智能体

    能力：
    - 设备控制（开关、亮度调节、温度设置等）
    - 设备状态查询
    - 场景执行
    - 自动化规则管理
    - 设备分组控制
    - 多种设备类型支持（灯光、空调、开关、窗帘、门锁、风扇、传感器等）
    - 实体缓存管理
    """
    
    PRIORITY = 4
    KEYWORD_MAPPINGS = {
        "打开智能家居": ("open_dashboard", {}),
        "智能家居": ("open_dashboard", {}),
        "打开控制面板": ("open_dashboard", {}),
        "智能家居控制": ("open_dashboard", {}),
    }

    def __init__(self):
        super().__init__(
            name="homeassistant_agent",
            description="Home Assistant 智能家居控制智能体"
        )
        
        self.register_capability(
            capability="ha_control",
            description="控制 Home Assistant 智能家居设备。支持打开/关闭灯光、开关、空调等设备。",
            parameters={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": "设备名称，如'客厅灯'、'卧室空调'、'电视'"
                    },
                    "action": {
                        "type": "string",
                        "description": "操作类型：'on' 打开、'off' 关闭、'toggle' 切换",
                        "enum": ["on", "off", "toggle"]
                    }
                },
                "required": ["device", "action"]
            },
            category="homeassistant"
        )
        
        self.register_capability(
            capability="ha_set_temperature",
            description="设置空调温度。调节智能空调的温度。",
            parameters={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": "空调设备名称（可选），如'客厅空调'、'卧室空调'"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "目标温度，如 26、24、28"
                    }
                },
                "required": ["temperature"]
            },
            category="homeassistant"
        )
        
        self.register_capability(
            capability="ha_set_brightness",
            description="调节灯光亮度。设置智能灯的亮度。",
            parameters={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": "灯光设备名称，如'客厅灯'、'卧室灯'"
                    },
                    "brightness": {
                        "type": "integer",
                        "description": "亮度值 (0-100)，0最暗，100最亮",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["device", "brightness"]
            },
            category="homeassistant"
        )
        
        self.register_capability(
            capability="ha_query_state",
            description="查询智能家居设备状态。获取灯光、开关、空调等设备的当前状态。",
            parameters={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": "设备名称（可选），不指定则查询所有设备状态"
                    }
                },
                "required": []
            },
            category="homeassistant"
        )
        
        self.register_capability("control_lights", "控制灯光")
        self.register_capability("control_switches", "控制开关")
        self.register_capability("control_climate", "控制气候")
        self.register_capability("control_covers", "控制窗帘")
        self.register_capability("control_locks", "控制门锁")
        self.register_capability("control_fans", "控制风扇")
        self.register_capability("execute_scenes", "执行场景")
        self.register_capability("query_states", "查询状态")
        self.register_capability("open_dashboard", "打开仪表板")
        self.register_capability("query_sensors", "查询传感器")
        
        self.api = None
        
        self._entity_cache: Dict[str, Dict] = {}
        self._friendly_name_map: Dict[str, str] = {}
        self._use_mock = False
        self._automation_rules: Dict[str, Dict] = {}
        self._rule_id_counter = 1
        
        self._init_api()
        self._load_automation_rules()
    
    def get_capabilities_description(self) -> str:
        """获取能力描述，用于LLM意图识别"""
        return """### homeassistant_agent (智能家居控制智能体)
- 打开控制面板: 打开智能家居控制面板，action=open_dashboard
- 设备控制: 控制设备开关，action=turn_on/turn_off, entity_name=设备名称
- 设备切换: 切换设备状态，action=toggle, entity_name=设备名称
- 亮度调节: 调节灯光亮度，action=set_brightness, entity_name=灯光名称, brightness=亮度值
- 温度设置: 设置空调温度，action=set_temperature, entity_name=空调名称, temperature=温度值
- 模式设置: 设置空调模式，action=set_hvac_mode, entity_name=空调名称, mode=模式名称
- 场景执行: 执行场景，action=execute_scene, scene_name=场景名称
- 状态查询: 查询设备状态，action=query_state, entity_name=设备名称
- 实体列表: 列出所有设备，action=list_entities
- 自动化规则: 创建自动化规则，action=create_automation_rule, name=规则名称, trigger=触发条件, action=执行动作
- 自动化规则管理: 删除/列出/切换自动化规则，action=delete_automation_rule/list_automation_rules/toggle_automation_rule, rule_id=规则ID
- 窗帘控制: 控制窗帘开关，action=open_cover/close_cover/toggle_cover, entity_name=窗帘名称
- 窗帘位置: 设置窗帘位置，action=set_cover_position, entity_name=窗帘名称, position=位置值
- 门锁控制: 控制门锁开关，action=lock/unlock, entity_name=门锁名称
- 风扇控制: 控制风扇，action=control_fan, entity_name=风扇名称, speed=速度值
- 传感器查询: 查询传感器数据，action=query_sensors, entity_name=传感器名称
- 示例: "打开客厅灯" -> action=turn_on, entity_name="客厅灯"
- 示例: "设置空调温度为26度" -> action=set_temperature, entity_name="空调", temperature=26
- 示例: "打开窗帘" -> action=open_cover, entity_name="窗帘"
"""
    
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """🏠 智能家居控制智能体

功能：
- 设备控制：控制各种智能家居设备的开关状态
- 亮度调节：调节灯光亮度
- 温度设置：设置空调温度
- 模式设置：设置空调运行模式
- 场景执行：执行预定义的智能家居场景
- 状态查询：查询设备当前状态
- 自动化规则管理：创建、删除、列出、切换自动化规则
- 设备分组控制：控制一组设备（如所有灯）
- 多种设备类型支持：灯光、空调、开关、窗帘、门锁、风扇、传感器等

使用方法：
- "打开智能家居面板"
- "打开客厅灯"
- "关闭卧室灯"
- "设置空调温度为26度"
- "将空调设置为制冷模式"
- "执行睡眠场景"
- "查询所有设备状态"
- "创建自动化规则"
- "打开窗帘"
- "关闭门锁"
- "设置风扇速度"

参数说明：
- open_dashboard: 无参数
- turn_on/turn_off: entity_name=设备名称
- toggle: entity_name=设备名称
- set_brightness: entity_name=灯光名称, brightness=亮度值(0-100)
- set_temperature: entity_name=空调名称, temperature=温度值
- set_hvac_mode: entity_name=空调名称, mode=模式名称(制冷/制热/自动/送风/除湿)
- execute_scene: scene_name=场景名称
- query_state: entity_name=设备名称（可选，不填则查询所有设备）
- list_entities: 无参数
- create_automation_rule: name=规则名称, trigger=触发条件, action=执行动作
- delete_automation_rule: rule_id=规则ID
- list_automation_rules: 无参数
- toggle_automation_rule: rule_id=规则ID
- open_cover/close_cover/toggle_cover: entity_name=窗帘名称
- set_cover_position: entity_name=窗帘名称, position=位置值(0-100)
- lock/unlock: entity_name=门锁名称
- control_fan: entity_name=风扇名称, speed=速度值
- query_sensors: entity_name=传感器名称（可选，不填则查询所有传感器）

注意：
- 需要在设置中配置 Home Assistant URL 和访问令牌
- 支持自然语言查询，如"打开所有灯"、"关闭客厅空调"等
- 自动化规则会保存到本地 JSON 文件中
- 设备状态会缓存以提高响应速度
"""

    
    def _init_api(self):
        """初始化 API 客户端"""
        ha_config = getattr(settings, 'homeassistant', None)
        if ha_config:
            url = getattr(ha_config, 'url', None)
            token = getattr(ha_config, 'token', None)
            enabled = getattr(ha_config, 'enabled', False)
            if url and token and enabled:
                self.api = HomeAssistantAPI(url, token)
                logger.info(f"✅ Home Assistant API 初始化成功: {url}")
                return
        
        self.api = MockHomeAssistantAPI()
        self._use_mock = True
        logger.info("🏠 使用模拟智能家居环境（测试模式）")
    
    def _load_automation_rules(self):
        """加载自动化规则"""
        import json
        from pathlib import Path
        
        rules_file = Path("./data/automation_rules.json")
        if rules_file.exists():
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._automation_rules = data.get("rules", {})
                    self._rule_id_counter = data.get("next_id", 1)
                logger.info(f"✅ 加载了 {len(self._automation_rules)} 个自动化规则")
            except Exception as e:
                logger.error(f"❌ 加载自动化规则失败: {e}")
                self._automation_rules = {}
                self._rule_id_counter = 1
        else:
            logger.info("🏠 首次启动，暂无自动化规则")
    
    def _save_automation_rules(self):
        """保存自动化规则"""
        import json
        from pathlib import Path
        
        rules_file = Path("./data/automation_rules.json")
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                "rules": self._automation_rules,
                "next_id": self._rule_id_counter
            }
            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 保存了 {len(self._automation_rules)} 个自动化规则")
        except Exception as e:
            logger.error(f"❌ 保存自动化规则失败: {e}")
    
    async def _handle_create_automation_rule(self, params: Dict) -> str:
        """创建自动化规则"""
        name = params.get("name", "")
        trigger = params.get("trigger", "")
        action = params.get("action", "")
        
        if not name or not trigger or not action:
            return "❌ 创建自动化规则失败：缺少必要参数（名称、触发条件、执行动作）"
        
        rule_id = str(self._rule_id_counter)
        self._rule_id_counter += 1
        
        self._automation_rules[rule_id] = {
            "id": rule_id,
            "name": name,
            "trigger": trigger,
            "action": action,
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_automation_rules()
        return f"✅ 成功创建自动化规则：{name}"
    
    async def _handle_delete_automation_rule(self, params: Dict) -> str:
        """删除自动化规则"""
        rule_id = params.get("rule_id")
        rule_name = params.get("rule_name")
        
        if rule_id and rule_id in self._automation_rules:
            del self._automation_rules[rule_id]
            self._save_automation_rules()
            return f"✅ 成功删除自动化规则 ID: {rule_id}"
        
        if rule_name:
            for rule_id, rule in list(self._automation_rules.items()):
                if rule.get("name") == rule_name:
                    del self._automation_rules[rule_id]
                    self._save_automation_rules()
                    return f"✅ 成功删除自动化规则：{rule_name}"
        
        return "❌ 未找到指定的自动化规则"
    
    async def _handle_list_automation_rules(self, params: Dict) -> str:
        """列出所有自动化规则"""
        if not self._automation_rules:
            return "📋 当前无自动化规则"
        
        result = "📋 自动化规则列表\n\n"
        for rule_id, rule in self._automation_rules.items():
            status = "🟢 启用" if rule.get("enabled", True) else "🔴 禁用"
            result += f"ID: {rule_id}\n"
            result += f"名称: {rule.get('name', '未命名')}\n"
            result += f"状态: {status}\n"
            result += f"触发条件: {rule.get('trigger', '无')}\n"
            result += f"执行动作: {rule.get('action', '无')}\n"
            result += f"创建时间: {rule.get('created_at', '未知')}\n"
            result += "-" * 30 + "\n"
        
        return result.strip()
    
    async def _handle_toggle_automation_rule(self, params: Dict) -> str:
        """启用/禁用自动化规则"""
        rule_id = params.get("rule_id")
        rule_name = params.get("rule_name")
        
        if rule_id and rule_id in self._automation_rules:
            rule = self._automation_rules[rule_id]
            rule["enabled"] = not rule.get("enabled", True)
            self._save_automation_rules()
            status = "启用" if rule["enabled"] else "禁用"
            return f"✅ 成功{status}自动化规则 ID: {rule_id}"
        
        if rule_name:
            for rule_id, rule in self._automation_rules.items():
                if rule.get("name") == rule_name:
                    rule["enabled"] = not rule.get("enabled", True)
                    self._save_automation_rules()
                    status = "启用" if rule["enabled"] else "禁用"
                    return f"✅ 成功{status}自动化规则：{rule_name}"
        
        return "❌ 未找到指定的自动化规则"
    
    async def _get_api(self):
        """获取 API 客户端"""
        if self.api is None:
            self._init_api()
        return self.api
    
    async def _refresh_entity_cache(self):
        """刷新实体缓存"""
        api = await self._get_api()
        if not api:
            return
        
        try:
            states = await api.get_states()
            self._entity_cache.clear()
            self._friendly_name_map.clear()
            
            for state in states:
                entity_id = state.get('entity_id', '')
                friendly_name = state.get('attributes', {}).get('friendly_name', '')
                
                self._entity_cache[entity_id] = state
                
                if friendly_name:
                    self._friendly_name_map[friendly_name.lower()] = entity_id
                    self._friendly_name_map[entity_id.lower()] = entity_id
            
            logger.info(f"✅ 已缓存 {len(self._entity_cache)} 个实体")
        except Exception as e:
            logger.error(f"❌ 刷新实体缓存失败: {e}")
    
    def _find_entity(self, name: str) -> Optional[str]:
        """根据名称查找实体 ID"""
        name_lower = name.lower()
        
        if name_lower in self._friendly_name_map:
            return self._friendly_name_map[name_lower]
        
        for friendly_name, entity_id in self._friendly_name_map.items():
            if name_lower in friendly_name:
                return entity_id
        
        for entity_id in self._entity_cache.keys():
            if name_lower in entity_id.lower():
                return entity_id
        
        return None
    
    def _get_entity_by_domain(self, domain: str) -> List[str]:
        """获取指定域的所有实体"""
        return [eid for eid in self._entity_cache.keys() if eid.startswith(f"{domain}.")]
    
    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params
        
        if task_type == "ha_control":
            task_type = params.get("action", "query_state")
        elif task_type == "ha_set_temperature":
            task_type = "set_temperature"
        elif task_type == "ha_set_brightness":
            task_type = "set_brightness"
        elif task_type == "ha_query_state":
            task_type = "query_state"
        
        logger.info(f"🏠 {self.name} 执行任务: {task_type}, 参数: {params}")
        
        try:
            if not self.api:
                return "❌ 未配置 Home Assistant，请在设置中配置 URL 和访问令牌"
            
            if task_type == "open_dashboard":
                return await self._handle_open_dashboard(params)
            elif task_type == "turn_on":
                return await self._handle_turn_on(params)
            elif task_type == "turn_off":
                return await self._handle_turn_off(params)
            elif task_type == "toggle":
                return await self._handle_toggle(params)
            elif task_type == "set_brightness":
                return await self._handle_set_brightness(params)
            elif task_type == "set_temperature":
                return await self._handle_set_temperature(params)
            elif task_type == "set_hvac_mode":
                return await self._handle_set_hvac_mode(params)
            elif task_type == "execute_scene":
                return await self._handle_execute_scene(params)
            elif task_type == "query_state":
                return await self._handle_query_state(params)
            elif task_type == "list_entities":
                return await self._handle_list_entities(params)
            elif task_type == "control_light":
                return await self._handle_control_light(params)
            elif task_type == "control_climate":
                return await self._handle_control_climate(params)
            elif task_type == "control_switch":
                return await self._handle_control_switch(params)
            elif task_type == "create_automation_rule":
                return await self._handle_create_automation_rule(params)
            elif task_type == "delete_automation_rule":
                return await self._handle_delete_automation_rule(params)
            elif task_type == "list_automation_rules":
                return await self._handle_list_automation_rules(params)
            elif task_type == "toggle_automation_rule":
                return await self._handle_toggle_automation_rule(params)
            elif task_type == "open_cover":
                return await self._handle_open_cover(params)
            elif task_type == "close_cover":
                return await self._handle_close_cover(params)
            elif task_type == "toggle_cover":
                return await self._handle_toggle_cover(params)
            elif task_type == "set_cover_position":
                return await self._handle_set_cover_position(params)
            elif task_type == "lock":
                return await self._handle_lock(params)
            elif task_type == "unlock":
                return await self._handle_unlock(params)
            elif task_type == "control_fan":
                return await self._handle_control_fan(params)
            elif task_type == "query_sensors":
                return await self._handle_query_sensors(params)
            else:
                return await self._handle_natural_language(params)
        except Exception as e:
            error_msg = f"❌ 执行任务失败: {str(e)}"
            logger.error(error_msg)
            logger.exception("详细错误信息:")
            return error_msg
    
    async def _handle_open_dashboard(self, params: Dict) -> str:
        """打开控制面板"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'chat_window'):
                        main_window = widget
                        if hasattr(main_window, 'chat_window'):
                            chat_window = main_window.chat_window
                            if hasattr(chat_window, 'signal_helper'):
                                chat_window.signal_helper.emit_show_homeassistant_dashboard()
                                return "🏠 已打开智能家居控制面板"
        except Exception as e:
            logger.error(f"打开控制面板失败: {e}")
        
        return "❌ 无法打开控制面板"
    
    async def _handle_turn_on(self, params: Dict) -> str:
        """打开设备"""
        entity_name = params.get("entity_name", params.get("device", ""))
        if not entity_name:
            return "❌ 请指定要打开的设备"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        success = await self.api.turn_on(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已打开 {friendly_name}"
        return f"❌ 打开 {entity_name} 失败"
    
    async def _handle_turn_off(self, params: Dict) -> str:
        """关闭设备"""
        entity_name = params.get("entity_name", params.get("device", ""))
        if not entity_name:
            return "❌ 请指定要关闭的设备"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        success = await self.api.turn_off(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已关闭 {friendly_name}"
        return f"❌ 关闭 {entity_name} 失败"
    
    async def _handle_toggle(self, params: Dict) -> str:
        """切换设备状态"""
        entity_name = params.get("entity_name", params.get("device", ""))
        if not entity_name:
            return "❌ 请指定要切换的设备"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        success = await self.api.toggle(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已切换 {friendly_name} 状态"
        return f"❌ 切换 {entity_name} 状态失败"
    
    async def _handle_set_brightness(self, params: Dict) -> str:
        """设置亮度"""
        entity_name = params.get("entity_name", params.get("device", ""))
        brightness = params.get("brightness", 128)
        
        if isinstance(brightness, str):
            if brightness.isdigit():
                brightness = int(brightness)
            elif "亮" in brightness or "高" in brightness:
                brightness = 255
            elif "暗" in brightness or "低" in brightness:
                brightness = 64
            else:
                brightness = 128
        
        if brightness > 100:
            brightness_pct = brightness
            brightness = int(brightness_pct * 255 / 100)
        else:
            brightness = int(brightness * 255 / 100)
        
        if not entity_name:
            return "❌ 请指定要调节亮度的灯"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("light."):
            return f"❌ {entity_name} 不是灯光设备"
        
        success = await self.api.set_brightness(entity_id, brightness)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已将 {friendly_name} 亮度调节到 {brightness_pct if brightness_pct else int(brightness * 100 / 255)}%"
        return f"❌ 调节 {entity_name} 亮度失败"
    
    async def _handle_set_temperature(self, params: Dict) -> str:
        """设置温度"""
        entity_name = params.get("entity_name", params.get("device", ""))
        temperature = params.get("temperature")
        
        if temperature is None:
            return "❌ 请指定温度"
        
        if isinstance(temperature, str):
            import re
            match = re.search(r'(\d+)', temperature)
            if match:
                temperature = float(match.group(1))
            else:
                return "❌ 无法解析温度值"
        
        if not entity_name:
            climate_entities = self._get_entity_by_domain("climate")
            if climate_entities:
                entity_id = climate_entities[0]
            else:
                return "❌ 未找到空调设备"
        else:
            await self._refresh_entity_cache()
            entity_id = self._find_entity(entity_name)
            if not entity_id:
                return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("climate."):
            return f"❌ {entity_name} 不是空调设备"
        
        success = await self.api.set_temperature(entity_id, temperature)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已将 {friendly_name} 温度设置为 {temperature}°C"
        return f"❌ 设置温度失败"
    
    async def _handle_set_hvac_mode(self, params: Dict) -> str:
        """设置空调模式"""
        entity_name = params.get("entity_name", params.get("device", ""))
        mode = params.get("mode", "").lower()
        
        mode_map = {
            "制冷": "cool",
            "制热": "heat",
            "自动": "auto",
            "送风": "fan_only",
            "除湿": "dry",
            "关": "off",
            "cool": "cool",
            "heat": "heat",
            "auto": "auto",
            "fan": "fan_only",
            "dry": "dry",
            "off": "off"
        }
        
        ha_mode = mode_map.get(mode, mode)
        
        if not entity_name:
            climate_entities = self._get_entity_by_domain("climate")
            if climate_entities:
                entity_id = climate_entities[0]
            else:
                return "❌ 未找到空调设备"
        else:
            await self._refresh_entity_cache()
            entity_id = self._find_entity(entity_name)
            if not entity_id:
                return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("climate."):
            return f"❌ {entity_name} 不是空调设备"
        
        success = await self.api.set_hvac_mode(entity_id, ha_mode)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            mode_name = {"cool": "制冷", "heat": "制热", "auto": "自动", "fan_only": "送风", "dry": "除湿", "off": "关闭"}.get(ha_mode, ha_mode)
            return f"✅ 已将 {friendly_name} 设置为{mode_name}模式"
        return f"❌ 设置空调模式失败"
    
    async def _handle_execute_scene(self, params: Dict) -> str:
        """执行场景"""
        scene_name = params.get("scene_name", params.get("scene", ""))
        
        if not scene_name:
            return "❌ 请指定要执行的场景"
        
        await self._refresh_entity_cache()
        
        scene_id = None
        for eid in self._entity_cache.keys():
            if eid.startswith("scene."):
                friendly_name = self._entity_cache[eid].get('attributes', {}).get('friendly_name', '')
                if scene_name.lower() in friendly_name.lower() or scene_name.lower() in eid.lower():
                    scene_id = eid
                    break
        
        if not scene_id:
            return f"❌ 未找到场景: {scene_name}"
        
        success = await self.api.activate_scene(scene_id)
        if success:
            friendly_name = self._entity_cache.get(scene_id, {}).get('attributes', {}).get('friendly_name', scene_id)
            return f"✅ 已执行场景: {friendly_name}"
        return f"❌ 执行场景 {scene_name} 失败"
    
    async def _handle_query_state(self, params: Dict) -> str:
        """查询设备状态"""
        entity_name = params.get("entity_name", params.get("device", ""))
        
        await self._refresh_entity_cache()
        
        if entity_name:
            entity_id = self._find_entity(entity_name)
            if not entity_id:
                return f"❌ 未找到设备: {entity_name}"
            
            state = self._entity_cache.get(entity_id, {})
            friendly_name = state.get('attributes', {}).get('friendly_name', entity_id)
            current_state = state.get('state', 'unknown')
            
            result = f"📊 {friendly_name}\n"
            result += f"状态: {current_state}\n"
            
            attrs = state.get('attributes', {})
            if 'brightness' in attrs:
                brightness = attrs['brightness']
                brightness_pct = int(brightness * 100 / 255)
                result += f"亮度: {brightness_pct}%\n"
            if 'temperature' in attrs:
                result += f"温度: {attrs['temperature']}°C\n"
            if 'current_temperature' in attrs:
                result += f"当前温度: {attrs['current_temperature']}°C\n"
            if 'hvac_action' in attrs:
                result += f"运行状态: {attrs['hvac_action']}\n"
            
            return result.strip()
        else:
            lights = [eid for eid in self._entity_cache.keys() if eid.startswith("light.")]
            switches = [eid for eid in self._entity_cache.keys() if eid.startswith("switch.")]
            climates = [eid for eid in self._entity_cache.keys() if eid.startswith("climate.")]
            
            result = "📊 智能家居设备状态\n\n"
            
            if lights:
                result += "💡 灯光:\n"
                for eid in lights[:5]:
                    state = self._entity_cache[eid]
                    friendly_name = state.get('attributes', {}).get('friendly_name', eid)
                    current_state = "🟢 开" if state.get('state') == 'on' else "⚫ 关"
                    result += f"  {friendly_name}: {current_state}\n"
                result += "\n"
            
            if climates:
                result += "❄️ 空调:\n"
                for eid in climates[:3]:
                    state = self._entity_cache[eid]
                    friendly_name = state.get('attributes', {}).get('friendly_name', eid)
                    current_state = state.get('state', 'off')
                    temp = state.get('attributes', {}).get('temperature', '-')
                    result += f"  {friendly_name}: {current_state} ({temp}°C)\n"
                result += "\n"
            
            if switches:
                result += "🔌 开关:\n"
                for eid in switches[:5]:
                    state = self._entity_cache[eid]
                    friendly_name = state.get('attributes', {}).get('friendly_name', eid)
                    current_state = "🟢 开" if state.get('state') == 'on' else "⚫ 关"
                    result += f"  {friendly_name}: {current_state}\n"
            
            return result.strip()
    
    async def _handle_list_entities(self, params: Dict) -> str:
        """列出所有实体"""
        await self._refresh_entity_cache()
        
        domain = params.get("domain", "")
        
        if domain:
            entities = [eid for eid in self._entity_cache.keys() if eid.startswith(f"{domain}.")]
        else:
            entities = list(self._entity_cache.keys())
        
        if not entities:
            return "❌ 没有找到设备"
        
        result = f"📋 设备列表 (共 {len(entities)} 个)\n\n"
        for eid in entities[:20]:
            state = self._entity_cache[eid]
            friendly_name = state.get('attributes', {}).get('friendly_name', eid)
            result += f"• {friendly_name} ({eid})\n"
        
        if len(entities) > 20:
            result += f"\n... 还有 {len(entities) - 20} 个设备"
        
        return result
    
    async def _handle_control_light(self, params: Dict) -> str:
        """控制灯光"""
        action = params.get("action", "")
        entity_name = params.get("entity_name", params.get("device", ""))
        
        if action == "on":
            return await self._handle_turn_on(params)
        elif action == "off":
            return await self._handle_turn_off(params)
        elif action == "brightness":
            return await self._handle_set_brightness(params)
        else:
            return await self._handle_turn_on(params)
    
    async def _handle_control_climate(self, params: Dict) -> str:
        """控制空调"""
        action = params.get("action", "")
        
        if action == "on":
            return await self._handle_turn_on(params)
        elif action == "off":
            return await self._handle_turn_off(params)
        elif action == "temperature":
            return await self._handle_set_temperature(params)
        elif action == "mode":
            return await self._handle_set_hvac_mode(params)
        else:
            return await self._handle_turn_on(params)
    
    async def _handle_control_switch(self, params: Dict) -> str:
        """控制开关"""
        action = params.get("action", "")
        
        if action == "on":
            return await self._handle_turn_on(params)
        elif action == "off":
            return await self._handle_turn_off(params)
        else:
            return await self._handle_toggle(params)
    
    async def _handle_open_cover(self, params: Dict) -> str:
        """打开窗帘"""
        entity_name = params.get("entity_name", params.get("device", ""))
        
        if not entity_name:
            return "❌ 请指定要打开的窗帘"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("cover."):
            return f"❌ {entity_name} 不是窗帘设备"
        
        success = await self.api.open_cover(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已打开 {friendly_name}"
        return f"❌ 打开 {entity_name} 失败"
    
    async def _handle_close_cover(self, params: Dict) -> str:
        """关闭窗帘"""
        entity_name = params.get("entity_name", params.get("device", ""))
        
        if not entity_name:
            return "❌ 请指定要关闭的窗帘"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("cover."):
            return f"❌ {entity_name} 不是窗帘设备"
        
        success = await self.api.close_cover(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已关闭 {friendly_name}"
        return f"❌ 关闭 {entity_name} 失败"
    
    async def _handle_toggle_cover(self, params: Dict) -> str:
        """切换窗帘状态"""
        entity_name = params.get("entity_name", params.get("device", ""))
        
        if not entity_name:
            return "❌ 请指定要切换的窗帘"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("cover."):
            return f"❌ {entity_name} 不是窗帘设备"
        
        success = await self.api.toggle_cover(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已切换 {friendly_name} 状态"
        return f"❌ 切换 {entity_name} 状态失败"
    
    async def _handle_set_cover_position(self, params: Dict) -> str:
        """设置窗帘位置"""
        entity_name = params.get("entity_name", params.get("device", ""))
        position = params.get("position", 50)
        
        if not entity_name:
            return "❌ 请指定要设置的窗帘"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("cover."):
            return f"❌ {entity_name} 不是窗帘设备"
        
        success = await self.api.set_cover_position(entity_id, position)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已将 {friendly_name} 设置到 {position}% 位置"
        return f"❌ 设置 {entity_name} 位置失败"
    
    async def _handle_lock(self, params: Dict) -> str:
        """锁门"""
        entity_name = params.get("entity_name", params.get("device", ""))
        
        if not entity_name:
            return "❌ 请指定要锁的门"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("lock."):
            return f"❌ {entity_name} 不是门锁设备"
        
        success = await self.api.lock(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已锁上 {friendly_name}"
        return f"❌ 锁 {entity_name} 失败"
    
    async def _handle_unlock(self, params: Dict) -> str:
        """解锁"""
        entity_name = params.get("entity_name", params.get("device", ""))
        
        if not entity_name:
            return "❌ 请指定要解锁的门"
        
        await self._refresh_entity_cache()
        entity_id = self._find_entity(entity_name)
        
        if not entity_id:
            return f"❌ 未找到设备: {entity_name}"
        
        if not entity_id.startswith("lock."):
            return f"❌ {entity_name} 不是门锁设备"
        
        success = await self.api.unlock(entity_id)
        if success:
            friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
            return f"✅ 已解锁 {friendly_name}"
        return f"❌ 解锁 {entity_name} 失败"
    
    async def _handle_control_fan(self, params: Dict) -> str:
        """控制风扇"""
        action = params.get("action", "")
        entity_name = params.get("entity_name", params.get("device", ""))
        speed = params.get("speed", "")
        
        if action == "on":
            if speed:
                await self._refresh_entity_cache()
                entity_id = self._find_entity(entity_name)
                if entity_id:
                    success = await self.api.set_fan_speed(entity_id, speed)
                    if success:
                        friendly_name = self._entity_cache.get(entity_id, {}).get('attributes', {}).get('friendly_name', entity_id)
                        return f"✅ 已打开 {friendly_name}，速度设置为 {speed}"
            return await self._handle_turn_on(params)
        elif action == "off":
            return await self._handle_turn_off(params)
        else:
            return await self._handle_toggle(params)
    
    async def _handle_query_sensors(self, params: Dict) -> str:
        """查询传感器状态"""
        await self._refresh_entity_cache()
        
        sensors = []
        for entity_id, entity in self._entity_cache.items():
            if entity_id.startswith("sensor."):
                sensors.append(entity)
        
        if not sensors:
            return "📊 当前无传感器数据"
        
        result = "📊 传感器状态\n\n"
        for sensor in sensors:
            friendly_name = sensor.get('attributes', {}).get('friendly_name', sensor.get('entity_id', ''))
            state = sensor.get('state', 'unknown')
            unit = sensor.get('attributes', {}).get('unit_of_measurement', '')
            result += f"• {friendly_name}: {state} {unit}\n"
        
        return result.strip()
    
    async def _handle_group_control(self, action: str, group_type: str = None, location: str = None) -> str:
        """处理设备分组控制"""
        await self._refresh_entity_cache()
        
        # 确定要控制的设备列表
        target_entities = []
        
        for entity_id, entity in self._entity_cache.items():
            # 根据分组类型过滤
            if group_type:
                if group_type == "灯" and not entity_id.startswith("light."):
                    continue
                elif group_type == "空调" and not entity_id.startswith("climate."):
                    continue
                elif group_type == "开关" and not entity_id.startswith("switch."):
                    continue
            
            # 根据位置过滤
            if location:
                friendly_name = entity.get('attributes', {}).get('friendly_name', '').lower()
                entity_id_lower = entity_id.lower()
                if location not in friendly_name and location not in entity_id_lower:
                    continue
            
            target_entities.append(entity_id)
        
        if not target_entities:
            if group_type and location:
                return f"❌ 未找到{location}的{group_type}"
            elif group_type:
                return f"❌ 未找到{group_type}"
            elif location:
                return f"❌ 未找到{location}的设备"
            else:
                return "❌ 未找到设备"
        
        # 执行控制操作
        success_count = 0
        api = await self._get_api()
        
        for entity_id in target_entities:
            try:
                if action == "turn_on":
                    await api.turn_on(entity_id)
                elif action == "turn_off":
                    await api.turn_off(entity_id)
                elif action == "toggle":
                    await api.toggle(entity_id)
                success_count += 1
            except Exception as e:
                logger.error(f"控制设备 {entity_id} 失败: {e}")
        
        # 生成响应
        entity_names = []
        for entity_id in target_entities[:3]:  # 只显示前3个设备名称
            friendly_name = self._entity_cache[entity_id].get('attributes', {}).get('friendly_name', entity_id)
            entity_names.append(friendly_name)
        
        if len(target_entities) > 3:
            entity_names.append(f"等{len(target_entities)}个设备")
        
        device_list = "、".join(entity_names)
        
        action_text = {"turn_on": "打开", "turn_off": "关闭", "toggle": "切换"}.get(action, action)
        
        return f"✅ 已{action_text} {device_list}"
    
    async def _handle_natural_language(self, params: Dict) -> str:
        """处理自然语言请求"""
        original_text = params.get("original_text", "").lower()
        
        # 设备分组控制
        if "所有" in original_text:
            if "打开所有" in original_text or "开启所有" in original_text:
                if "灯" in original_text:
                    return await self._handle_group_control("turn_on", "灯")
                elif "空调" in original_text:
                    return await self._handle_group_control("turn_on", "空调")
                elif "开关" in original_text:
                    return await self._handle_group_control("turn_on", "开关")
                else:
                    return await self._handle_group_control("turn_on")
            
            if "关闭所有" in original_text or "关掉所有" in original_text:
                if "灯" in original_text:
                    return await self._handle_group_control("turn_off", "灯")
                elif "空调" in original_text:
                    return await self._handle_group_control("turn_off", "空调")
                elif "开关" in original_text:
                    return await self._handle_group_control("turn_off", "开关")
                else:
                    return await self._handle_group_control("turn_off")
        
        # 按位置分组控制
        locations = ["客厅", "卧室", "厨房", "卫生间", "书房", "阳台"]
        for location in locations:
            if location in original_text:
                if "打开" in original_text or "开启" in original_text:
                    if "灯" in original_text:
                        return await self._handle_group_control("turn_on", "灯", location)
                    elif "空调" in original_text:
                        return await self._handle_group_control("turn_on", "空调", location)
                    else:
                        return await self._handle_group_control("turn_on", None, location)
                
                if "关闭" in original_text or "关掉" in original_text:
                    if "灯" in original_text:
                        return await self._handle_group_control("turn_off", "灯", location)
                    elif "空调" in original_text:
                        return await self._handle_group_control("turn_off", "空调", location)
                    else:
                        return await self._handle_group_control("turn_off", None, location)
        
        # 灯光控制
        if "开灯" in original_text or "打开灯" in original_text or "开一下灯" in original_text:
            device = original_text.replace("开灯", "").replace("打开灯", "").replace("开一下灯", "").replace("把", "").replace("的", "").strip()
            return await self._handle_turn_on({"entity_name": device} if device else {})
        
        if "关灯" in original_text or "关闭灯" in original_text or "关一下灯" in original_text:
            device = original_text.replace("关灯", "").replace("关闭灯", "").replace("关一下灯", "").replace("把", "").replace("的", "").strip()
            return await self._handle_turn_off({"entity_name": device} if device else {})
        
        if "调亮" in original_text or "调高" in original_text or "亮一点" in original_text or "亮度调高" in original_text:
            device = original_text.replace("调亮", "").replace("调高", "").replace("亮一点", "").replace("亮度调高", "").replace("把", "").replace("的", "").strip()
            return await self._handle_set_brightness({"entity_name": device, "brightness": "高"})
        
        if "调暗" in original_text or "调低" in original_text or "暗一点" in original_text or "亮度调低" in original_text:
            device = original_text.replace("调暗", "").replace("调低", "").replace("暗一点", "").replace("亮度调低", "").replace("把", "").replace("的", "").strip()
            return await self._handle_set_brightness({"entity_name": device, "brightness": "低"})
        
        # 空调控制
        if "开空调" in original_text or "打开空调" in original_text or "启动空调" in original_text:
            device = original_text.replace("开空调", "").replace("打开空调", "").replace("启动空调", "").replace("把", "").replace("的", "").strip()
            return await self._handle_turn_on({"entity_name": device if device else "空调"})
        
        if "关空调" in original_text or "关闭空调" in original_text or "停止空调" in original_text:
            device = original_text.replace("关空调", "").replace("关闭空调", "").replace("停止空调", "").replace("把", "").replace("的", "").strip()
            return await self._handle_turn_off({"entity_name": device if device else "空调"})
        
        # 温度控制
        import re
        temp_match = re.search(r'(\d+)\s*度', original_text)
        if temp_match and ("空调" in original_text or "温度" in original_text or "调到" in original_text):
            device = original_text.replace("空调", "").replace("温度", "").replace("调到", "").replace(temp_match.group(1), "").replace("度", "").replace("把", "").replace("的", "").strip()
            return await self._handle_set_temperature({"entity_name": device if device else "空调", "temperature": temp_match.group(1)})
        
        # 空调模式
        if "制冷" in original_text or "冷气" in original_text:
            device = original_text.replace("制冷", "").replace("冷气", "").replace("把", "").replace("的", "").strip()
            return await self._handle_set_hvac_mode({"entity_name": device if device else "空调", "mode": "制冷"})
        
        if "制热" in original_text or "暖气" in original_text:
            device = original_text.replace("制热", "").replace("暖气", "").replace("把", "").replace("的", "").strip()
            return await self._handle_set_hvac_mode({"entity_name": device if device else "空调", "mode": "制热"})
        
        if "自动" in original_text and "空调" in original_text:
            device = original_text.replace("自动", "").replace("空调", "").replace("把", "").replace("的", "").strip()
            return await self._handle_set_hvac_mode({"entity_name": device if device else "空调", "mode": "自动"})
        
        # 场景控制
        if "场景" in original_text or "模式" in original_text:
            scene = original_text.replace("场景", "").replace("模式", "").replace("执行", "").replace("激活", "").replace("打开", "").strip()
            return await self._handle_execute_scene({"scene_name": scene})
        
        # 设备状态查询
        if "状态" in original_text or "查询" in original_text or "怎么样" in original_text or "如何" in original_text:
            device = original_text.replace("状态", "").replace("查询", "").replace("怎么样", "").replace("如何", "").replace("的", "").strip()
            if device:
                return await self._handle_query_state({"entity_name": device})
            else:
                return await self._handle_query_state({})
        
        # 开关控制
        if "打开" in original_text or "开启" in original_text or "启动" in original_text:
            device = original_text.replace("打开", "").replace("开启", "").replace("启动", "").replace("把", "").replace("的", "").strip()
            if device and "灯" not in device and "空调" not in device:
                return await self._handle_turn_on({"entity_name": device})
        
        if "关闭" in original_text or "关掉" in original_text or "停止" in original_text:
            device = original_text.replace("关闭", "").replace("关掉", "").replace("停止", "").replace("把", "").replace("的", "").strip()
            if device and "灯" not in device and "空调" not in device:
                return await self._handle_turn_off({"entity_name": device})
        
        # 切换设备状态
        if "切换" in original_text or "开关" in original_text or "切换状态" in original_text:
            device = original_text.replace("切换", "").replace("开关", "").replace("切换状态", "").replace("把", "").replace("的", "").strip()
            return await self._handle_toggle({"entity_name": device} if device else {})
        
        # 列出设备
        if "有哪些" in original_text or "设备" in original_text or "列表" in original_text:
            return await self._handle_list_entities({})
        
        # 自动化规则管理
        if "创建自动化规则" in original_text or "添加自动化规则" in original_text:
            # 简单的规则创建示例，实际应用中可能需要更复杂的解析
            return "✅ 请提供规则名称、触发条件和执行动作，例如：'创建自动化规则 晚上回家 当我到家时 打开客厅灯'"
        
        if "删除自动化规则" in original_text:
            rule_name = original_text.replace("删除自动化规则", "").strip()
            if rule_name:
                return await self._handle_delete_automation_rule({"rule_name": rule_name})
            else:
                return "❌ 请指定要删除的自动化规则名称"
        
        if "自动化规则列表" in original_text or "列出自动化规则" in original_text:
            return await self._handle_list_automation_rules({})
        
        if "启用自动化规则" in original_text:
            rule_name = original_text.replace("启用自动化规则", "").strip()
            if rule_name:
                return await self._handle_toggle_automation_rule({"rule_name": rule_name})
            else:
                return "❌ 请指定要启用的自动化规则名称"
        
        if "禁用自动化规则" in original_text:
            rule_name = original_text.replace("禁用自动化规则", "").strip()
            if rule_name:
                return await self._handle_toggle_automation_rule({"rule_name": rule_name})
            else:
                return "❌ 请指定要禁用的自动化规则名称"
        
        # 窗帘控制
        if "打开窗帘" in original_text or "拉开窗帘" in original_text:
            device = original_text.replace("打开窗帘", "").replace("拉开窗帘", "").strip()
            return await self._handle_open_cover({"entity_name": device})
        
        if "关闭窗帘" in original_text or "拉上窗帘" in original_text:
            device = original_text.replace("关闭窗帘", "").replace("拉上窗帘", "").strip()
            return await self._handle_close_cover({"entity_name": device})
        
        if "切换窗帘" in original_text or "窗帘开关" in original_text:
            device = original_text.replace("切换窗帘", "").replace("窗帘开关", "").strip()
            return await self._handle_toggle_cover({"entity_name": device})
        
        # 门锁控制
        if "锁门" in original_text or "关门" in original_text:
            device = original_text.replace("锁门", "").replace("关门", "").strip()
            return await self._handle_lock({"entity_name": device})
        
        if "开门" in original_text or "解锁" in original_text:
            device = original_text.replace("开门", "").replace("解锁", "").strip()
            return await self._handle_unlock({"entity_name": device})
        
        # 风扇控制
        if "打开风扇" in original_text:
            device = original_text.replace("打开风扇", "").strip()
            return await self._handle_control_fan({"action": "on", "entity_name": device})
        
        if "关闭风扇" in original_text:
            device = original_text.replace("关闭风扇", "").strip()
            return await self._handle_control_fan({"action": "off", "entity_name": device})
        
        if "风扇速度" in original_text:
            device = original_text.replace("风扇速度", "").strip()
            # 简单的速度解析，实际应用中可能需要更复杂的解析
            speed = "medium"
            if "低速" in original_text:
                speed = "low"
            elif "高速" in original_text:
                speed = "high"
            return await self._handle_control_fan({"action": "on", "entity_name": device, "speed": speed})
        
        # 传感器查询
        if "温度" in original_text or "湿度" in original_text or "传感器" in original_text:
            return await self._handle_query_sensors({})
        
        return "❌ 无法理解您的请求，请尝试更具体的指令，如'打开客厅灯'或'空调调到26度'"
    
    async def cleanup(self):
        """清理资源"""
        if self.api:
            await self.api.close()
