"""
Long-term Memory - Vector-based persistent memory
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import aiofiles

from .base import BaseMemory, MemoryItem


class LongTermMemory(BaseMemory):
    def __init__(
        self,
        db_path: Path,
        collection_name: str = "agent_memory",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self._collection = None
        self._embedding_function = None
        self._memory_file = db_path / "memory_store.json"
        self._memories: Dict[str, MemoryItem] = {}

    async def _initialize(self):
        if self._collection is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            self.db_path.mkdir(parents=True, exist_ok=True)

            client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False)
            )

            self._collection = client.get_or_create_collection(
                name=self.collection_name
            )

            self._embedding_function = SentenceTransformer(self.embedding_model)

        except ImportError:
            pass

        await self._load_memories()

    async def _load_memories(self):
        if self._memory_file.exists():
            async with aiofiles.open(self._memory_file, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                for id, item_data in data.items():
                    self._memories[id] = MemoryItem.from_dict(item_data)

    async def _save_memories(self):
        self.db_path.mkdir(parents=True, exist_ok=True)
        data = {id: item.to_dict() for id, item in self._memories.items()}
        async with aiofiles.open(self._memory_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

    def _generate_embedding(self, text: str) -> List[float]:
        if self._embedding_function:
            return self._embedding_function.encode(text).tolist()
        return []

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

    async def add(
        self,
        item: MemoryItem,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        await self._initialize()

        memory_id = self._generate_id()
        item.metadata.update(metadata or {})
        item.metadata["created_at"] = datetime.now().isoformat()

        if self._collection is not None:
            embedding = self._generate_embedding(item.content)
            if embedding:
                self._collection.add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[item.content],
                    metadatas=[item.metadata]
                )
            item.embedding = embedding

        self._memories[memory_id] = item
        await self._save_memories()

        return memory_id

    async def get(self, id: str) -> Optional[MemoryItem]:
        await self._initialize()
        return self._memories.get(id)

    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        await self._initialize()

        results = []

        if self._collection is not None:
            query_embedding = self._generate_embedding(query)
            if query_embedding:
                search_results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit
                )

                if search_results["ids"] and search_results["ids"][0]:
                    for i, doc_id in enumerate(search_results["ids"][0]):
                        if doc_id in self._memories:
                            results.append(self._memories[doc_id])
                        else:
                            results.append(MemoryItem(
                                content=search_results["documents"][0][i],
                                metadata=search_results["metadatas"][0][i] if search_results["metadatas"] else {}
                            ))

        if not results:
            query_lower = query.lower()
            for item in self._memories.values():
                if query_lower in item.content.lower():
                    results.append(item)
                    if len(results) >= limit:
                        break

        return results[:limit]

    async def clear(self) -> None:
        await self._initialize()

        if self._collection is not None:
            if self._memories:
                self._collection.delete(ids=list(self._memories.keys()))

        self._memories.clear()
        await self._save_memories()

    async def get_all(self) -> List[MemoryItem]:
        await self._initialize()
        return list(self._memories.values())

    async def delete(self, memory_id: str) -> bool:
        await self._initialize()

        if memory_id not in self._memories:
            return False

        if self._collection is not None:
            self._collection.delete(ids=[memory_id])

        del self._memories[memory_id]
        await self._save_memories()
        return True

    async def update(self, memory_id: str, content: str) -> bool:
        await self._initialize()

        if memory_id not in self._memories:
            return False

        old_item = self._memories[memory_id]
        new_item = MemoryItem(
            content=content,
            metadata=old_item.metadata,
            timestamp=datetime.now()
        )

        if self._collection is not None:
            embedding = self._generate_embedding(content)
            if embedding:
                self._collection.update(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[new_item.metadata]
                )
            new_item.embedding = embedding

        self._memories[memory_id] = new_item
        await self._save_memories()
        return True
