import time
import uuid

from open_webui.internal.db import get_async_db
from open_webui.models.base import Base
from open_webui.utils.access_control import has_access

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, delete, select, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

####################
# Channel DB Schema
####################


class Channel(Base):
    __tablename__ = "channel"

    id = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)

    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    access_control: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class ChannelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: str | None = None

    name: str
    description: str | None = None

    data: dict | None = None
    meta: dict | None = None
    access_control: dict | None = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class ChannelForm(BaseModel):
    name: str
    description: str | None = None
    data: dict | None = None
    meta: dict | None = None
    access_control: dict | None = None


class ChannelTable:
    async def insert_new_channel(
        self, type: str | None, form_data: ChannelForm, user_id: str
    ) -> ChannelModel | None:
        async with get_async_db() as db:
            channel = ChannelModel(
                **{
                    **form_data.model_dump(),
                    "type": type,
                    "name": form_data.name.lower(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            new_channel = Channel(**channel.model_dump())

            db.add(new_channel)
            await db.commit()
            return channel

    async def get_channels(self) -> list[ChannelModel]:
        async with get_async_db() as db:
            channels = await db.scalars(select(Channel))
            return [ChannelModel.model_validate(channel) for channel in channels.all()]

    async def get_channels_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[ChannelModel]:
        channels = await self.get_channels()
        return [
            channel
            for channel in channels
            if channel.user_id == user_id
            or await has_access(user_id, permission, channel.access_control)
        ]

    async def get_channel_by_id(self, id: str) -> ChannelModel | None:
        async with get_async_db() as db:
            channel = await db.scalar(select(Channel).where(Channel.id == id))
            return ChannelModel.model_validate(channel) if channel else None

    async def update_channel_by_id(
        self, id: str, form_data: ChannelForm
    ) -> ChannelModel | None:
        async with get_async_db() as db:
            channel = await db.scalar(select(Channel).where(Channel.id == id))
            if not channel:
                return None

            channel.name = form_data.name
            channel.data = form_data.data
            channel.meta = form_data.meta
            channel.access_control = form_data.access_control
            channel.updated_at = int(time.time())

            await db.commit()
            return ChannelModel.model_validate(channel) if channel else None

    async def delete_channel_by_id(self, id: str):
        async with get_async_db() as db:
            _ = await db.execute(delete(Channel).where(Channel.id == id))
            await db.commit()
            return True


Channels = ChannelTable()
