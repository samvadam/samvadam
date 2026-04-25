from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class TwilioCallSchema(BaseModel):
    # Required Fields
    to: str = Field(description="The phone number or SIP endpoint to call.")
    from_: str = Field(alias="from", description="The phone number or caller ID to show.")

    # URL/Routing Fields
    url: Optional[str] = None
    twiml: Optional[str] = None
    application_sid: Optional[str] = None
    method: Optional[str] = "POST"

    # Fallbacks and Callbacks
    fallback_url: Optional[str] = None
    fallback_method: Optional[str] = None
    status_callback: Optional[str] = None
    status_callback_event: Optional[List[str]] = None
    status_callback_method: Optional[str] = None

    # Recording Settings
    record: Optional[bool] = False
    recording_channels: Optional[str] = None
    recording_status_callback: Optional[str] = None
    recording_status_callback_method: Optional[str] = None
    recording_status_callback_event: Optional[List[str]] = None
    recording_track: Optional[str] = None
    trim: Optional[str] = None

    # Machine Detection (AMD)
    machine_detection: Optional[str] = None
    machine_detection_timeout: Optional[int] = None
    machine_detection_speech_threshold: Optional[int] = None
    machine_detection_speech_end_threshold: Optional[int] = None
    machine_detection_silence_timeout: Optional[int] = None
    async_amd: Optional[str] = None
    async_amd_status_callback: Optional[str] = None
    async_amd_status_callback_method: Optional[str] = None

    # Advanced Telephony
    send_digits: Optional[str] = None
    timeout: Optional[int] = None
    sip_auth_username: Optional[str] = None
    sip_auth_password: Optional[str] = None
    caller_id: Optional[str] = None
    byoc: Optional[str] = None
    call_reason: Optional[str] = None
    call_token: Optional[str] = None
    time_limit: Optional[int] = None
    client_notification_url: Optional[str] = None

    class Config:
        populate_by_name = True


class TOutboundCallRequestSchema(TwilioCallSchema):
    pass


class TwilioCallWebhook(BaseModel):
    # Core Identifiers
    call_sid: str = Field(alias="CallSid")
    account_sid: str = Field(alias="AccountSid")

    # Numbers
    from_number: str = Field(alias="From")
    to_number: str = Field(alias="To")
    call_status: str = Field(alias="CallStatus")

    # Optional - not always present
    timestamp: Optional[str] = Field(alias="Timestamp", default=None)
    sequence_number: Optional[str] = Field(alias="SequenceNumber", default=None)
    direction: Optional[str] = Field(alias="Direction", default=None)
    duration: Optional[str] = Field(alias="Duration", default=None)
    call_duration: Optional[str] = Field(alias="CallDuration", default=None)

    # Called/Caller info
    called: Optional[str] = Field(alias="Called", default=None)
    caller: Optional[str] = Field(alias="Caller", default=None)
    caller_country: Optional[str] = Field(alias="CallerCountry", default=None)
    caller_state: Optional[str] = Field(alias="CallerState", default=None)
    caller_city: Optional[str] = Field(alias="CallerCity", default=None)
    caller_zip: Optional[str] = Field(alias="CallerZip", default=None)

    # To info
    to_country: Optional[str] = Field(alias="ToCountry", default=None)
    to_state: Optional[str] = Field(alias="ToState", default=None)
    to_city: Optional[str] = Field(alias="ToCity", default=None)
    to_zip: Optional[str] = Field(alias="ToZip", default=None)

    # From info
    from_country: Optional[str] = Field(alias="FromCountry", default=None)
    from_state: Optional[str] = Field(alias="FromState", default=None)
    from_city: Optional[str] = Field(alias="FromCity", default=None)
    from_zip: Optional[str] = Field(alias="FromZip", default=None)

    # Called (destination) info
    called_country: Optional[str] = Field(alias="CalledCountry", default=None)
    called_state: Optional[str] = Field(alias="CalledState", default=None)
    called_city: Optional[str] = Field(alias="CalledCity", default=None)
    called_zip: Optional[str] = Field(alias="CalledZip", default=None)

    # Misc
    api_version: Optional[str] = Field(alias="ApiVersion", default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"  # safely ignores any future Twilio fields
    )


class TwilioCallStatusWebhook(BaseModel):
    # Core Identifiers
    call_sid: str = Field(alias="CallSid")
    account_sid: str = Field(alias="AccountSid")
    api_version: str = Field(alias="ApiVersion")

    # Numbers and Direction
    from_number: str = Field(alias="From")
    to_number: str = Field(alias="To")
    direction: str = Field(alias="Direction")
    caller: str = Field(alias="Caller")
    called: str = Field(alias="Called")

    # Status and Duration
    call_status: str = Field(alias="CallStatus")
    duration: Optional[int] = Field(alias="Duration", default=None)
    call_duration: Optional[int] = Field(alias="CallDuration", default=None)
    sip_response_code: Optional[str] = Field(alias="SipResponseCode", default=None)

    # Location Details (From)
    from_city: Optional[str] = Field(alias="FromCity", default="")
    from_state: Optional[str] = Field(alias="FromState", default="")
    from_zip: Optional[str] = Field(alias="FromZip", default="")
    from_country: Optional[str] = Field(alias="FromCountry", default="")

    # Location Details (To/Called)
    to_city: Optional[str] = Field(alias="ToCity", default="")
    to_state: Optional[str] = Field(alias="ToState", default="")
    to_zip: Optional[str] = Field(alias="ToZip", default="")
    to_country: Optional[str] = Field(alias="ToCountry", default="")

    # Metadata
    timestamp: str = Field(alias="Timestamp")  # You can use datetime if you provide a custom parser
    sequence_number: str = Field(alias="SequenceNumber")
    callback_source: Optional[str] = Field(alias="CallbackSource", default=None)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"  # Highly recommended for webhooks in case the provider adds new fields
    )
