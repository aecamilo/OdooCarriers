from typing import Any, Optional

from pydantic import BaseModel, Field


class Party(BaseModel):
    country_code: str = ""
    postal_code: str = ""
    city: str = ""
    street: str = ""
    contact_phone: str = ""
    contact_email: Optional[str] = None
    name: Optional[str] = None
    company_name: Optional[str] = None


class Parcel(BaseModel):
    weight_kg: float = Field(gt=0)


class LabelRequest(BaseModel):
    schema_version: str
    operation: str
    idempotency_key: Optional[str] = None
    carrier_code: str = ""
    service_level: str = "standard"
    reference: str = ""
    shipper: Optional[Party] = None
    recipient: Optional[Party] = None
    parcels: list[Parcel] = Field(default_factory=list)
    carrier_auth: Optional[dict[str, Any]] = None
