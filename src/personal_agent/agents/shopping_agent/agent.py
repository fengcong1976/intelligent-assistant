"""
Shopping Agent - 购物助手智能体
支持商品比价、优惠信息聚合、购物清单管理、个性化商品推荐等功能
"""
import asyncio
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from loguru import logger

from ..base import BaseAgent, Task, Message


@dataclass
class ShoppingItem:
    """购物项"""
    id: str = field(default_factory=lambda: f"item_{uuid.uuid4().hex[:12]}")
    name: str = ""
    price: float = 0.0
    quantity: int = 1
    category: str = "其他"
    store: str = ""
    url: str = ""
    notes: str = ""
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    checked: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ShoppingItem":
        return cls(**data)


@dataclass
class ShoppingList:
    """购物清单"""
    id: str = field(default_factory=lambda: f"list_{uuid.uuid4().hex[:12]}")
    name: str = "默认清单"
    items: List[ShoppingItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ShoppingList":
        items = [ShoppingItem.from_dict(item_data) for item_data in data.get("items", [])]
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            items=items,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class Product:
    """商品信息"""
    id: str
    name: str
    price: float
    store: str
    url: str
    image: str = ""
    rating: float = 0.0
    reviews: int = 0
    description: str = ""
    category: str = ""


class ShoppingManager:
    """购物数据管理器"""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path.home() / ".personal_agent" / "shopping"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lists_file = self.data_dir / "lists.json"
        self.history_file = self.data_dir / "history.json"
        self.preferences_file = self.data_dir / "preferences.json"
        
        self.lists: Dict[str, ShoppingList] = {}
        self.history: List[Dict] = []
        self.preferences: Dict[str, Any] = {}
        
        self._load_data()

    def _load_data(self):
        """加载数据"""
        try:
            if self.lists_file.exists():
                with open(self.lists_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.lists = {
                        k: ShoppingList.from_dict(v) for k, v in data.items()
                    }
                logger.info(f"🛒 已加载 {len(self.lists)} 个购物清单")
            
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
                logger.info(f"🛒 已加载 {len(self.history)} 条购物历史")
            
            if self.preferences_file.exists():
                with open(self.preferences_file, "r", encoding="utf-8") as f:
                    self.preferences = json.load(f)
                logger.info("🛒 已加载购物偏好设置")
        except Exception as e:
            logger.error(f"加载购物数据失败: {e}")
            self.lists = {}
            self.history = []
            self.preferences = {}

    def _save_data(self):
        """保存数据"""
        try:
            with open(self.lists_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self.lists.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            
            with open(self.preferences_file, "w", encoding="utf-8") as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存购物数据失败: {e}")

    def create_list(self, name: str) -> ShoppingList:
        """创建购物清单"""
        shopping_list = ShoppingList(name=name)
        self.lists[shopping_list.id] = shopping_list
        self._save_data()
        return shopping_list

    def get_list(self, list_id: str) -> Optional[ShoppingList]:
        """获取购物清单"""
        return self.lists.get(list_id)

    def update_list(self, list_id: str, name: Optional[str] = None) -> Optional[ShoppingList]:
        """更新购物清单"""
        shopping_list = self.lists.get(list_id)
        if shopping_list:
            if name:
                shopping_list.name = name
            shopping_list.updated_at = datetime.now().isoformat()
            self._save_data()
        return shopping_list

    def delete_list(self, list_id: str) -> bool:
        """删除购物清单"""
        if list_id in self.lists:
            del self.lists[list_id]
            self._save_data()
            return True
        return False

    def add_item(self, list_id: str, item: ShoppingItem) -> Optional[ShoppingItem]:
        """添加购物项"""
        shopping_list = self.lists.get(list_id)
        if shopping_list:
            shopping_list.items.append(item)
            shopping_list.updated_at = datetime.now().isoformat()
            self._save_data()
            return item
        return None

    def update_item(self, list_id: str, item_id: str, **kwargs) -> Optional[ShoppingItem]:
        """更新购物项"""
        shopping_list = self.lists.get(list_id)
        if shopping_list:
            for item in shopping_list.items:
                if item.id == item_id:
                    for key, value in kwargs.items():
                        if hasattr(item, key) and value is not None:
                            setattr(item, key, value)
                    shopping_list.updated_at = datetime.now().isoformat()
                    self._save_data()
                    return item
        return None

    def delete_item(self, list_id: str, item_id: str) -> bool:
        """删除购物项"""
        shopping_list = self.lists.get(list_id)
        if shopping_list:
            original_length = len(shopping_list.items)
            shopping_list.items = [item for item in shopping_list.items if item.id != item_id]
            if len(shopping_list.items) != original_length:
                shopping_list.updated_at = datetime.now().isoformat()
                self._save_data()
                return True
        return False

    def toggle_item(self, list_id: str, item_id: str) -> Optional[ShoppingItem]:
        """切换购物项状态"""
        shopping_list = self.lists.get(list_id)
        if shopping_list:
            for item in shopping_list.items:
                if item.id == item_id:
                    item.checked = not item.checked
                    shopping_list.updated_at = datetime.now().isoformat()
                    self._save_data()
                    return item
        return None

    def add_to_history(self, item: Dict):
        """添加购物历史"""
        history_item = {
            "id": f"hist_{uuid.uuid4().hex[:12]}",
            "item": item,
            "purchased_at": datetime.now().isoformat()
        }
        self.history.append(history_item)
        # 只保留最近100条历史记录
        if len(self.history) > 100:
            self.history = self.history[-100:]
        self._save_data()

    def update_preferences(self, preferences: Dict):
        """更新购物偏好"""
        self.preferences.update(preferences)
        self._save_data()

    def get_preferences(self) -> Dict:
        """获取购物偏好"""
        return self.preferences


class ProductSearcher:
    """商品搜索器"""

    def __init__(self):
        # 价格缓存，格式: {product_name: {"timestamp": float, "products": List[Product]}}
        self.price_cache = {}
        # 缓存过期时间（秒）
        self.cache_expiry = 3600  # 1小时
        # 模拟商品数据
        self.mock_products = [
            Product(
                id="prod_001",
                name="iPhone 16 Pro Max",
                price=9999.00,
                store="Apple官方旗舰店",
                url="https://example.com/iphone16",
                image="https://example.com/iphone16.jpg",
                rating=4.8,
                reviews=1250,
                description="最新款iPhone，搭载A18 Pro芯片",
                category="电子产品"
            ),
            Product(
                id="prod_002",
                name="AirPods Pro 2",
                price=1899.00,
                store="Apple官方旗舰店",
                url="https://example.com/airpods",
                image="https://example.com/airpods.jpg",
                rating=4.7,
                reviews=2000,
                description="主动降噪耳机，支持空间音频",
                category="电子产品"
            ),
            Product(
                id="prod_003",
                name="MacBook Air M3",
                price=7999.00,
                store="Apple官方旗舰店",
                url="https://example.com/macbook",
                image="https://example.com/macbook.jpg",
                rating=4.9,
                reviews=850,
                description="轻薄便携，搭载M3芯片",
                category="电子产品"
            ),
            Product(
                id="prod_004",
                name="Nike Air Max 270",
                price=899.00,
                store="Nike官方旗舰店",
                url="https://example.com/nike",
                image="https://example.com/nike.jpg",
                rating=4.6,
                reviews=1500,
                description="舒适缓震，时尚外观",
                category="服装鞋包"
            ),
            Product(
                id="prod_005",
                name="Adidas Ultraboost 22",
                price=1299.00,
                store="Adidas官方旗舰店",
                url="https://example.com/adidas",
                image="https://example.com/adidas.jpg",
                rating=4.7,
                reviews=950,
                description="BOOST中底，提供卓越缓震",
                category="服装鞋包"
            ),
            Product(
                id="prod_006",
                name="Sony WH-1000XM5",
                price=2999.00,
                store="Sony官方旗舰店",
                url="https://example.com/sony",
                image="https://example.com/sony.jpg",
                rating=4.9,
                reviews=1100,
                description="业界领先的降噪耳机",
                category="电子产品"
            ),
            Product(
                id="prod_007",
                name="华为 Mate 60 Pro",
                price=6999.00,
                store="华为官方旗舰店",
                url="https://example.com/huawei",
                image="https://example.com/huawei.jpg",
                rating=4.7,
                reviews=1800,
                description="搭载麒麟9000S芯片",
                category="电子产品"
            ),
            Product(
                id="prod_008",
                name="小米 14 Ultra",
                price=5999.00,
                store="小米官方旗舰店",
                url="https://example.com/xiaomi",
                image="https://example.com/xiaomi.jpg",
                rating=4.6,
                reviews=1350,
                description="徕卡四摄，骁龙8 Gen 3",
                category="电子产品"
            ),
        ]
        
        # 电商平台URL
        self.platforms = {
            "天猫超市": "https://s.tmall.com/search?q=特仑苏纯牛奶250ml*16盒",
            "京东": "https://search.jd.com/Search?keyword=特仑苏纯牛奶250ml*16盒",
            "苏宁": "https://search.suning.com/特仑苏纯牛奶250ml*16盒/"
        }

    async def _crawl_telunsu_prices(self) -> List[Product]:
        """抓取特仑苏纯牛奶价格"""
        import asyncio
        import re
        from typing import List, Optional
        import httpx
        
        products = []
        
        # 特仑苏纯牛奶规格配置
        specifications = [
            {"name": "250ml*10包", "keyword": "特仑苏纯牛奶250ml*10包"},
            {"name": "250ml*16盒", "keyword": "特仑苏纯牛奶250ml*16盒"},
            {"name": "250ml*20瓶", "keyword": "特仑苏纯牛奶250ml*20瓶"},
            {"name": "250ml*12包", "keyword": "特仑苏有机纯牛奶250ml*12包"}
        ]
        
        # 平台配置
        platforms = {
            "京东": {
                "base_url": "https://search.jd.com/Search?keyword=",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            },
            "淘宝": {
                "base_url": "https://s.taobao.com/search?q=",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            },
            "天猫": {
                "base_url": "https://list.tmall.com/search_product.htm?q=",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            },
            "拼多多": {
                "base_url": "https://mobile.yangkeduo.com/search_result.html?search_key=",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for spec in specifications:
                spec_name = spec["name"]
                keyword = spec["keyword"]
                logger.info(f"🔍 开始抓取{spec_name}规格的价格")
                
                for platform_name, platform_config in platforms.items():
                    try:
                        logger.info(f"🔍 抓取{platform_name}{spec_name}特仑苏价格")
                        
                        # 构建URL
                        import urllib.parse
                        url = platform_config["base_url"] + urllib.parse.quote(keyword)
                        
                        # 发送HTTP请求
                        response = await client.get(
                            url,
                            headers=platform_config["headers"]
                        )
                        # 不使用raise_for_status，允许处理重定向后的状态码
                        html = response.text
                        
                        logger.info(f"✅ {platform_name}页面加载成功，状态码: {response.status_code}")
                        
                        # 从HTML中提取价格
                        logger.info(f"🔍 开始提取{platform_name}{spec_name}价格")
                        
                        # 清理HTML，提取纯文本
                        text = re.sub(r'<[^>]+>', ' ', html)
                        text = re.sub(r'\s+', ' ', text)
                        text = text.strip()
                        
                        # 定义多种价格提取模式
                        price_patterns = [
                            r'¥\s*\d+\.\d+',  # ¥ 123.45
                            r'\d+\.\d+\s*元',  # 123.45 元
                            r'价格\s*[:：]\s*¥?\s*\d+\.\d+',  # 价格: ¥123.45
                            r'售价\s*[:：]\s*¥?\s*\d+\.\d+',  # 售价: 123.45
                            r'¥?\s*\d+\.\d+',  # 123.45 或 ¥123.45
                        ]
                        
                        # 尝试每种价格提取模式
                        extracted_prices = []
                        for pattern in price_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            for match in matches:
                                # 提取数字部分
                                price_match = re.search(r'\d+\.\d+', match)
                                if price_match:
                                    price = float(price_match.group())
                                    extracted_prices.append(price)
                        
                        # 过滤和排序价格
                        if extracted_prices:
                            # 根据规格设置合理的价格范围
                            if "10包" in spec_name:
                                min_price, max_price = 30, 80
                            elif "16盒" in spec_name:
                                min_price, max_price = 40, 100
                            elif "20瓶" in spec_name:
                                min_price, max_price = 50, 120
                            elif "有机" in spec_name:
                                min_price, max_price = 50, 120
                            else:
                                min_price, max_price = 20, 100
                            
                            # 过滤不合理的价格
                            valid_prices = [p for p in extracted_prices if p >= min_price and p <= max_price]
                            if valid_prices:
                                # 按价格排序，取中间值
                                valid_prices.sort()
                                # 取中间值作为最终价格
                                if len(valid_prices) % 2 == 0:
                                    final_price = (valid_prices[len(valid_prices)//2 - 1] + valid_prices[len(valid_prices)//2]) / 2
                                else:
                                    final_price = valid_prices[len(valid_prices)//2]
                                
                                logger.info(f"💰 {platform_name}{spec_name}价格: ¥{final_price}")
                                
                                # 提取促销信息
                                promotion_info = ""
                                
                                # 查找促销信息的模式
                                promotion_patterns = [
                                    r'优惠后\s*[:：]\s*¥?\s*\d+\.\d+',
                                    r'实付\s*[:：]\s*¥?\s*\d+\.\d+',
                                    r'满\d+减\d+',
                                    r'满\d+元减\d+元',
                                    r'优惠券\s*[:：]\s*¥?\s*\d+',
                                    r'补贴\s*[:：]\s*¥?\s*\d+',
                                    r'限时\s*[:：]\s*¥?\s*\d+\.\d+',
                                    r'秒杀\s*[:：]\s*¥?\s*\d+\.\d+',
                                ]
                                
                                for pattern in promotion_patterns:
                                    promotion_matches = re.findall(pattern, text, re.IGNORECASE)
                                    if promotion_matches:
                                        promotion_info = " | ".join(promotion_matches[:3])  # 最多取3个促销信息
                                        break
                                
                                # 构建完整描述
                                full_description = f"特仑苏纯牛奶{spec_name}"
                                if promotion_info:
                                    full_description += f" ({promotion_info})"
                                
                                products.append(Product(
                                    id=f"prod_{platform_name.lower()}_{spec_name.replace('*', 'x')}",
                                    name="特仑苏纯牛奶",
                                    price=final_price,
                                    store=platform_name,
                                    url=url,
                                    image="https://example.com/telunsu.jpg",
                                    rating=4.8,
                                    reviews=10000,
                                    description=full_description,
                                    category="食品饮料"
                                ))
                            else:
                                # 尝试扩大价格范围
                                extended_prices = [p for p in extracted_prices if p >= min_price/2 and p <= max_price*1.5]
                                if extended_prices:
                                    extended_prices.sort()
                                    if len(extended_prices) % 2 == 0:
                                        final_price = (extended_prices[len(extended_prices)//2 - 1] + extended_prices[len(extended_prices)//2]) / 2
                                    else:
                                        final_price = extended_prices[len(extended_prices)//2]
                                    
                                    logger.info(f"💰 {platform_name}{spec_name}价格（扩大范围）: ¥{final_price}")
                                    
                                    products.append(Product(
                                        id=f"prod_{platform_name.lower()}_{spec_name.replace('*', 'x')}",
                                        name="特仑苏纯牛奶",
                                        price=final_price,
                                        store=platform_name,
                                        url=url,
                                        image="https://example.com/telunsu.jpg",
                                        rating=4.8,
                                        reviews=10000,
                                        description=f"特仑苏纯牛奶{spec_name}",
                                        category="食品饮料"
                                    ))
                                else:
                                    logger.warning(f"❌ {platform_name}{spec_name}未找到有效价格")
                        else:
                            # 尝试从HTML中直接提取价格（针对JavaScript渲染的页面）
                            # 查找包含价格的JavaScript变量
                            js_price_patterns = [
                                r'price\s*[:=]\s*["\']?\d+\.\d+["\']?',
                                r'price\s*[:=]\s*\d+',
                                r'priceInfo\s*[:=]\s*\{[^\}]*\bprice\b\s*[:=]\s*["\']?\d+\.\d+["\']?',
                            ]
                            
                            for pattern in js_price_patterns:
                                matches = re.findall(pattern, html, re.DOTALL)
                                for match in matches:
                                    price_match = re.search(r'\d+\.\d+', match)
                                    if price_match:
                                        price = float(price_match.group())
                                        # 根据规格检查价格合理性
                                        if "10包" in spec_name:
                                            if 30 <= price <= 80:
                                                logger.info(f"💰 {platform_name}{spec_name}价格（从JS中提取）: ¥{price}")
                                                products.append(Product(
                                                    id=f"prod_{platform_name.lower()}_{spec_name.replace('*', 'x')}",
                                                    name="特仑苏纯牛奶",
                                                    price=price,
                                                    store=platform_name,
                                                    url=url,
                                                    image="https://example.com/telunsu.jpg",
                                                    rating=4.8,
                                                    reviews=10000,
                                                    description=f"特仑苏纯牛奶{spec_name}",
                                                    category="食品饮料"
                                                ))
                                                break
                                        elif "16盒" in spec_name:
                                            if 40 <= price <= 100:
                                                logger.info(f"💰 {platform_name}{spec_name}价格（从JS中提取）: ¥{price}")
                                                products.append(Product(
                                                    id=f"prod_{platform_name.lower()}_{spec_name.replace('*', 'x')}",
                                                    name="特仑苏纯牛奶",
                                                    price=price,
                                                    store=platform_name,
                                                    url=url,
                                                    image="https://example.com/telunsu.jpg",
                                                    rating=4.8,
                                                    reviews=10000,
                                                    description=f"特仑苏纯牛奶{spec_name}",
                                                    category="食品饮料"
                                                ))
                                                break
                                        elif "20瓶" in spec_name:
                                            if 50 <= price <= 120:
                                                logger.info(f"💰 {platform_name}{spec_name}价格（从JS中提取）: ¥{price}")
                                                products.append(Product(
                                                    id=f"prod_{platform_name.lower()}_{spec_name.replace('*', 'x')}",
                                                    name="特仑苏纯牛奶",
                                                    price=price,
                                                    store=platform_name,
                                                    url=url,
                                                    image="https://example.com/telunsu.jpg",
                                                    rating=4.8,
                                                    reviews=10000,
                                                    description=f"特仑苏纯牛奶{spec_name}",
                                                    category="食品饮料"
                                                ))
                                                break
                                        elif "有机" in spec_name:
                                            if 50 <= price <= 120:
                                                logger.info(f"💰 {platform_name}{spec_name}价格（从JS中提取）: ¥{price}")
                                                products.append(Product(
                                                    id=f"prod_{platform_name.lower()}_{spec_name.replace('*', 'x')}",
                                                    name="特仑苏纯牛奶",
                                                    price=price,
                                                    store=platform_name,
                                                    url=url,
                                                    image="https://example.com/telunsu.jpg",
                                                    rating=4.8,
                                                    reviews=10000,
                                                    description=f"特仑苏纯牛奶{spec_name}",
                                                    category="食品饮料"
                                                ))
                                                break
                                    
                                else:
                                    continue
                                break
                            else:
                                logger.warning(f"❌ {platform_name}{spec_name}未找到价格信息")
                        
                        # 避免请求过于频繁
                        await asyncio.sleep(1.0)
                        
                    except Exception as e:
                        logger.error(f"❌ {platform_name}{spec_name}抓取失败: {e}")
                        continue
        
        # 如果没有抓取到任何价格，使用默认数据
        if not products:
            logger.warning("⚠️ 所有平台抓取失败，使用默认价格数据")
            products = [
                Product(
                    id="prod_jd_1",
                    name="特仑苏纯牛奶",
                    price=32.91,
                    store="京东",
                    url="https://search.jd.com/Search?keyword=特仑苏纯牛奶250ml*16盒",
                    image="https://example.com/telunsu.jpg",
                    rating=4.9,
                    reviews=20000,
                    description="特仑苏纯牛奶250ml*16盒",
                    category="食品饮料"
                ),
                Product(
                    id="prod_taobao_1",
                    name="特仑苏纯牛奶",
                    price=29.90,
                    store="淘宝",
                    url="https://s.taobao.com/search?q=特仑苏纯牛奶250ml*16盒",
                    image="https://example.com/telunsu.jpg",
                    rating=4.7,
                    reviews=15000,
                    description="特仑苏纯牛奶250ml*16盒",
                    category="食品饮料"
                ),
                Product(
                    id="prod_tmall_1",
                    name="特仑苏纯牛奶",
                    price=27.09,
                    store="天猫",
                    url="https://s.tmall.com/search?q=特仑苏纯牛奶250ml*16盒",
                    image="https://example.com/telunsu.jpg",
                    rating=4.8,
                    reviews=18000,
                    description="特仑苏纯牛奶250ml*16盒",
                    category="食品饮料"
                ),
                Product(
                    id="prod_pdd_1",
                    name="特仑苏纯牛奶",
                    price=25.99,
                    store="拼多多",
                    url="https://mobile.yangkeduo.com/search_result.html?search_key=特仑苏纯牛奶250ml*16盒",
                    image="https://example.com/telunsu.jpg",
                    rating=4.6,
                    reviews=12000,
                    description="特仑苏纯牛奶250ml*16盒",
                    category="食品饮料"
                ),
            ]
        
        return products

    async def search_products(self, keyword: str, category: Optional[str] = None) -> List[Product]:
        """搜索商品"""
        logger.info(f"🔍 搜索商品: {keyword}, 分类: {category}")
        
        # 模拟网络延迟
        await asyncio.sleep(0.5)
        
        results = []
        for product in self.mock_products:
            if keyword.lower() in product.name.lower() or keyword.lower() in product.description.lower():
                if not category or product.category == category:
                    results.append(product)
        
        return results

    async def compare_prices(self, product_name: str) -> List[Product]:
        """比价功能"""
        logger.info(f"💰 比价商品: {product_name}")
        
        # 检查缓存是否有效
        current_time = time.time()
        if product_name in self.price_cache:
            cache_data = self.price_cache[product_name]
            if current_time - cache_data["timestamp"] < self.cache_expiry:
                logger.info("📦 使用缓存的价格数据")
                # 按价格排序
                cached_results = cache_data["products"]
                cached_results.sort(key=lambda x: x.price)
                return cached_results
            else:
                logger.info("⏰ 缓存已过期，重新抓取价格数据")
        
        # 模拟网络延迟
        await asyncio.sleep(0.8)
        
        # 对于特仑苏纯牛奶，使用网页爬虫抓取真实价格
        if "特仑苏" in product_name and "牛奶" in product_name:
            logger.info("🔄 使用网页爬虫抓取特仑苏纯牛奶价格")
            results = await self._crawl_telunsu_prices()
        else:
            # 其他商品使用模拟数据
            results = []
            for product in self.mock_products:
                if product_name.lower() in product.name.lower():
                    results.append(product)
        
        # 更新缓存
        self.price_cache[product_name] = {
            "timestamp": current_time,
            "products": results
        }
        logger.info("💾 价格数据已缓存")
        
        # 按价格排序
        results.sort(key=lambda x: x.price)
        
        return results

    async def get_deals(self, category: Optional[str] = None) -> List[Dict]:
        """获取优惠信息"""
        logger.info(f"🎁 获取优惠信息: {category}")
        
        # 模拟网络延迟
        await asyncio.sleep(0.5)
        
        # 模拟优惠信息
        deals = [
            {
                "id": "deal_001",
                "title": "Apple官方旗舰店 - 全场满10000减500",
                "description": "购买任意Mac或iPad，可享受满10000减500优惠",
                "start_time": "2026-02-01",
                "end_time": "2026-02-29",
                "store": "Apple官方旗舰店",
                "category": "电子产品"
            },
            {
                "id": "deal_002",
                "title": "Nike官方旗舰店 - 新品8折起",
                "description": "春季新品上市，全场8折起，部分商品低至5折",
                "start_time": "2026-02-15",
                "end_time": "2026-02-28",
                "store": "Nike官方旗舰店",
                "category": "服装鞋包"
            },
            {
                "id": "deal_003",
                "title": "华为官方旗舰店 - Mate 60系列优惠",
                "description": "购买Mate 60系列手机，赠送华为手环",
                "start_time": "2026-02-01",
                "end_time": "2026-02-29",
                "store": "华为官方旗舰店",
                "category": "电子产品"
            },
            {
                "id": "deal_004",
                "title": "小米官方旗舰店 - 全场满3000减200",
                "description": "购买任意小米产品，满3000减200，上不封顶",
                "start_time": "2026-02-20",
                "end_time": "2026-02-28",
                "store": "小米官方旗舰店",
                "category": "电子产品"
            },
        ]
        
        if category:
            deals = [deal for deal in deals if deal.get("category") == category]
        
        return deals


class ShoppingAgent(BaseAgent):
    """购物助手智能体"""
    
    KEYWORD_MAPPINGS = {
        "购物": ("query_deals", {}),
        "比价": ("compare_prices", {}),
        "优惠": ("query_deals", {}),
        "特价": ("query_deals", {}),
        "折扣": ("query_deals", {}),
        "购物清单": ("list_lists", {}),
        "我的清单": ("list_lists", {}),
        "添加清单": ("create_list", {}),
        "新建清单": ("create_list", {}),
        "删除清单": ("delete_list", {}),
        "修改清单": ("update_list", {}),
        "添加商品": ("add_item", {}),
        "删除商品": ("delete_item", {}),
        "修改商品": ("update_item", {}),
        "标记商品": ("toggle_item", {}),
        "搜索商品": ("search_products", {}),
        "查找商品": ("search_products", {}),
    }

    def __init__(self):
        super().__init__(
            name="购物智能体",
            description="购物助手智能体，支持商品比价、优惠信息聚合、购物清单管理、个性化商品推荐等功能"
        )
        
        self.register_capability(
            capability="shopping_query",
            description="购物比价查询。搜索商品在不同平台的价格，帮助用户找到最优惠的购买渠道。",
            parameters={
                "type": "object",
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "商品名称，如'特仑苏纯牛奶'、'iPhone 15'"
                    },
                    "platform": {
                        "type": "string",
                        "description": "指定平台（可选），如'京东'、'淘宝'、'拼多多'"
                    }
                },
                "required": ["product"]
            },
            category="shopping"
        )

        self.shopping_manager = ShoppingManager()
        self.product_searcher = ProductSearcher()
        
        self.register_capability("search_products", "搜索商品")
        self.register_capability("compare_prices", "比较价格")
        self.register_capability("query_deals", "查询优惠")
        self.register_capability("create_list", "创建购物清单")
        self.register_capability("list_lists", "列出购物清单")
        self.register_capability("update_list", "更新购物清单")
        self.register_capability("delete_list", "删除购物清单")
        self.register_capability("add_item", "添加商品")
        self.register_capability("update_item", "更新商品")
        self.register_capability("delete_item", "删除商品")
        self.register_capability("toggle_item", "切换商品状态")
        self.register_capability("recommend_products", "推荐商品")

        logger.info("🛒 购物助手智能体已初始化")

    async def execute_task(self, task: Task) -> Any:
        """执行任务"""
        task_type = task.type
        params = task.params or {}

        logger.info(f"🛒 执行购物任务: {task_type}")

        if task_type == "shopping_query":
            task_type = "search_products"

        if task_type == "search_products":
            result = await self._handle_search_products(params)
        elif task_type == "compare_prices":
            result = await self._handle_compare_prices(params)
        elif task_type == "query_deals":
            result = await self._handle_query_deals(params)
        elif task_type == "create_list":
            result = await self._handle_create_list(params)
        elif task_type == "list_lists":
            result = await self._handle_list_lists(params)
        elif task_type == "update_list":
            result = await self._handle_update_list(params)
        elif task_type == "delete_list":
            result = await self._handle_delete_list(params)
        elif task_type == "add_item":
            result = await self._handle_add_item(params)
        elif task_type == "update_item":
            result = await self._handle_update_item(params)
        elif task_type == "delete_item":
            result = await self._handle_delete_item(params)
        elif task_type == "toggle_item":
            result = await self._handle_toggle_item(params)
        elif task_type == "recommend_products":
            result = await self._handle_recommend_products(params)
        else:
            return f"❌ 不支持的操作: {task_type}"
        
        if result and ("未找到" in result or "不存在" in result):
            task.no_retry = True
        return result

    async def _handle_search_products(self, params: Dict) -> str:
        """搜索商品"""
        keyword = params.get("keyword") or params.get("content")
        category = params.get("category")
        
        if not keyword:
            return "❌ 请提供商品关键词"
        
        products = await self.product_searcher.search_products(keyword, category)
        
        if not products:
            return f"🔍 未找到包含「{keyword}」的商品"
        
        lines = [f"🔍 找到 {len(products)} 个包含「{keyword}」的商品:", ""]
        for i, product in enumerate(products[:5], 1):  # 只显示前5个结果
            lines.append(f"{i}. {product.name}")
            lines.append(f"   💰 价格: ¥{product.price:.2f}")
            lines.append(f"   📦 店铺: {product.store}")
            lines.append(f"   ⭐ 评分: {product.rating} ({product.reviews}条评价)")
            lines.append(f"   🔗 链接: {product.url}")
            lines.append("")
        
        if len(products) > 5:
            lines.append(f"... 还有 {len(products) - 5} 个商品未显示")
        
        return "\n".join(lines)

    async def _handle_compare_prices(self, params: Dict) -> str:
        """比价功能"""
        product_name = params.get("product_name") or params.get("content")
        
        if not product_name:
            return "❌ 请提供商品名称"
        
        products = await self.product_searcher.compare_prices(product_name)
        
        if not products:
            return f"🔍 未找到商品「{product_name}」"
        
        lines = [f"💰 「{product_name}」比价结果:", ""]
        for i, product in enumerate(products, 1):
            lines.append(f"{i}. {product.store}")
            lines.append(f"   价格: ¥{product.price:.2f}")
            lines.append(f"   评分: {product.rating} ({product.reviews}条评价)")
            lines.append(f"   链接: {product.url}")
            lines.append("")
        
        return "\n".join(lines)

    async def _handle_query_deals(self, params: Dict) -> str:
        """查询优惠信息"""
        category = params.get("category")
        
        deals = await self.product_searcher.get_deals(category)
        
        if not deals:
            if category:
                return f"🎁 未找到「{category}」分类的优惠信息"
            return "🎁 暂无可优惠信息"
        
        lines = ["🎁 最新优惠信息:", ""]
        for i, deal in enumerate(deals, 1):
            lines.append(f"{i}. {deal['title']}")
            lines.append(f"   📝 描述: {deal['description']}")
            lines.append(f"   📅 时间: {deal['start_time']} 至 {deal['end_time']}")
            lines.append(f"   🏪 店铺: {deal['store']}")
            if 'category' in deal:
                lines.append(f"   📁 分类: {deal['category']}")
            lines.append("")
        
        return "\n".join(lines)

    async def _handle_create_list(self, params: Dict) -> str:
        """创建购物清单"""
        name = params.get("name") or params.get("content")
        
        if not name:
            return "❌ 请提供清单名称"
        
        shopping_list = self.shopping_manager.create_list(name)
        return f"✅ 已创建购物清单: {shopping_list.name}"

    async def _handle_list_lists(self, params: Dict) -> str:
        """列出购物清单"""
        lists = self.shopping_manager.lists
        
        if not lists:
            return "📋 暂无购物清单"
        
        lines = ["📋 我的购物清单:", ""]
        for i, (list_id, shopping_list) in enumerate(lists.items(), 1):
            lines.append(f"{i}. {shopping_list.name}")
            lines.append(f"   📅 创建时间: {shopping_list.created_at.split('T')[0]}")
            lines.append(f"   📦 商品数量: {len(shopping_list.items)}")
            lines.append(f"   ✅ 已完成: {sum(1 for item in shopping_list.items if item.checked)}/{len(shopping_list.items)}")
            lines.append("")
        
        return "\n".join(lines)

    async def _handle_update_list(self, params: Dict) -> str:
        """更新购物清单"""
        list_id = params.get("list_id")
        name = params.get("name")
        
        if not list_id:
            return "❌ 请提供清单ID"
        
        if not name:
            return "❌ 请提供新的清单名称"
        
        shopping_list = self.shopping_manager.update_list(list_id, name)
        if shopping_list:
            return f"✅ 已更新购物清单名称为: {shopping_list.name}"
        return "❌ 找不到指定的购物清单"

    async def _handle_delete_list(self, params: Dict) -> str:
        """删除购物清单"""
        list_id = params.get("list_id")
        
        if not list_id:
            return "❌ 请提供清单ID"
        
        deleted = self.shopping_manager.delete_list(list_id)
        if deleted:
            return "✅ 已删除购物清单"
        return "❌ 找不到指定的购物清单"

    async def _handle_add_item(self, params: Dict) -> str:
        """添加购物项"""
        list_id = params.get("list_id")
        name = params.get("name") or params.get("content")
        price = params.get("price", 0.0)
        quantity = params.get("quantity", 1)
        category = params.get("category", "其他")
        store = params.get("store", "")
        url = params.get("url", "")
        notes = params.get("notes", "")
        
        if not list_id:
            # 如果没有指定清单ID，使用默认清单
            lists = self.shopping_manager.lists
            if lists:
                list_id = next(iter(lists.keys()))
            else:
                # 如果没有清单，创建一个默认清单
                default_list = self.shopping_manager.create_list("默认清单")
                list_id = default_list.id
        
        if not name:
            return "❌ 请提供商品名称"
        
        item = ShoppingItem(
            name=name,
            price=price,
            quantity=quantity,
            category=category,
            store=store,
            url=url,
            notes=notes
        )
        
        added_item = self.shopping_manager.add_item(list_id, item)
        if added_item:
            return f"✅ 已添加商品到购物清单: {added_item.name}"
        return "❌ 添加商品失败"

    async def _handle_update_item(self, params: Dict) -> str:
        """更新购物项"""
        list_id = params.get("list_id")
        item_id = params.get("item_id")
        name = params.get("name")
        price = params.get("price")
        quantity = params.get("quantity")
        category = params.get("category")
        store = params.get("store")
        url = params.get("url")
        notes = params.get("notes")
        
        if not list_id or not item_id:
            return "❌ 请提供清单ID和商品ID"
        
        update_fields = {}
        if name:
            update_fields["name"] = name
        if price is not None:
            update_fields["price"] = price
        if quantity is not None:
            update_fields["quantity"] = quantity
        if category:
            update_fields["category"] = category
        if store:
            update_fields["store"] = store
        if url:
            update_fields["url"] = url
        if notes:
            update_fields["notes"] = notes
        
        if not update_fields:
            return "❌ 没有提供要修改的内容"
        
        updated_item = self.shopping_manager.update_item(list_id, item_id, **update_fields)
        if updated_item:
            return f"✅ 已更新商品: {updated_item.name}"
        return "❌ 更新商品失败"

    async def _handle_delete_item(self, params: Dict) -> str:
        """删除购物项"""
        list_id = params.get("list_id")
        item_id = params.get("item_id")
        
        if not list_id or not item_id:
            return "❌ 请提供清单ID和商品ID"
        
        deleted = self.shopping_manager.delete_item(list_id, item_id)
        if deleted:
            return "✅ 已删除商品"
        return "❌ 删除商品失败"

    async def _handle_toggle_item(self, params: Dict) -> str:
        """切换购物项状态"""
        list_id = params.get("list_id")
        item_id = params.get("item_id")
        
        if not list_id or not item_id:
            return "❌ 请提供清单ID和商品ID"
        
        toggled_item = self.shopping_manager.toggle_item(list_id, item_id)
        if toggled_item:
            status = "已完成" if toggled_item.checked else "未完成"
            return f"✅ 已更新商品状态为: {status}"
        return "❌ 更新商品状态失败"

    async def _handle_recommend_products(self, params: Dict) -> str:
        """推荐商品"""
        category = params.get("category")
        
        # 基于历史购物记录和偏好推荐商品
        preferences = self.shopping_manager.get_preferences()
        
        # 模拟推荐逻辑
        lines = ["🎯 为您推荐的商品:", ""]
        
        # 从模拟数据中选择一些商品作为推荐
        recommended_products = self.product_searcher.mock_products[:3]
        
        for i, product in enumerate(recommended_products, 1):
            lines.append(f"{i}. {product.name}")
            lines.append(f"   💰 价格: ¥{product.price:.2f}")
            lines.append(f"   📦 店铺: {product.store}")
            lines.append(f"   ⭐ 评分: {product.rating} ({product.reviews}条评价)")
            lines.append(f"   🔗 链接: {product.url}")
            lines.append("")
        
        return "\n".join(lines)

    def get_capabilities_description(self) -> str:
        """获取能力描述"""
        return """
### shopping_agent (购物助手智能体)
- 商品搜索: 搜索商品信息，action=search_products, keyword=商品关键词, category=商品分类
- 商品比价: 对比商品在不同店铺的价格，action=compare_prices, product_name=商品名称
- 优惠信息: 获取最新优惠活动，action=query_deals, category=商品分类
- 购物清单管理: 创建、查看、修改、删除购物清单
  - 创建清单: action=create_list, name=清单名称
  - 查看清单: action=list_lists
  - 修改清单: action=update_list, list_id=清单ID, name=新清单名称
  - 删除清单: action=delete_list, list_id=清单ID
- 商品管理: 添加、修改、删除、标记购物清单中的商品
  - 添加商品: action=add_item, list_id=清单ID, name=商品名称, price=价格, quantity=数量
  - 修改商品: action=update_item, list_id=清单ID, item_id=商品ID, name=新商品名称
  - 删除商品: action=delete_item, list_id=清单ID, item_id=商品ID
  - 标记商品: action=toggle_item, list_id=清单ID, item_id=商品ID
- 商品推荐: 基于历史购买记录和偏好推荐商品，action=recommend_products, category=商品分类
- 示例: "搜索iPhone" -> action=search_products, keyword="iPhone"
- 示例: "比价AirPods" -> action=compare_prices, product_name="AirPods"
- 示例: "查看优惠" -> action=query_deals
- 示例: "创建购物清单" -> action=create_list, name="日常用品"
- 示例: "添加商品到购物清单" -> action=add_item, name="牛奶", quantity=2
"""

    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """
🌤️ 购物助手智能体

功能：
- 商品搜索：搜索商品信息和价格
- 商品比价：对比同一商品在不同店铺的价格
- 优惠信息：获取最新的优惠活动和折扣信息
- 购物清单管理：创建、查看、修改、删除购物清单
- 商品管理：在购物清单中添加、修改、删除、标记商品
- 商品推荐：基于历史购买记录和偏好推荐商品

使用方法：
- "搜索iPhone"
- "比价AirPods"
- "查看优惠"
- "创建购物清单 日常用品"
- "添加商品到购物清单 牛奶 2盒"
- "查看我的购物清单"

参数说明：
- keyword: 商品关键词
- product_name: 商品名称
- category: 商品分类
- list_id: 购物清单ID
- item_id: 商品ID
- name: 商品名称或清单名称
- price: 商品价格
- quantity: 商品数量

注意：
- 支持自然语言查询，如"搜索iPhone"、"比价AirPods"等
- 购物清单数据存储在本地，保护用户隐私
- 商品数据为模拟数据，实际使用时可集成真实的购物API
"""
