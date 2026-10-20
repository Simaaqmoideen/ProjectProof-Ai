import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecruiterProfileRequest(BaseModel):
    full_name: str
    organization: str


class RecruiterProfileResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    organization: str
    work_email_domain: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
