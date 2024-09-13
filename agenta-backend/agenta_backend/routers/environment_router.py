import logging
from typing import Optional

from fastapi.responses import JSONResponse
from fastapi import Request, HTTPException

from agenta_backend.utils import project_utils
from agenta_backend.services import db_manager, app_manager
from agenta_backend.utils.common import APIRouter, isCloudEE
from agenta_backend.models.api.api_models import DeployToEnvironmentPayload

if isCloudEE():
    from agenta_backend.commons.models.shared_models import Permission
    from agenta_backend.commons.utils.permissions import check_action_access

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@router.post("/deploy/", operation_id="deploy_to_environment")
async def deploy_to_environment(
    payload: DeployToEnvironmentPayload,
    request: Request,
    project_id: Optional[str] = None,
):
    """Deploys a given variant to an environment

    Args:
        environment_name: Name of the environment to deploy to.
        variant_id: variant id to deploy.
        stoken_session: . Defaults to Depends(verify_session()).

    Raises:
        HTTPException: If the deployment fails.
    """
    try:
        project_id = project_utils.get_project_id(
            request=request, project_id=project_id
        )
        if isCloudEE():
            has_permission = await check_action_access(
                user_uid=request.state.user_id,
                object_id=payload.variant_id,
                object_type="app_variant",
                permission=Permission.DEPLOY_APPLICATION,
            )
            logger.debug(f"User has permission deploy to environment: {has_permission}")
            if not has_permission:
                error_msg = f"You do not have permission to perform this action. Please contact your organization admin."
                logger.error(error_msg)
                return JSONResponse(
                    {"detail": error_msg},
                    status_code=403,
                )

        await db_manager.deploy_to_environment(
            environment_name=payload.environment_name,
            variant_id=payload.variant_id,
            project_id=project_id,
            user_uid=request.state.user_id,
        )

        # Update last_modified_by app information
        await app_manager.update_last_modified_by(
            user_uid=request.state.user_id,
            object_id=payload.variant_id,
            object_type="variant",
            project_id=project_id,
        )
        logger.debug("Successfully updated last_modified_by app information")
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
