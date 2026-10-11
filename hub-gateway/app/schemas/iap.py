from typing import Any, Optional

from pydantic import BaseModel


class IapJsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any]
    id: Optional[int | str] = None


class IapChargeParams(BaseModel):
    account_token: str
    credit: float = 1.0
    dbuuid: Optional[str] = None
    description: Optional[str] = None
    transaction_id: Optional[str] = None
