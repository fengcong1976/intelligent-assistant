"""
Short-term Memory - Session-based conversation history
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles

from .base import BaseMemory, MemoryItem


class ConversationTurn:
    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None
    ):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationTurn":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class ShortTermMemory(BaseMemory):
    def __init__(self, session_id: str, storage_path: Optional[Path] = None):
        self.session_id = session_id
        self.storage_path = storage_path or Path("./data/sessions")
        self.conversation_history: List[ConversationTurn] = []
        self._loaded = False

    async def _ensure_loaded(self):
        if not self._loaded:
            await self._load_from_disk()
            self._loaded = True

    async def _load_from_disk(self):
        file_path = self.storage_path / f"{self.session_id}.jsonl"
        if file_path.exists():
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                for line in content.strip().split("\n"):
                    if line:
                        data = json.loads(line)
                        self.conversation_history.append(
                            ConversationTurn.from_dict(data)
                        )

    async def _save_to_disk(self):
        self.storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self.storage_path / f"{self.session_id}.jsonl"
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            for turn in self.conversation_history:
                await f.write(json.dumps(turn.to_dict(), ensure_ascii=False) + "\n")

    async def add_user_message(self, content: str):
        await self._ensure_loaded()
        self.conversation_history.append(
            ConversationTurn(role="user", content=content)
        )
        await self._save_to_disk()

    async def add_assistant_message(self, content: str):
        await self._ensure_loaded()
        self.conversation_history.append(
            ConversationTurn(role="assistant", content=content)
        )
        await self._save_to_disk()

    async def add_tool_message(self, content: str, tool_name: str):
        await self._ensure_loaded()
        self.conversation_history.append(
            ConversationTurn(
                role="tool",
                content=content,
                timestamp=datetime.now()
            )
        )
        await self._save_to_disk()

    def get_messages(self) -> List[Dict[str, str]]:
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self.conversation_history
        ]

    def get_last_n_messages(self, n: int = 10) -> List[Dict[str, str]]:
        recent = self.conversation_history[-n:]
        return [
            {"role": turn.role, "content": turn.content}
            for turn in recent
        ]

    async def add(self, item: MemoryItem) -> str:
        await self._ensure_loaded()
        role = item.metadata.get("role", "user")
        self.conversation_history.append(
            ConversationTurn(role=role, content=item.content)
        )
        await self._save_to_disk()
        return str(len(self.conversation_history) - 1)

    async def get(self, id: str) -> Optional[MemoryItem]:
        await self._ensure_loaded()
        try:
            index = int(id)
            if 0 <= index < len(self.conversation_history):
                turn = self.conversation_history[index]
                return MemoryItem(
                    content=turn.content,
                    metadata={"role": turn.role},
                    timestamp=turn.timestamp
                )
        except ValueError:
            pass
        return None

    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        await self._ensure_loaded()
        results = []
        query_lower = query.lower()
        for turn in reversed(self.conversation_history):
            if query_lower in turn.content.lower():
                results.append(MemoryItem(
                    content=turn.content,
                    metadata={"role": turn.role},
                    timestamp=turn.timestamp
                ))
                if len(results) >= limit:
                    break
        return results

    async def clear(self) -> None:
        self.conversation_history = []
        file_path = self.storage_path / f"{self.session_id}.jsonl"
        if file_path.exists():
            file_path.unlink()

    async def get_all(self) -> List[MemoryItem]:
        await self._ensure_loaded()
        return [
            MemoryItem(
                content=turn.content,
                metadata={"role": turn.role},
                timestamp=turn.timestamp
            )
            for turn in self.conversation_history
        ]
