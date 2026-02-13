from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel

from open_webui.models.users import Users, UserModel
from open_webui.models.feedbacks import (
    FeedbackModel,
    FeedbackResponse,
    FeedbackForm,
    Feedbacks,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()


############################
# GetConfig
############################


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS,
        "EVALUATION_ARENA_MODELS": request.app.state.config.EVALUATION_ARENA_MODELS,
    }


############################
# UpdateConfig
############################


class UpdateConfigForm(BaseModel):
    ENABLE_EVALUATION_ARENA_MODELS: bool


@router.post("/config")
async def update_config(
    request: Request,
    form_data: UpdateConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS = (
        form_data.ENABLE_EVALUATION_ARENA_MODELS
    )
    return {
        "ENABLE_EVALUATION_ARENA_MODELS": request.app.state.config.ENABLE_EVALUATION_ARENA_MODELS,
    }


############################
# Feedbacks
############################


class FeedbackUserResponse(FeedbackResponse):
    user: UserModel | None = None


@router.get("/feedbacks/all", response_model=list[FeedbackUserResponse])
async def get_all_feedbacks(user=Depends(get_admin_user)):
    """Get all feedbacks (original behavior)"""
    feedbacks = await Feedbacks.get_all_feedbacks()
    return [
        FeedbackUserResponse(
            **feedback.model_dump(), user=await Users.get_user_by_id(feedback.user_id)
        )
        for feedback in feedbacks
    ]


# NEW PAGINATED ENDPOINT
@router.get("/feedbacks/all/paginated", response_model=list[FeedbackUserResponse])
async def get_all_feedbacks_paginated(
    user=Depends(get_admin_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search query"),
):
    """Get paginated feedbacks with optional search"""
    feedbacks = await Feedbacks.get_all_feedbacks_paginated(
        page=page, limit=limit, search=search
    )
    return [
        FeedbackUserResponse(
            **feedback.model_dump(), user=await Users.get_user_by_id(feedback.user_id)
        )
        for feedback in feedbacks
    ]


@router.get("/feedbacks/count")
async def get_feedbacks_count(
    user=Depends(get_admin_user),
    search: str | None = Query(None, description="Search query"),
):
    """Get total count of feedbacks with optional search filter"""
    return {"count": await Feedbacks.get_feedbacks_count(search=search)}


@router.get("/feedbacks/all/export", response_model=list[FeedbackUserResponse])
async def export_all_feedbacks(user=Depends(get_admin_user)):
    """Export all feedbacks for admin use"""
    feedbacks = await Feedbacks.get_all_feedbacks()
    return [
        FeedbackUserResponse(
            **feedback.model_dump(), user=await Users.get_user_by_id(feedback.user_id)
        )
        for feedback in feedbacks
    ]


@router.delete("/feedbacks/all")
async def delete_all_feedbacks(user=Depends(get_admin_user)):
    """Delete all feedbacks (admin only)"""
    success = await Feedbacks.delete_all_feedbacks()
    return success


@router.get("/feedbacks/user", response_model=list[FeedbackUserResponse])
async def get_feedbacks(user=Depends(get_verified_user)):
    feedbacks = await Feedbacks.get_feedbacks_by_user_id(user.id)
    return feedbacks


@router.delete("/feedbacks", response_model=bool)
async def delete_feedbacks(user=Depends(get_verified_user)):
    success = await Feedbacks.delete_feedbacks_by_user_id(user.id)
    return success


@router.post("/feedback", response_model=FeedbackModel)
async def create_feedback(
    request: Request,
    form_data: FeedbackForm,
    user=Depends(get_verified_user),
):
    feedback = await Feedbacks.insert_new_feedback(user_id=user.id, form_data=form_data)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return feedback


@router.get("/feedback/{id}", response_model=FeedbackModel)
async def get_feedback_by_id(id: str, user=Depends(get_verified_user)):
    feedback = await Feedbacks.get_feedback_by_id_and_user_id(id=id, user_id=user.id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.post("/feedback/{id}", response_model=FeedbackModel)
async def update_feedback_by_id(
    id: str, form_data: FeedbackForm, user=Depends(get_verified_user)
):
    feedback = await Feedbacks.update_feedback_by_id_and_user_id(
        id=id, user_id=user.id, form_data=form_data
    )

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return feedback


@router.delete("/feedback/{id}")
async def delete_feedback_by_id(id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        success = await Feedbacks.delete_feedback_by_id(id=id)
    else:
        success = await Feedbacks.delete_feedback_by_id_and_user_id(
            id=id, user_id=user.id
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return success
