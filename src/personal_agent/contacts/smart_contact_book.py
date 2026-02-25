"""
Smart Contact Book - 智能通讯录管理模块
支持每个联系人的独立信息库，自动提取和保存联系人信息
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger


@dataclass
class ContactInfo:
    """联系人信息条目"""
    key: str
    value: str
    source: str = "对话"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    confidence: float = 1.0


@dataclass
class Contact:
    """联系人数据类 - 支持独立信息库"""
    name: str
    alias: List[str] = field(default_factory=list)
    email: str = ""
    phone: str = ""
    address: str = ""
    company: str = ""
    position: str = ""
    relationship: str = ""
    notes: str = ""
    
    info_db: Dict[str, ContactInfo] = field(default_factory=dict)
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def add_info(self, key: str, value: str, source: str = "对话", confidence: float = 1.0):
        """添加或更新信息"""
        self.info_db[key] = ContactInfo(
            key=key,
            value=value,
            source=source,
            confidence=confidence
        )
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_info(self, key: str) -> Optional[str]:
        """获取信息"""
        info = self.info_db.get(key)
        return info.value if info else None
    
    def get_all_info(self) -> Dict[str, str]:
        """获取所有信息"""
        return {k: v.value for k, v in self.info_db.items()}
    
    def to_dict(self) -> Dict:
        result = {
            "name": self.name,
            "alias": self.alias,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "company": self.company,
            "position": self.position,
            "relationship": self.relationship,
            "notes": self.notes,
            "info_db": {k: asdict(v) for k, v in self.info_db.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Contact":
        info_db = {}
        for k, v in data.get("info_db", {}).items():
            info_db[k] = ContactInfo(**v)
        
        return cls(
            name=data["name"],
            alias=data.get("alias", []),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            company=data.get("company", ""),
            position=data.get("position", ""),
            relationship=data.get("relationship", ""),
            notes=data.get("notes", ""),
            info_db=info_db,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )
    
    def get_display_info(self) -> str:
        """获取显示信息"""
        lines = [f"📱 {self.name}"]
        
        if self.alias:
            lines.append(f"   别名: {', '.join(self.alias)}")
        if self.phone:
            lines.append(f"   📞 电话: {self.phone}")
        if self.email:
            lines.append(f"   📧 邮箱: {self.email}")
        if self.company:
            lines.append(f"   🏢 公司: {self.company}")
        if self.position:
            lines.append(f"   💼 职位: {self.position}")
        if self.relationship:
            lines.append(f"   👥 关系: {self.relationship}")
        
        if self.info_db:
            lines.append("   📋 详细信息:")
            for key, info in self.info_db.items():
                lines.append(f"      • {key}: {info.value}")
        
        return "\n".join(lines)


class SmartContactBook:
    """智能通讯录管理器"""
    
    INFO_PATTERNS = {
        "生日": [
            r"生日[是为]?\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            r"生日[是为]?\s*(\d{1,2}月\d{1,2}日)",
            r"出生[日期]?\s*(\d{4}年\d{1,2}月\d{1,2}日)",
            r"(\d{4}年\d{1,2}月\d{1,2}日)[出生过生]",
        ],
        "住址": [
            r"[住家]址[是为]?\s*(.+?)(?=[，。！？]|$)",
            r"住在(.+?)(?=[，。！？]|$)",
            r"家在(.+?)(?=[，。！？]|$)",
            r"居住在(.+?)(?=[，。！？]|$)",
        ],
        "电话": [
            r"电话[是为]?\s*(\d{11})",
            r"手机[是为]?\s*(\d{11})",
            r"联系方式[是为]?\s*(\d{11})",
        ],
        "邮箱": [
            r"邮箱[是为]?\s*([\w.-]+@[\w.-]+\.\w+)",
            r"邮件[是为]?\s*([\w.-]+@[\w.-]+\.\w+)",
            r"email[是为]?\s*([\w.-]+@[\w.-]+\.\w+)",
        ],
        "公司": [
            r"公司[是为]?\s*(.+?)(?=[，。！？]|$)",
            r"单位[是为]?\s*(.+?)(?=[，。！？]|$)",
            r"在(.+?)工作",
        ],
        "职位": [
            r"职位[是为]?\s*(.+?)(?=[，。！？]|$)",
            r"职务[是为]?\s*(.+?)(?=[，。！？]|$)",
            r"担任(.+?)(?=[，。！？]|$)",
        ],
        "爱好": [
            r"爱好[是为]?\s*(.+?)(?=[，。！？]|$)",
            r"喜欢(.+?)(?=[，。！？]|$)",
            r"兴趣爱好[是为]?\s*(.+?)(?=[，。！？]|$)",
        ],
        "年龄": [
            r"年龄[是为]?\s*(\d+)[岁]?",
            r"(\d+)岁",
        ],
    }
    
    def __init__(self, data_path: str = "./data/contacts.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._contacts: Dict[str, Contact] = {}
        self._alias_map: Dict[str, str] = {}
        self._load()
    
    def _load(self):
        """加载通讯录"""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if "contacts" in data:
                        contacts_data = data.get("contacts", {})
                    else:
                        contacts_data = data
                    
                    for name, contact_data in contacts_data.items():
                        if isinstance(contact_data, dict):
                            contact = Contact.from_dict(contact_data)
                            self._contacts[name] = contact
                            for alias in contact.alias:
                                self._alias_map[alias.lower()] = name
                            self._alias_map[name.lower()] = name
            except Exception as e:
                logger.error(f"加载通讯录失败: {e}")
    
    def _save(self):
        """保存通讯录"""
        try:
            data = {name: contact.to_dict() for name, contact in self._contacts.items()}
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("通讯录已保存")
        except Exception as e:
            logger.error(f"保存通讯录失败: {e}")
    
    def _normalize_name(self, name: str) -> str:
        """规范化名称"""
        name = name.strip()
        if name.endswith("总") or name.endswith("经理") or name.endswith("先生") or name.endswith("女士"):
            return name
        return name
    
    def add_contact(self, name: str, alias: List[str] = None, **kwargs) -> Contact:
        """添加或更新联系人"""
        name = self._normalize_name(name)
        
        if name in self._contacts:
            contact = self._contacts[name]
            if alias:
                for a in alias:
                    if a not in contact.alias:
                        contact.alias.append(a)
                        self._alias_map[a.lower()] = name
            for key, value in kwargs.items():
                if value and hasattr(contact, key):
                    setattr(contact, key, value)
        else:
            contact = Contact(name=name, alias=alias or [], **kwargs)
            self._contacts[name] = contact
            self._alias_map[name.lower()] = name
            for a in (alias or []):
                self._alias_map[a.lower()] = name
        
        self._save()
        logger.info(f"✅ 联系人已保存: {name}")
        return contact
    
    def get_contact(self, name: str) -> Optional[Contact]:
        """获取联系人（支持别名查找）"""
        name_lower = name.lower()
        
        if name_lower in self._alias_map:
            actual_name = self._alias_map[name_lower]
            return self._contacts.get(actual_name)
        
        for contact_name, contact in self._contacts.items():
            if name in contact_name or contact_name in name:
                return contact
        
        return None
    
    def add_info_to_contact(self, name: str, key: str, value: str, source: str = "对话") -> bool:
        """为联系人添加信息"""
        contact = self.get_contact(name)
        
        if not contact:
            contact = self.add_contact(name)
        
        contact.add_info(key, value, source)
        self._save()
        
        logger.info(f"📝 已为 {contact.name} 添加信息: {key} = {value}")
        return True
    
    def extract_and_save_info(self, text: str, contact_name: str = None) -> Dict[str, Any]:
        """从文本中提取联系人信息并保存"""
        results = {
            "contact_name": None,
            "extracted_info": {},
            "saved": False
        }
        
        detected_name = contact_name or self._detect_contact_name(text)
        
        if not detected_name:
            return results
        
        results["contact_name"] = detected_name
        
        extracted = self._extract_info_from_text(text)
        results["extracted_info"] = extracted
        
        if extracted:
            contact = self.get_contact(detected_name)
            if not contact:
                contact = self.add_contact(detected_name)
            
            for key, value in extracted.items():
                contact.add_info(key, value, "对话提取")
            
            self._save()
            results["saved"] = True
            logger.info(f"✅ 已为 {contact.name} 提取并保存 {len(extracted)} 条信息")
        
        return results
    
    def _detect_contact_name(self, text: str) -> Optional[str]:
        """从文本中检测联系人名称"""
        patterns = [
            r"([^\s，。！？]{2,4}(?:总|经理|先生|女士|老师|老板))",
            r"([^\s，。！？]{2,3})的",
            r"问([^\s，。！？]{2,4})",
            r"查([^\s，。！？]{2,4})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                potential_name = match.group(1)
                if potential_name in self._alias_map or any(
                    potential_name.lower() == k for k in self._alias_map.keys()
                ):
                    return potential_name
                
                for contact in self._contacts.values():
                    if potential_name in contact.name or potential_name in contact.alias:
                        return contact.name
        
        return None
    
    def _extract_info_from_text(self, text: str) -> Dict[str, str]:
        """从文本中提取信息"""
        extracted = {}
        
        for info_type, patterns in self.INFO_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value and len(value) < 100:
                        extracted[info_type] = value
                        break
        
        return extracted
    
    def query_contact_info(self, name: str, info_key: str = None) -> Optional[str]:
        """查询联系人信息"""
        contact = self.get_contact(name)
        
        if not contact:
            return None
        
        if info_key:
            return contact.get_info(info_key)
        
        return contact.get_display_info()
    
    def search_contacts(self, keyword: str) -> List[Contact]:
        """搜索联系人"""
        keyword = keyword.lower()
        results = []
        
        for contact in self._contacts.values():
            if keyword in contact.name.lower():
                results.append(contact)
                continue
            
            if any(keyword in a.lower() for a in contact.alias):
                results.append(contact)
                continue
            
            if keyword in contact.email.lower() or keyword in contact.phone.lower():
                results.append(contact)
                continue
            
            for info in contact.info_db.values():
                if keyword in info.value.lower():
                    results.append(contact)
                    break
        
        return results
    
    def list_all_contacts(self) -> List[Contact]:
        """列出所有联系人"""
        return list(self._contacts.values())
    
    def delete_contact(self, name: str) -> bool:
        """删除联系人"""
        contact = self.get_contact(name)
        if not contact:
            return False
        
        actual_name = contact.name
        del self._contacts[actual_name]
        
        keys_to_remove = [k for k, v in self._alias_map.items() if v == actual_name]
        for k in keys_to_remove:
            del self._alias_map[k]
        
        self._save()
        logger.info(f"🗑️ 已删除联系人: {actual_name}")
        return True
    
    def get_contacts_by_relationship(self, relationship: str) -> List[Contact]:
        """按关系筛选联系人"""
        results = []
        for contact in self._contacts.values():
            if contact.relationship and relationship.lower() in contact.relationship.lower():
                results.append(contact)
        return results
    
    def get_contact_summary(self, relationship: str = None) -> str:
        """获取通讯录摘要"""
        if not self._contacts:
            return "📭 通讯录为空"
        
        contacts = list(self._contacts.values())
        
        if relationship:
            contacts = self.get_contacts_by_relationship(relationship)
            if not contacts:
                return f"📭 没有关系为「{relationship}」的联系人"
        
        lines = [f"📖 通讯录 (共 {len(contacts)} 人)\n"]
        
        for contact in sorted(contacts, key=lambda c: c.name):
            info_count = len(contact.info_db)
            lines.append(f"• {contact.name}")
            if contact.phone:
                lines[-1] += f" 📞 {contact.phone}"
            if contact.email:
                lines[-1] += f" 📧 {contact.email}"
            if contact.relationship:
                lines[-1] += f" 👥 {contact.relationship}"
            if info_count > 0:
                lines[-1] += f" 📋 {info_count}条信息"
        
        return "\n".join(lines)
    
    def to_prompt_string(self) -> str:
        """转换为提示词格式"""
        if not self._contacts:
            return "通讯录为空"
        
        lines = ["【通讯录】"]
        for contact in self._contacts.values():
            info_parts = [contact.name]
            if contact.phone:
                info_parts.append(f"电话: {contact.phone}")
            if contact.email:
                info_parts.append(f"邮箱: {contact.email}")
            if contact.company:
                info_parts.append(f"公司: {contact.company}")
            
            if contact.info_db:
                for key, info in contact.info_db.items():
                    info_parts.append(f"{key}: {info.value}")
            
            lines.append(" | ".join(info_parts))
        
        return "\n".join(lines)


smart_contact_book = SmartContactBook()
