from open_webui.constants import ERROR_MESSAGES
from open_webui.models.users import Users
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
# GetTotalUsers
############################

@router.get("/users")
async def get_total_users(user=Depends(get_verified_user)):
    if user.role == "admin":
        total_users = Users.get_num_users()
        return {"total_users": total_users}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# GetTotalUsersByDomain
############################

@router.get("/users/{domain}")
async def get_total_users_by_domain(domain: str, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain parameter is required.",
        )

    total_users = Users.get_num_users_by_domain(domain)
    return {"total_users": total_users}

############################
# GetDomains
############################

@router.get("/domains")
async def get_total_users_by_domain(user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    domains = Users.get_user_domains()

    if not domains:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No domains found.",
        )
    
    return {"domains": domains}

############################
# GetDailyUsers
############################

@router.get("/daily/users")
async def get_daily_active_users_number(user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    daily_active_users = Users.get_daily_active_users_number()
    if not daily_active_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active users found.",
        )
    
    return {"daily_active_users": daily_active_users}

############################
# GetDailyUsersByDomain
############################

@router.get("/daily/users/{domain}")
async def get_daily_active_users_number_by_domain(domain: str, user=Depends(get_verified_user)):
    if not user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain parameter is required.",
        )

    daily_active_users = Users.get_daily_active_users_number_by_domain()
    
    if not daily_active_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active users found.",
        )
    
    return {"daily_active_users": daily_active_users}