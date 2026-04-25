from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model as AIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from app.agents.intent_prompt import (
    INTENT_CLASSIFIER_PROMPT_CHAT_ORIENTED,
    INTENT_CLASSIFIER_PROMPT_MVP1,
)
from app.agents.prompts import SETUP_STATIONS_AGENT_PROMPT  # define in prompt
from app.agents.prompts import (
    ACTION_CARD_PROMPT,
    CHAT_AGENT_PROMPT,
    DEVICE_AGENT_PROMPT,
    RECIPE_AGENT_PROMPT,
    RECIPE_AGENT_PROMPT_NESTED,
    SINGLE_RECIPE_AGENT_PROMPT,
    VISION_AGENT_PROMPT,
    WEBSITE_AGENT_PROMPT,
)
from app.models.models import SetupStationsAgentResponse  # define in models
from app.models.models import (
    ActionCardResponse,
    ChatAgentResponse,
    DeviceAgentResponse,
    FullRecipeAgentResponse,
    IntentAgentResponse,
    OffTopicAgentResponse,
    RecipeAgentResponse,
    SingleRecipeAgentResponse,
    VisionResult,
    VisionResult_llm,
    WebsiteAgentResponse,
)

off_topic_response_text = """
    I'm BarBot, your personal cocktail and ChatBot assistant!
    I can help you discover new drink recipes or answer questions about your ChatBot device.
    Sorry, I can't help with topics outside of that.
    What cocktail are you in the mood for, or how can I assist with your ChatBot device today?"""

output_arguments = {"data": {"response": off_topic_response_text}}
stub = TestModel(custom_output_args=output_arguments)


class Metadata(BaseModel):
    agent_id: Optional[str] = None
    llm_model: Optional[str] = None
    request_tokens: Optional[int] = None
    response_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


T_Payload = TypeVar("T_Payload", bound=BaseModel)


class Envelope(BaseModel, Generic[T_Payload]):
    metadata: Metadata = Field(default_factory=Metadata)
    data: T_Payload


@dataclass(slots=True)
class AgentSpec(Generic[T_Payload]):
    name: str
    system_prompt: str
    output_model: Type[T_Payload]

    model: str | AIModel | None = None

    retries: int = 3

    def build(self) -> Agent[None, Envelope[T_Payload]]:
        output_type = Envelope[self.output_model]

        agent = Agent(
            model=self.model,
            output_type=output_type,
            system_prompt=self.system_prompt,
            name=self.name,
            retries=self.retries,
        )

        @agent.output_validator
        async def _inject_meta(
            ctx: RunContext[None], out: Envelope[T_Payload]
        ) -> Envelope[T_Payload]:
            model_name = "unknown"
            if isinstance(self.model, str):
                model_name = self.model
            elif hasattr(self.model, "model_name"):
                model_name = self.model.model_name  # type: ignore

            meta = Metadata(
                agent_id=self.name,
                llm_model=model_name,
                request_tokens=ctx.usage.request_tokens or 0,
                response_tokens=ctx.usage.response_tokens or 0,
                total_tokens=ctx.usage.total_tokens or 0,
            )
            return out.model_copy(update={"metadata": meta})

        return agent


class AgentName(str, Enum):
    """Agent identifiers for routing"""

    # Core agents
    INTENT = "intent"
    CHAT = "chat"
    DEVICE = "device"
    SETUP_STATIONS = "setup_stations"

    # Recipe agents (MVP1 intents map to RECIPE agent for now)
    RECIPE = "recipe"
    REC = "rec"  # Maps to RECIPE
    SHOTS = "shots"  # Maps to RECIPE
    HOST = "host"  # Maps to RECIPE (but uses HOST_MODE)
    INVENTORY = "inventory"  # Maps to RECIPE
    MOOD = "mood"  # Maps to RECIPE (but uses MOOD_MODE)
    ACTION = "action"  # Maps to RECIPE (ACTION mode)
    BUY = "buy"  # Maps to RECIPE (ACTION mode)
    LEARN = "learn"  # Maps to RECIPE (EDUCATION mode)
    BANTER = "banter"  # Maps to CHAT

    # Legacy (for backward compatibility)
    LOOKING_FOR_RECIPE = "looking_for_recipe"

    # Utility agents
    ACTION_CARD = "action_card"
    VISION = "vision"
    OFF_TOPIC = "off_topic"
    SINGLE_RECIPE = "single_recipe"
    WEBSITE = "website"
    FULL_RECIPE = "full_recipe"


gemini_model = GeminiModel(
    "gemini-2.5-flash", provider=GoogleGLAProvider(api_key=os.getenv("GOOGLE_API_KEY"))
)


AGENT_SPECS: Dict[AgentName, AgentSpec] = {
    AgentName.SINGLE_RECIPE: AgentSpec[SingleRecipeAgentResponse](
        name=AgentName.SINGLE_RECIPE.value,
        model="openai:gpt-4.1-mini",
        system_prompt=SINGLE_RECIPE_AGENT_PROMPT,
        output_model=SingleRecipeAgentResponse,
        retries=3,
    ),
    AgentName.CHAT: AgentSpec[ChatAgentResponse](
        name=AgentName.CHAT.value,
        model=gemini_model,
        system_prompt=CHAT_AGENT_PROMPT,
        output_model=ChatAgentResponse,
        retries=3,
    ),
    AgentName.DEVICE: AgentSpec[DeviceAgentResponse](
        name=AgentName.DEVICE.value,
        model="openai:gpt-4.1-mini",
        system_prompt=DEVICE_AGENT_PROMPT,
        output_model=DeviceAgentResponse,
        retries=3,
    ),
    AgentName.INTENT: AgentSpec[IntentAgentResponse](
        name=AgentName.INTENT.value,
        # model="openai:gpt-3.5-turbo",
        model=gemini_model,
        system_prompt=INTENT_CLASSIFIER_PROMPT_MVP1,  # Using MVP1 prompt now
        output_model=IntentAgentResponse,
        retries=3,
    ),
    AgentName.RECIPE: AgentSpec[RecipeAgentResponse](
        name=AgentName.RECIPE.value,
        # model="openai:gpt-4o",
        model=gemini_model,
        system_prompt=RECIPE_AGENT_PROMPT,
        output_model=RecipeAgentResponse,
        retries=3,
    ),
    AgentName.ACTION_CARD: AgentSpec[ActionCardResponse](
        name=AgentName.ACTION_CARD.value,
        # model="openai:gpt-4.1-mini",
        model=gemini_model,
        system_prompt=ACTION_CARD_PROMPT,
        output_model=ActionCardResponse,
        retries=3,
    ),
    AgentName.VISION: AgentSpec[VisionResult_llm](
        name=AgentName.VISION.value,
        model="openai:gpt-5.2",
        system_prompt=VISION_AGENT_PROMPT,
        output_model=VisionResult_llm,
        retries=3,
    ),
    AgentName.OFF_TOPIC: AgentSpec[OffTopicAgentResponse](
        name=AgentName.OFF_TOPIC.value,
        model=stub,
        system_prompt="IGNORED",
        output_model=OffTopicAgentResponse,
    ),
    AgentName.WEBSITE: AgentSpec[WebsiteAgentResponse](
        name=AgentName.WEBSITE.value,
        model=gemini_model,
        system_prompt=WEBSITE_AGENT_PROMPT,
        output_model=WebsiteAgentResponse,
        retries=3,
    ),
    AgentName.FULL_RECIPE: AgentSpec[FullRecipeAgentResponse](
        name=AgentName.FULL_RECIPE.value,
        model=gemini_model,
        system_prompt=RECIPE_AGENT_PROMPT_NESTED,
        output_model=FullRecipeAgentResponse,
        retries=3,
    ),
    AgentName.SETUP_STATIONS: AgentSpec[SetupStationsAgentResponse](
        name=AgentName.SETUP_STATIONS.value,
        model="openai:gpt-4o",
        system_prompt=SETUP_STATIONS_AGENT_PROMPT,
        output_model=SetupStationsAgentResponse,
        retries=3,
    ),
}

AGENTS: Dict[AgentName, Agent[None, Envelope[Any]]] = {
    AgentName.CHAT: AGENT_SPECS[AgentName.CHAT].build(),
    AgentName.DEVICE: AGENT_SPECS[AgentName.DEVICE].build(),
    AgentName.INTENT: AGENT_SPECS[AgentName.INTENT].build(),
    AgentName.RECIPE: AGENT_SPECS[AgentName.RECIPE].build(),
    AgentName.ACTION_CARD: AGENT_SPECS[AgentName.ACTION_CARD].build(),
    AgentName.VISION: AGENT_SPECS[AgentName.VISION].build(),
    AgentName.OFF_TOPIC: AGENT_SPECS[AgentName.OFF_TOPIC].build(),
    AgentName.SINGLE_RECIPE: AGENT_SPECS[AgentName.SINGLE_RECIPE].build(),
    AgentName.WEBSITE: AGENT_SPECS[AgentName.WEBSITE].build(),
    AgentName.FULL_RECIPE: AGENT_SPECS[AgentName.FULL_RECIPE].build(),
    AgentName.SETUP_STATIONS: AGENT_SPECS[AgentName.SETUP_STATIONS].build(),
}
