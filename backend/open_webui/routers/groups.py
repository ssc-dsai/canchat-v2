from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.models.db_services import GROUPS, USERS
from open_webui.models.groups import (
    GroupForm,
    GroupResponse,
    GroupUpdateForm,
)
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()


############################
# GetFunctions
############################


@router.get("/", response_model=list[GroupResponse])
async def get_groups(user=Depends(get_verified_user)):
    if user.role == "admin":
        return await GROUPS.get_groups()
    else:
        return await GROUPS.get_groups_by_member_id(user.id)


############################
# CreateNewGroup
############################


@router.post("/create", response_model=GroupResponse | None)
async def create_new_function(form_data: GroupForm, user=Depends(get_admin_user)):
    try:
        group = await GROUPS.insert_new_group(user.id, form_data)
        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error creating group"),
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# GetGroupById
############################


@router.get("/id/{id}", response_model=GroupResponse | None)
async def get_group_by_id(id: str, user=Depends(get_admin_user)):
    group = await GROUPS.get_group_by_id(id)
    if group:
        return group
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateGroupById
############################


@router.post("/id/{id}/update", response_model=GroupResponse | None)
async def update_group_by_id(
    id: str, form_data: GroupUpdateForm, user=Depends(get_admin_user)
):
    try:
        if form_data.user_ids:
            form_data.user_ids = await USERS.get_valid_user_ids(form_data.user_ids)

        # Get the current group state before update to compare domain changes
        current_group = await GROUPS.get_group_by_id(id)

        # Update the group
        group = await GROUPS.update_group_by_id(id, form_data)

        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating group"),
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# GetAvailableDomains
############################


@router.get("/domains", response_model=list[str])
async def get_available_domains(user=Depends(get_admin_user)):
    """Get all unique domains from existing users in the database"""
    try:
        domains = await USERS.get_user_domains()
        return sorted(domains)  # Return sorted list of domains
    except Exception as e:
        print(f"Error getting domains: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error retrieving domains"),
        )


############################
# DeleteGroupById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_group_by_id(id: str, user=Depends(get_admin_user)):
    try:

        if result := await GROUPS.delete_group_by_id(id):
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting group"),
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
