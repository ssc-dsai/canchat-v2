from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
import logging
import aiohttp

from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS, VERSION, AIOHTTP_CLIENT_TIMEOUT

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["INCIDENTS"])

router = APIRouter()

############################
# CreateIncident
############################

@router.post("/create", tags=["incidents"])
async def create_incident(
    request: Request,
    email: str = Form(...),
    description: str = Form(...),
    stepsToReproduce: str = Form(...),
    files: List[UploadFile] = File(None),
    user=Depends(get_verified_user)
):
    log.info("Processing incident submission")

    WEBUI_URL = request.app.state.config.WEBUI_URL
    JIRA_API_URL = request.app.state.config.JIRA_API_URL
    JIRA_USERNAME = request.app.state.config.JIRA_USERNAME
    JIRA_API_TOKEN = request.app.state.config.JIRA_API_TOKEN
    JIRA_PROJECT_KEY = request.app.state.config.JIRA_PROJECT_KEY

    try:
        description = (
            f"Environment: {WEBUI_URL}\n"
            f"App Version: {VERSION}\n"
            f"Email: {email}\n\n"
            f"Description:\n{description}\n\n"
            f"Steps to Reproduce:\n{stepsToReproduce}"
        )

        issue_data = {
            "fields": {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": "User Incident Submission",
                "description": description,
                "issuetype": {"name": "Bug"},
            }
        }

        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            # Create the Jira issue
            async with session.post(
                f"{JIRA_API_URL.rstrip('/')}/rest/api/2/issue",
                json=issue_data,
                auth=aiohttp.BasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
                headers={"Content-Type": "application/json"},
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    log.error(f"Jira API error: {error_text}")
                    raise HTTPException(status_code=response.status, detail=error_text)

                result = await response.json()
                issue_key = result.get("key")

                if not issue_key:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="No issue key in Jira response",
                    )

                # Process file attachments
                if files:
                    attachment_url = f"{JIRA_API_URL.rstrip('/')}/rest/api/2/issue/{issue_key}/attachments"

                    for file in files:
                        try:
                            await file.seek(0)
                            content = await file.read()

                            if not content:
                                log.error(f"Empty content for file {file.filename}")
                                continue

                            jira_form = aiohttp.FormData()
                            jira_form.add_field(
                                "file",
                                content,
                                filename=file.filename,
                                content_type=file.content_type or "application/octet-stream",
                            )

                            async with session.post(
                                attachment_url,
                                data=jira_form,
                                headers={"X-Atlassian-Token": "no-check"},
                                auth=aiohttp.BasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
                            ) as attach_response:
                                if not attach_response.ok:
                                    error_text = await attach_response.text()
                                    log.error(f"Failed to attach file {file.filename}: {error_text}")
                        except Exception as e:
                            log.error(f"Error attaching file: {str(e)}")
                            continue

                log.info(f"Created Jira issue: {issue_key}")
                return {"success": True, "ticketId": issue_key}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating incident report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
