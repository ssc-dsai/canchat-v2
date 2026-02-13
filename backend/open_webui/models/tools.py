import logging
import time

from open_webui.internal.db import JSONField, get_async_db
from open_webui.models.base import Base
from open_webui.models.users import Users, UserResponse
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    delete,
    select,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Tools DB Schema
####################


class ToolMeta(BaseModel):
    description: str | None = None
    manifest: dict | None = {}


class Tool(Base):
    __tablename__ = "tool"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    specs: Mapped[list[dict]] = mapped_column(JSONField)
    meta: Mapped[ToolMeta] = mapped_column(JSONField)
    valves = mapped_column(JSONField)

    access_control: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    updated_at: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)


class ToolModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    specs: list[dict]
    meta: ToolMeta
    access_control: dict | None = None

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ToolUserModel(ToolModel):
    user: UserResponse | None = None


class ToolResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: ToolMeta
    access_control: dict | None = None
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ToolUserResponse(ToolResponse):
    user: UserResponse | None = None


class ToolForm(BaseModel):
    id: str
    name: str
    content: str
    meta: ToolMeta
    access_control: dict | None = None


class ToolValves(BaseModel):
    valves: dict | None = None


class ToolsTable:
    async def insert_new_tool(
        self, user_id: str, form_data: ToolForm, specs: list[dict]
    ) -> ToolModel | None:
        async with get_async_db() as db:
            tool = ToolModel(
                **{
                    **form_data.model_dump(),
                    "specs": specs,
                    "user_id": user_id,
                    "updated_at": int(time.time()),
                    "created_at": int(time.time()),
                }
            )

            try:
                result = Tool(**tool.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return ToolModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(f"Error creating tool: {e}")
                return None

    async def get_tool_by_id(self, id: str) -> ToolModel | None:
        try:
            async with get_async_db() as db:
                tool = await db.get(Tool, id)
                return ToolModel.model_validate(tool)
        except Exception:
            return None

    async def get_tools(self) -> list[ToolUserModel]:
        async with get_async_db() as db:
            tools: list[ToolUserModel] = []

            # Import User model to do the join
            from open_webui.models.users import User

            query = (
                select(Tool, User)
                .join(User, Tool.user_id == User.id, isouter=True)
                .order_by(Tool.updated_at.desc())
            )

            result = await db.execute(query)

            for tool, user in result.all():
                tools.append(
                    ToolUserModel.model_validate(
                        {
                            **ToolModel.model_validate(tool).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return tools

    async def get_tools_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[ToolUserModel]:
        async with get_async_db() as db:
            tools: list[ToolUserModel] = []

            # Import User model to do the join
            from open_webui.models.users import User, UserModel

            query = (
                select(Tool, User)
                .join(User, Tool.user_id == User.id, isouter=True)
                .where(Tool.user_id == user_id)
                .order_by(Tool.updated_at.desc())
            )

            result = await db.execute(query)

            for tool, user in result.all():
                if await has_access(user_id, permission, tool.access_control):
                    tools.append(
                        ToolUserModel.model_validate(
                            {
                                **ToolModel.model_validate(tool).model_dump(),
                                "user": (
                                    UserModel.model_validate(user).model_dump()
                                    if user
                                    else None
                                ),
                            }
                        )
                    )
            return tools

    async def get_tool_valves_by_id(self, id: str) -> dict | None:
        try:
            async with get_async_db() as db:
                tool = await db.get(Tool, id)
                return tool.valves if tool.valves else {}
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    async def update_tool_valves_by_id(
        self, id: str, valves: dict
    ) -> ToolValves | None:
        try:
            async with get_async_db() as db:
                if tool := await db.get(Tool, id):
                    tool.valves = valves
                    await db.commit()
                    await db.refresh(tool)
                    return ToolValves(valves=tool.valves)
                return None
        except Exception:
            return None

    async def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> dict | None:
        try:
            if user := await Users.get_user_by_id(user_id):
                user_settings = user.settings.model_dump() if user.settings else {}

                # Check if user has "tools" and "valves" settings
                if "tools" not in user_settings:
                    user_settings["tools"] = {}
                if "valves" not in user_settings["tools"]:
                    user_settings["tools"]["valves"] = {}

                return user_settings["tools"]["valves"].get(id, {})
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    async def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict
    ) -> dict | None:
        try:
            if user := await Users.get_user_by_id(user_id):
                user_settings = user.settings.model_dump() if user.settings else {}

                # Check if user has "tools" and "valves" settings
                if "tools" not in user_settings:
                    user_settings["tools"] = {}
                if "valves" not in user_settings["tools"]:
                    user_settings["tools"]["valves"] = {}

                user_settings["tools"]["valves"][id] = valves

                # Update the user settings in the database
                updated_user = await Users.update_user_by_id(
                    user_id, {"settings": user_settings}
                )

                return (
                    updated_user.settings["tools"]["valves"][id]
                    if updated_user
                    else None
                )
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    async def update_tool_by_id(self, id: str, updated: dict) -> ToolModel | None:
        try:
            async with get_async_db() as db:
                if tool := await db.get(Tool, id):
                    for key, value in updated.items():
                        if hasattr(tool, key):
                            setattr(tool, key, value)
                        else:
                            log.error(f"{key} is not a valid attribute of Tool")

                    tool.updated_at = int(time.time())

                    await db.commit()
                    await db.refresh(tool)
                    return ToolModel.model_validate(tool)
                return None
        except Exception:
            return None

    async def delete_tool_by_id(self, id: str) -> bool:
        try:
            async with get_async_db() as db:
                _ = await db.execute(delete(Tool).where(Tool.id == id))
                await db.commit()

                return True
        except Exception:
            return False


Tools = ToolsTable()
