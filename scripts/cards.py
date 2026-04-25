from enum import Enum
from typing import Annotated, Any, Dict, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class ChatPayload(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)


class ContentPayload(BaseModel):
    content_type: str
    data: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class HardwareCommand(str, Enum):
    CRAFT = "craft"
    CONNECT = "connect"
    CLEAN = "clean"


class HardwarePayload(BaseModel):
    command: HardwareCommand
    data: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ChatActionCard(BaseModel):
    id: str
    type: Literal["chat"]
    label: str
    payload: ChatPayload

    model_config = ConfigDict(from_attributes=True)


class ContentActionCard(BaseModel):
    id: str
    type: Literal["content"]
    label: str
    payload: ContentPayload

    model_config = ConfigDict(from_attributes=True)


class HardwareActionCard(BaseModel):
    id: str
    type: Literal["hardware"]
    label: str
    payload: HardwarePayload

    model_config = ConfigDict(from_attributes=True)


ActionCard = Annotated[
    Union[ChatActionCard, ContentActionCard, HardwareActionCard],
    Field(discriminator="type"),
]
