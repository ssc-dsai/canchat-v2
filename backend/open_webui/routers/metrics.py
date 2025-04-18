from open_webui.constants import ERROR_MESSAGES
from open_webui.models.users import Users
from open_webui.models.message_metrics import MessageMetrics
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
import logging

from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["METRICS"])

router = APIRouter()

############################
# GetDomains
############################


@router.get("/domains")
async def get_total_users_by_domain(user=Depends(get_verified_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    domains = Users.get_user_domains() or []
    return {"domains": domains}


############################
# GetTotalUsers
############################


@router.get("/users")
async def get_total_users(domain: str = None, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    total_users = Users.get_num_users(domain) if domain else Users.get_num_users()
    return {"total_users": total_users}


############################
# GetDailyUsers
############################


@router.get("/daily/users")
async def get_daily_users_number(domain: str = None, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    total_daily_users = (
        Users.get_daily_users_number(domain=domain)
        if domain
        else Users.get_daily_users_number()
    )
    return {"total_daily_users": total_daily_users}


############################
# GetTotalPrompts
############################


@router.get("/prompts")
async def get_total_prompts(domain: str = None, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    total_prompts = (
        MessageMetrics.get_messages_number(domain)
        if domain
        else MessageMetrics.get_messages_number()
    )

    if not total_prompts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No prompts found.",
        )

    return {"total_prompts": total_prompts}


############################
# GetDailyUsers
############################


@router.get("/daily/prompts")
async def get_daily_prompts_number(domain: str = None, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    total_daily_prompts = (
        MessageMetrics.get_daily_messages_number(domain=domain)
        if domain
        else MessageMetrics.get_daily_messages_number()
    )
    return {"total_daily_prompts": total_daily_prompts}


############################
# GetTotalTokens
############################


@router.get("/tokens")
async def get_total_tokens(domain: str = None, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    total_tokens = (
        MessageMetrics.get_message_tokens_sum(domain)
        if domain
        else MessageMetrics.get_message_tokens_sum()
    )

    return {"total_tokens": total_tokens}


############################
# GetDailyTokens
############################


@router.get("/daily/tokens")
async def get_daily_tokens(domain: str = None, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    total_daily_tokens = (
        MessageMetrics.get_daily_message_tokens_sum(domain=domain)
        if domain
        else MessageMetrics.get_daily_message_tokens_sum()
    )
    return {"total_daily_tokens": total_daily_tokens}
