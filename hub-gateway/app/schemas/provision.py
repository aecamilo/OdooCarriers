from typing import Optional

from pydantic import BaseModel


class ProvisionRequest(BaseModel):
    iap_account_token: str
    contact_email: Optional[str] = None
    plan_code: Optional[str] = "free"
