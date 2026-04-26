from pydantic import BaseModel, Field
from typing import Optional


class TelnyxOutboundCallSchema(BaseModel):
    to: str = Field(description="The phone number or SIP endpoint to call.")
    from_: str = Field(alias="from", description="The phone number or caller ID to show.")
    wss_url: Optional[str] = None
