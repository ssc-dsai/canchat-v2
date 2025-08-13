import time
import uuid

from open_webui.models.users import UserModel


def create_user(name: str, email: str) -> UserModel:
    return UserModel(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        domain=email.split("@")[1],
        created_at=int(time.time()),
        last_active_at=int(time.time()),
        updated_at=int(time.time()),
        profile_image_url="",
    )
