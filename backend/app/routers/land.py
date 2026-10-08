"""
routers/land.py
----------------
REST API endpoints for Land Management (Module 2).

Endpoints:
    POST   /api/v1/lands
    GET    /api/v1/lands
    GET    /api/v1/lands/{land_id}
    PUT    /api/v1/lands/{land_id}
    DELETE /api/v1/lands/{land_id}

Thin by design — all business logic lives in services/land_service.py.
This file only: parses/validates HTTP input (via Pydantic + FastAPI),
calls the service layer, and maps results/errors to HTTP responses.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams, get_pagination_params
from app.models.user import User
from app.schemas.land import LandCreate, LandListResponse, LandResponse, LandUpdate
from app.services import land_service
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lands", tags=["Land Management"])


@router.post(
    "",
    response_model=LandResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new land record",
)
async def create_land(
    payload: LandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LandResponse:
    """Creates a new land/plot entry, owned by the logged-in user."""
    try:
        land = await land_service.create_land(db, payload, user_id=current_user.id)
        return LandResponse.model_validate(land)
    except Exception as exc:
        logger.error("Error creating land record: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Land creation failed: {type(exc).__name__} - {str(exc)}"
        ) from exc


@router.get(
    "",
    response_model=LandListResponse,
    status_code=status.HTTP_200_OK,
    summary="List the current user's land records (paginated)",
)
async def list_lands(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LandListResponse:
    """Returns a paginated list of the logged-in user's lands, most recently created first."""
    lands, total = await land_service.list_lands(
        db, skip=pagination.skip, limit=pagination.limit, user_id=current_user.id
    )
    return LandListResponse(
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        items=[LandResponse.model_validate(land) for land in lands],
    )


@router.get(
    "/{land_id}",
    response_model=LandResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single land record by id",
)
async def get_land(
    land_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LandResponse:
    """Fetches one land record. Returns 404 if it doesn't exist. Requires login."""
    try:
        land = await land_service.get_land(db, land_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LandResponse.model_validate(land)


@router.put(
    "/{land_id}",
    response_model=LandResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a land record (partial update)",
)
async def update_land(
    land_id: uuid.UUID,
    payload: LandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LandResponse:
    """
    Updates only the fields provided in the request body.
    Returns 404 if the land doesn't exist, 422 if the payload is invalid.
    """
    try:
        land = await land_service.update_land(db, land_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LandResponse.model_validate(land)


@router.delete(
    "/{land_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a land record",
)
async def delete_land(
    land_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deletes a land record. Returns 404 if it doesn't exist."""
    try:
        await land_service.delete_land(db, land_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    # 204 No Content — no response body returned
