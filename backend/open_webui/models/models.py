import logging
import time

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db_utils import AsyncDatabaseConnector, JSONField
from open_webui.models.base import Base
from open_webui.models.users import UserResponse, UsersTable
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Boolean, Text, delete, select, update
from sqlalchemy.orm import Mapped, mapped_column

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Models DB Schema
####################


# ModelParams is a model for the data stored in the params field of the Model table
class ModelParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    pass


# ModelMeta is a model for the data stored in the meta field of the Model table
class ModelMeta(BaseModel):
    profile_image_url: str | None = "/static/favicon.png"

    description: str | None = None
    """
        User-facing description of the model.
    """

    capabilities: dict | None = None

    model_config = ConfigDict(extra="allow")

    pass


class Model(Base):
    __tablename__ = "model"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    """
        The model's id as used in the API. If set to an existing model, it will override the model.
    """
    user_id: Mapped[str] = mapped_column(Text)

    base_model_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    """
        An optional pointer to the actual model that should be used when proxying requests.
    """

    name: Mapped[str] = mapped_column(Text)
    """
        The human-readable display name of the model.
    """

    params: Mapped[ModelParams] = mapped_column(JSONField)
    """
        Holds a JSON encoded blob of parameters, see `ModelParams`.
    """

    meta: Mapped[ModelMeta] = mapped_column(JSONField)
    """
        Holds a JSON encoded blob of metadata, see `ModelMeta`.
    """

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

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_at: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)


class ModelModel(BaseModel):
    id: str
    user_id: str
    base_model_id: str | None = None

    name: str
    params: ModelParams
    meta: ModelMeta

    access_control: dict | None = None

    is_active: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ModelUserResponse(ModelModel):
    user: UserResponse | None = None


class ModelResponse(ModelModel):
    pass


class ModelForm(BaseModel):
    id: str
    base_model_id: str | None = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_control: dict | None = None
    is_active: bool = True


class ModelsTable:

    __db: AsyncDatabaseConnector
    __users: UsersTable

    def __init__(
        self, db_connector: AsyncDatabaseConnector, users_table: UsersTable
    ) -> None:
        self.__db = db_connector
        self.__users = users_table

    async def insert_new_model(
        self, form_data: ModelForm, user_id: str
    ) -> ModelModel | None:
        model = ModelModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        try:
            async with self.__db.get_async_db() as db:
                result = Model(**model.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)

                if result:
                    return ModelModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            print(e)
            return None

    async def get_all_models(self) -> list[ModelModel]:
        async with self.__db.get_async_db() as db:
            models = await db.scalars(select(Model))
            return [ModelModel.model_validate(model) for model in models.all()]

    async def get_models(self) -> list[ModelUserResponse]:
        async with self.__db.get_async_db() as db:
            models: list[ModelUserResponse] = []
            for model in (
                await db.scalars(select(Model).where(Model.base_model_id != None))
            ).all():
                user = await self.__users.get_user_by_id(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **ModelModel.model_validate(model).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return models

    async def get_base_models(self) -> list[ModelModel]:
        async with self.__db.get_async_db() as db:
            models = await db.scalars(select(Model).filter(Model.base_model_id == None))
            return [ModelModel.model_validate(model) for model in models.all()]

    async def get_models_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[ModelUserResponse]:
        from open_webui.utils.access_control import has_access

        models = await self.get_models()
        return [
            model
            for model in models
            if model.user_id == user_id
            or await has_access(user_id, permission, model.access_control)
        ]

    async def get_model_by_id(self, id: str) -> ModelModel | None:
        try:
            async with self.__db.get_async_db() as db:
                model = await db.get(Model, id)
                return ModelModel.model_validate(model)
        except Exception:
            return None

    async def toggle_model_by_id(self, id: str) -> ModelModel | None:
        async with self.__db.get_async_db() as db:
            try:
                if model := await db.scalar(select(Model).where(Model.id == id)):
                    model.is_active = not model.is_active
                    model.updated_at = int(time.time())

                    await db.commit()
                    await db.refresh(model)
                    return ModelModel.model_validate(model)
                return None
            except Exception:
                return None

    async def update_model_by_id(
        self, id: str, model_form: ModelForm
    ) -> ModelModel | None:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(
                    update(Model)
                    .where(Model.id == id)
                    .values(model_form.model_dump(exclude={"id"}))
                )
                await db.commit()

                model = await db.get(Model, id)
                await db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            print(e)

            return None

    async def delete_model_by_id(self, id: str) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(delete(Model).where(Model.id == id))
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_all_models(self) -> bool:
        try:
            async with self.__db.get_async_db() as db:
                _ = await db.execute(delete(Model))
                await db.commit()

                return True
        except Exception:
            return False
