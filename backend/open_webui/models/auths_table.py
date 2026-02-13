import logging
import uuid
from typing import Optional

from sqlalchemy import delete, select, update

from open_webui.internal.db import get_async_db
from open_webui.models.auths import Auth, AuthModel
from open_webui.models.users import UserModel, Users
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import verify_password

"""
The Auths service which provides the ability to interact with the DB.

Note: This service does not follow the pattern of being within the file
      of the Auth model due to causing circular dependency issues.
      This issue is due to the fact that the Auth model is instantiated via
      the model itself through SQLAlchemy whereas other tables use migration
      scripts.
"""

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class AuthsTable:
    async def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
        domain: str = "*",
    ) -> Optional[UserModel]:
        async with get_async_db() as db:

            log.info("insert_new_auth")

            id = str(uuid.uuid4())

            auth = AuthModel(
                **{
                    "id": id,
                    "email": email,
                    "password": password,
                    "active": True,
                }
            )
            result = Auth(**auth.model_dump())
            db.add(result)

            user = await Users.insert_new_user(
                id,
                name,
                email,
                profile_image_url,
                role,
                oauth_sub,
                domain,
            )

            await db.commit()
            await db.refresh(result)

            if result and user:
                return user
            else:
                return None

    async def authenticate_user(self, email: str, password: str) -> Optional[UserModel]:
        log.info(f"authenticate_user: {email}")
        try:
            async with get_async_db() as db:

                result = await db.execute(
                    select(Auth).where(Auth.email == email, Auth.active)
                )

                auth = result.scalars().first()
                if auth:
                    if verify_password(password, auth.password):
                        user = await Users.get_user_by_id(auth.id)
                        return user
                    else:
                        return None
                else:
                    return None
        except Exception:
            return None

    async def authenticate_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_api_key: {api_key}")
        # if no api_key, return None
        if not api_key:
            return None

        try:
            user = await Users.get_user_by_api_key(api_key)
            return user if user else None
        except Exception:
            return None

    async def authenticate_user_by_trusted_header(
        self, email: str
    ) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_trusted_header: {email}")
        try:
            async with get_async_db() as db:
                auth = await db.scalar(
                    select(Auth).where(Auth.email == email, Auth.active == True)
                )

                if auth:
                    user = await Users.get_user_by_id(auth.id)
                    return user
        except Exception:
            return None

    async def update_user_password_by_id(self, id: str, new_password: str) -> bool:
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    update(Auth).where(Auth.id == id).values(password=new_password)
                )
                await db.commit()
                return True if result.scalar_one() == 1 else False
        except Exception:
            return False

    async def update_email_by_id(self, id: str, email: str) -> bool:
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    update(Auth).where(Auth.id == id).values(email=email)
                )
                await db.commit()
                return True if result.scalar_one() == 1 else False
        except Exception:
            return False

    async def delete_auth_by_user_id(self, user_id: str) -> bool:
        try:
            async with get_async_db() as db:
                user = await Users.get_user_by_id(user_id)

                if user:
                    _ = await db.execute(delete(Auth).where(Auth.email == user.email))
                    await db.commit()
                    _ = await Users.delete_user_by_id(user_id)
                    return True
                else:
                    return False
        except Exception:
            return False


Auths = AuthsTable()
