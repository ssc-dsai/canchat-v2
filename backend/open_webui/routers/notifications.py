from fastapi import APIRouter
import logging

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["NOTIFICATIONS"])

router = APIRouter()


@router.get("/gc_notify/callback")
async def get_gc_notify_callback():
    pass


@router.post("/gc_notify/callback")
async def post_gc_notify_callback():
    pass
