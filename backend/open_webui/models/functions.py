import logging
import time

from open_webui.internal.db import JSONField, get_async_db
from open_webui.models.base import Base
from open_webui.models.users import Users
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, delete, select, String, Text, update
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Functions DB Schema
####################


class FunctionMeta(BaseModel):
    description: str | None = None
    manifest: dict | None = {}


class Function(Base):
    __tablename__ = "function"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[FunctionMeta] = mapped_column(JSONField)
    valves: Mapped[dict] = mapped_column(JSONField)
    is_active: Mapped[bool] = mapped_column(Boolean)
    is_global: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)


class FunctionModel(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    content: str
    meta: FunctionMeta
    valves: dict
    is_active: bool = False
    is_global: bool = False
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FunctionResponse(BaseModel):
    id: str
    user_id: str
    type: str
    name: str
    meta: FunctionMeta
    is_active: bool
    is_global: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class FunctionForm(BaseModel):
    id: str
    name: str
    content: str
    meta: FunctionMeta


class FunctionValves(BaseModel):
    valves: dict | None = None


class FunctionsTable:
    async def insert_new_function(
        self, user_id: str, type: str, form_data: FunctionForm
    ) -> FunctionModel | None:
        function = FunctionModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "type": type,
                "updated_at": int(time.time()),
                "created_at": int(time.time()),
            }
        )

        try:
            async with get_async_db() as db:
                result = Function(**function.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FunctionModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            print(f"Error creating tool: {e}")
            return None

    async def get_function_by_id(self, id: str) -> FunctionModel | None:
        try:
            async with get_async_db() as db:
                if function := await db.get(Function, id):
                    return FunctionModel.model_validate(function)
                return None
        except Exception:
            return None

    async def get_functions(self, active_only: bool = False) -> list[FunctionModel]:
        async with get_async_db() as db:
            functions = await db.scalars(
                select(Function).where(Function.is_active == active_only)
            )
            return [
                FunctionModel.model_validate(function) for function in functions.all()
            ]

    async def get_functions_by_type(
        self, type: str, active_only: bool = False
    ) -> list[FunctionModel]:
        async with get_async_db() as db:
            functions = await db.scalars(
                select(Function).where(
                    Function.type == type, Function.is_active == active_only
                )
            )
            return [
                FunctionModel.model_validate(function) for function in functions.all()
            ]

    async def get_global_filter_functions(self) -> list[FunctionModel]:
        async with get_async_db() as db:
            functions = await db.scalars(
                select(Function).where(
                    Function.type == "filter",
                    Function.is_active == True,
                    Function.is_global == True,
                )
            )
            return [
                FunctionModel.model_validate(function) for function in functions.all()
            ]

    async def get_global_action_functions(self) -> list[FunctionModel]:
        async with get_async_db() as db:
            functions = await db.scalars(
                select(Function).where(
                    Function.type == "action",
                    Function.is_active == True,
                    Function.is_global == True,
                )
            )
            return [
                FunctionModel.model_validate(function) for function in functions.all()
            ]

    async def get_function_valves_by_id(self, id: str) -> dict | None:
        async with get_async_db() as db:
            try:
                function = await db.get(Function, id)
                return function.valves if function.valves else None
            except Exception as e:
                print(f"An error occurred: {e}")
                return None

    async def update_function_valves_by_id(
        self, id: str, valves: dict
    ) -> FunctionValves | None:
        async with get_async_db() as db:
            try:
                if function := await db.get(Function, id):
                    function.valves = valves
                    function.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(function)
                    return FunctionValves(valves=function.valves)
                return None
            except Exception:
                return None

    async def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> dict | None:
        try:
            if user := await Users.get_user_by_id(user_id):
                user_settings = user.settings.model_dump() if user.settings else {}

                # Check if user has "functions" and "valves" settings
                if "functions" not in user_settings:
                    user_settings["functions"] = {}
                if "valves" not in user_settings["functions"]:
                    user_settings["functions"]["valves"] = {}

                return user_settings["functions"]["valves"].get(id, {})
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

                # Check if user has "functions" and "valves" settings
                if "functions" not in user_settings:
                    user_settings["functions"] = {}
                if "valves" not in user_settings["functions"]:
                    user_settings["functions"]["valves"] = {}

                user_settings["functions"]["valves"][id] = valves

                # Update the user settings in the database
                _ = await Users.update_user_by_id(user_id, {"settings": user_settings})

                return user_settings["functions"]["valves"][id]
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    async def update_function_by_id(
        self, id: str, updated: dict
    ) -> FunctionModel | None:
        async with get_async_db() as db:
            try:
                if function := await db.scalar(
                    select(Function).where(Function.id == id)
                ):
                    for key, value in updated.items():
                        if hasattr(function, key):
                            setattr(function, key, value)
                        else:
                            log.error(f"{key} is not a valid attribute of Function")

                    await db.commit()
                    return FunctionModel.model_validate(function)
                return None
            except Exception:
                return None

    async def deactivate_all_functions(self) -> bool | None:
        async with get_async_db() as db:
            try:
                _ = await db.execute(
                    update(Function).values(
                        is_active=False,
                        updated_at=int(time.time()),
                    )
                )

                await db.commit()
                return True
            except Exception:
                return None

    async def delete_function_by_id(self, id: str) -> bool:
        async with get_async_db() as db:
            try:
                _ = await db.execute(delete(Function).where(Function.id == id))
                await db.commit()

                return True
            except Exception:
                return False


Functions = FunctionsTable()
