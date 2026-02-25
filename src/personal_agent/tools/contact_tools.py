"""
Contact Tools - 通讯录工具
"""
from typing import List, Optional
from .base import BaseTool, ToolResult, tool_registry
from ..contacts.smart_contact_book import smart_contact_book, Contact


class SearchContactTool(BaseTool):
    name = "search_contact"
    description = "Search contacts by name, email, phone or company. Use this to find contact information."
    parameters = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Search keyword (name, email, phone, or company)"
            }
        },
        "required": ["keyword"]
    }

    async def execute(self, keyword: str) -> ToolResult:
        contacts = smart_contact_book.search(keyword)
        
        if not contacts:
            return ToolResult(
                success=True,
                output=f"未找到匹配 '{keyword}' 的联系人"
            )
        
        lines = [f"找到 {len(contacts)} 个匹配的联系人：\n"]
        for c in contacts:
            lines.append(f"姓名: {c.name}")
            if c.phone:
                lines.append(f"  电话: {c.phone}")
            if c.email:
                lines.append(f"  邮箱: {c.email}")
            if c.company:
                lines.append(f"  公司: {c.company}")
            if c.position:
                lines.append(f"  职位: {c.position}")
            if c.address:
                lines.append(f"  地址: {c.address}")
            if c.notes:
                lines.append(f"  备注: {c.notes}")
            lines.append("")
        
        return ToolResult(
            success=True,
            output="\n".join(lines).strip()
        )


class ListContactsTool(BaseTool):
    name = "list_contacts"
    description = "List all contacts in the address book."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self) -> ToolResult:
        contacts = smart_contact_book.list_all()
        
        if not contacts:
            return ToolResult(
                success=True,
                output="通讯录为空"
            )
        
        lines = [f"通讯录共有 {len(contacts)} 个联系人：\n"]
        for c in contacts:
            info = c.name
            if c.phone:
                info += f" | 电话: {c.phone}"
            if c.email:
                info += f" | 邮箱: {c.email}"
            lines.append(info)
        
        return ToolResult(
            success=True,
            output="\n".join(lines)
        )


class AddContactTool(BaseTool):
    name = "add_contact"
    description = "Add a new contact to the address book."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Contact name (required)"
            },
            "phone": {
                "type": "string",
                "description": "Phone number"
            },
            "email": {
                "type": "string",
                "description": "Email address"
            },
            "company": {
                "type": "string",
                "description": "Company name"
            },
            "position": {
                "type": "string",
                "description": "Job position"
            },
            "address": {
                "type": "string",
                "description": "Address"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes"
            }
        },
        "required": ["name"]
    }

    async def execute(
        self,
        name: str,
        phone: str = "",
        email: str = "",
        company: str = "",
        position: str = "",
        address: str = "",
        notes: str = ""
    ) -> ToolResult:
        existing = smart_contact_book.get(name)
        if existing:
            return ToolResult(
                success=False,
                output="",
                error=f"联系人 '{name}' 已存在，如需修改请使用 update_contact"
            )
        
        contact = Contact(
            name=name,
            phone=phone,
            email=email,
            company=company,
            position=position,
            address=address,
            notes=notes
        )
        
        if smart_contact_book.add(contact):
            return ToolResult(
                success=True,
                output=f"已添加联系人：{name}"
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error="添加联系人失败"
            )


class UpdateContactTool(BaseTool):
    name = "update_contact"
    description = "Update an existing contact's information."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Contact name to update (required)"
            },
            "phone": {
                "type": "string",
                "description": "New phone number"
            },
            "email": {
                "type": "string",
                "description": "New email address"
            },
            "company": {
                "type": "string",
                "description": "New company name"
            },
            "position": {
                "type": "string",
                "description": "New job position"
            },
            "address": {
                "type": "string",
                "description": "New address"
            },
            "notes": {
                "type": "string",
                "description": "New notes"
            }
        },
        "required": ["name"]
    }

    async def execute(
        self,
        name: str,
        phone: str = None,
        email: str = None,
        company: str = None,
        position: str = None,
        address: str = None,
        notes: str = None
    ) -> ToolResult:
        existing = smart_contact_book.get(name)
        if not existing:
            return ToolResult(
                success=False,
                output="",
                error=f"联系人 '{name}' 不存在"
            )
        
        updates = {}
        if phone is not None:
            updates["phone"] = phone
        if email is not None:
            updates["email"] = email
        if company is not None:
            updates["company"] = company
        if position is not None:
            updates["position"] = position
        if address is not None:
            updates["address"] = address
        if notes is not None:
            updates["notes"] = notes
        
        if not updates:
            return ToolResult(
                success=True,
                output="没有需要更新的信息"
            )
        
        if smart_contact_book.update(name, **updates):
            return ToolResult(
                success=True,
                output=f"已更新联系人 '{name}' 的信息"
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error="更新联系人失败"
            )


class DeleteContactTool(BaseTool):
    name = "delete_contact"
    description = "Delete a contact from the address book."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Contact name to delete"
            }
        },
        "required": ["name"]
    }

    async def execute(self, name: str) -> ToolResult:
        if smart_contact_book.delete(name):
            return ToolResult(
                success=True,
                output=f"已删除联系人：{name}"
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"联系人 '{name}' 不存在"
            )


class GetContactEmailTool(BaseTool):
    name = "get_contact_email"
    description = "Get email address of a contact by name. Use this when user wants to send email to someone in their contacts."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Contact name"
            }
        },
        "required": ["name"]
    }

    async def execute(self, name: str) -> ToolResult:
        contact = smart_contact_book.get(name)
        if not contact:
            return ToolResult(
                success=False,
                output="",
                error=f"未找到联系人 '{name}'"
            )
        
        if not contact.email:
            return ToolResult(
                success=False,
                output="",
                error=f"联系人 '{name}' 没有设置邮箱"
            )
        
        return ToolResult(
            success=True,
            output=f"{name} 的邮箱: {contact.email}"
        )


class GetContactPhoneTool(BaseTool):
    name = "get_contact_phone"
    description = "Get phone number of a contact by name."
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Contact name"
            }
        },
        "required": ["name"]
    }

    async def execute(self, name: str) -> ToolResult:
        contact = smart_contact_book.get(name)
        if not contact:
            return ToolResult(
                success=False,
                output="",
                error=f"未找到联系人 '{name}'"
            )
        
        if not contact.phone:
            return ToolResult(
                success=False,
                output="",
                error=f"联系人 '{name}' 没有设置电话"
            )
        
        return ToolResult(
            success=True,
            output=f"{name} 的电话: {contact.phone}"
        )


def register_contact_tools():
    """Register contact tools to the tool registry"""
    tool_registry.register(SearchContactTool())
    tool_registry.register(ListContactsTool())
    tool_registry.register(AddContactTool())
    tool_registry.register(UpdateContactTool())
    tool_registry.register(DeleteContactTool())
    tool_registry.register(GetContactEmailTool())
    tool_registry.register(GetContactPhoneTool())
