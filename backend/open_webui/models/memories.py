import time
import uuid

from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.base import Base
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, delete, select, String, Text
from sqlalchemy.orm import Mapped, mapped_column

####################
# Memory DB Schema
####################


class Memory(Base):
    __tablename__ = "memory"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)


class MemoryModel(BaseModel):
    id: str
    user_id: str
    content: str
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class MemoriesTable:
    __db: AsyncDatabaseConnector

    def __init__(self, db_connector: AsyncDatabaseConnector) -> None:
        self.__db = db_connector

    async def insert_new_memory(
        self,
        user_id: str,
        content: str,
    ) -> MemoryModel | None:
        async with self.__db.get_async_db() as db:
            id = str(uuid.uuid4())

            memory = MemoryModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "content": content,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = Memory(**memory.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            if result:
                return MemoryModel.model_validate(result)
            else:
                return None

    async def update_memory_by_id(
        self,
        id: str,
        content: str,
    ) -> MemoryModel | None:
        async with self.__db.get_async_db() as db:
            try:
                if memory := await db.scalar(select(Memory).where(Memory.id == id)):
                    memory.content = content
                    memory.updated_at = int(time.time())

                    await db.commit()
                    await db.refresh(memory)
                return MemoryModel.model_validate(memory) if memory else None
            except Exception:
                return None

    async def get_memories(self) -> list[MemoryModel]:
        async with self.__db.get_async_db() as db:
            try:
                memories = await db.scalars(select(Memory))
                return [MemoryModel.model_validate(memory) for memory in memories.all()]
            except Exception:
                return []

    async def get_memories_by_user_id(self, user_id: str) -> list[MemoryModel]:
        async with self.__db.get_async_db() as db:
            try:
                memories = await db.scalars(
                    select(Memory).where(Memory.user_id == user_id)
                )
                return [MemoryModel.model_validate(memory) for memory in memories.all()]
            except Exception:
                return []

    async def get_memory_by_id(self, id: str) -> MemoryModel | None:
        async with self.__db.get_async_db() as db:
            try:
                memory = await db.get(Memory, id)
                return MemoryModel.model_validate(memory)
            except Exception:
                return None

    async def delete_memory_by_id(self, id: str) -> bool:
        async with self.__db.get_async_db() as db:
            try:
                _ = db.execute(delete(Memory).where(Memory.id == id))
                await db.commit()

                return True
            except Exception:
                return False

    async def delete_memories_by_user_id(self, user_id: str) -> bool:
        async with self.__db.get_async_db() as db:
            try:
                _ = db.execute(delete(Memory).where(Memory.user_id == user_id))
                await db.commit()

                return True
            except Exception:
                return False

    async def delete_memory_by_id_and_user_id(self, id: str, user_id: str) -> bool:
        async with self.__db.get_async_db() as db:
            try:
                _ = db.execute(
                    delete(Memory).where(Memory.id == id, Memory.user_id == user_id)
                )
                await db.commit()

                return True
            except Exception:
                return False
