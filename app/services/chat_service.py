import asyncio
import base64
import dataclasses
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import AnyUrl
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

from app.agents.spec import AGENTS, AgentName, Envelope
from app.core.config import Settings
from app.core.logtools import log_execution_time
from app.models.models import ActionCard, ActionCardType, FlatRecipe, Recipe
from app.models.service_models import (
    ChatBotData,
    ChatRequest,
    ChatResponse,
    ImageInput,
    Mixlist,
)
from app.services.chatbot_content_search_service import ChatBotContentSearchService
from app.services.conversation_service import ConversationService
from app.services.device_info_service import DeviceInfoService
from app.services.device_service import DeviceService
from app.services.ingredient_service import IngredientService
from app.services.memory_service import MemoryService
from app.services.persona_router import PersonaContext, PersonaRouter
from app.services.response_templates import inject_persona_context_into_prompt
from app.services.vision_service import VisionService
from app.services.website_search_service import WebsiteSearchService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        vision_service: VisionService,
        memory_service: MemoryService,
        chatbot_content_search_service: ChatBotContentSearchService,
        website_search_service: WebsiteSearchService,
        device_info_service: DeviceInfoService,
        device_service: DeviceService,
        ingredient_service: IngredientService,
        conversation_service: ConversationService,
        settings: Settings,
        memory_limit: int = 5,  # how many past msgs to retrieve
    ):
        """
        The service is now initialized with other service instances.
        """
        self.vision_service = vision_service
        self.memory_service = memory_service
        self.chatbot_content_search_service = chatbot_content_search_service
        self.website_search_service = website_search_service
        self.device_info_service = device_info_service
        self.device_service = device_service
        self.ingredient_service = ingredient_service
        self.conversation_service = conversation_service
        self.settings = settings
        self.memory_limit = memory_limit
        self.persona_router = PersonaRouter()  # MVP1: Initialize persona router

    async def handle_chat_request(self, request: ChatRequest) -> ChatResponse:
        # Unified agent has been removed. Always use multi-agent flow.
        logger.info(f"Handling chat request")

        # Start timing BEFORE entering the same logging block for parity
        start = time.perf_counter()

        with log_execution_time("Total time for multi_agent"):
            response = await self._handle_chat_request(request)

            device_type_val = None
            try:
                if request.metadata and request.metadata.device:
                    # Prefer full context (includes normalized device_type when available)
                    ctx = await self.device_service.get_device_context(
                        request.metadata.device
                    )  # uses defteros + id inference
                    if ctx and ctx.get("device_type"):
                        device_type_val = ctx.get("device_type")
                    else:
                        # Fallback to local inference from device_number if context not available
                        dev_num = getattr(
                            request.metadata.device, "device_number", None
                        )
                        if dev_num:
                            device_type_val = (
                                self.device_service.infer_device_type_from_id(dev_num)
                            )  # "360" | "coaster" | None
            except Exception:
                logger.warning(
                    "Could not determine device_type for this turn", exc_info=True
                )

            # Safely serialize data for conversation storage
            action_cards_data = None
            if response.action_cards:
                action_cards_data = [
                    self._safe_serialize(ac) for ac in response.action_cards
                ]

            ai_recipe_data = None
            if response.recipes and len(response.recipes) > 0:
                ai_recipe_data = self._safe_serialize(response.recipes)

            chatbot_recipe_data = None
            if (
                response.chatbot
                and response.chatbot.recipes
                and len(response.chatbot.recipes) > 0
            ):
                chatbot_recipe_data = self._safe_serialize(response.chatbot.recipes)

            chatbot_mixlist_data = None
            if (
                response.chatbot
                and response.chatbot.mixlists
                and len(response.chatbot.mixlists) > 0
            ):
                chatbot_mixlist_data = self._safe_serialize(response.chatbot.mixlists)

            # Decide turn status: failed when AI produced empty/blank response
            status = "success" if (response.response or "").strip() else "failed"

            # Insert INSIDE the same timed/logged block with response_time=None
            message_id = self.conversation_service.append_conversation_message(
                session_id=request.session_id,
                user_id=request.user_id,
                user_message=request.input.text or "",
                bot_message=response.response or "",
                message_turn_status=status,
                action_cards=action_cards_data,
                ai_generated_recipe=ai_recipe_data,
                chatbot_recipe=chatbot_recipe_data,
                chatbot_mixlist=chatbot_mixlist_data,
                response_time=None,  # will be set after measuring
                device_type=device_type_val,
            )

        # Set response_time AFTER the block so the stored ms matches the logged scope
        try:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            self.conversation_service.set_response_time(message_id, elapsed_ms)
        except Exception as e:
            logger.error(
                f"Failed to set response_time for message {message_id}: {e}",
                exc_info=True,
            )

        # Add message_id to response before returning
        response_dict = response.model_dump()
        response_dict["message_id"] = message_id
        return ChatResponse(**response_dict)

    async def _handle_chat_request(self, request: ChatRequest) -> ChatResponse:
        with log_execution_time("Getting history"):
            history_dicts = self.memory_service.get_history_as_dicts(
                request.user_id, request.session_id, self.memory_limit
            )
            history: List[ModelMessage] = ModelMessagesTypeAdapter.validate_python(
                history_dicts
            )

        user_message: str = (request.input.text or "").strip()
        with log_execution_time("Getting image"):
            if request.input.image and request.input.image.url:
                image_url = request.input.image.url
                image_data = None
                media_type = "image/jpeg"  # Default media type

                if image_url.startswith("data:image/"):
                    try:
                        header, encoded_data = image_url.split(",", 1)
                        media_type = header.split(";")[0].split(":")[1]
                        image_data = base64.b64decode(encoded_data)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Could not parse data URI for image. Error: {e}",
                            exc_info=True,
                        )
                elif image_url.startswith("http"):
                    try:
                        async with httpx.AsyncClient(timeout=10) as client:
                            response = await client.get(
                                image_url, follow_redirects=True
                            )
                            response.raise_for_status()
                            image_data = response.content
                            media_type = response.headers.get(
                                "Content-Type", "image/jpeg"
                            )
                    except httpx.RequestError as e:
                        logger.error(
                            f"Failed to download image from URL: {image_url}. Error: {e}",
                            exc_info=True,
                        )
                else:
                    logger.warning(
                        f"Unsupported image URL format provided: {image_url}"
                    )

                if image_data:
                    vision_note = await self._vision_to_prompt(
                        request.input.image, image_data, media_type
                    )
                    user_message = f"{user_message}\n\n{vision_note}".strip()

        # Identify intent first (MVP1: returns persona context)
        agent_enum, persona_context = await self._identify_intent(user_message, history)
        agent_id = agent_enum.value
        # Log persona context for debugging
        if persona_context:
            logger.info(
                f"Persona context: {persona_context.persona.value} | "
                f"Response mode: {persona_context.response_mode.value} | "
                f"Show action cards: {self.persona_router.should_show_action_cards(persona_context)}"
            )

        # Prepare parallel tasks based on intent
        tasks = []
        task_names = []

        # 1. Always run the agent (pass persona_context for MVP1)
        with log_execution_time("Parallel execution of agent, searches"):
            tasks.append(
                self._run_agent(
                    agent_enum, request, user_message, history, persona_context
                )
            )
            task_names.append("agent")

            # 2. Run chatbot content search only when needed (explicit ask or intent requires it)
            run_chatbot_search = persona_context and getattr(
                persona_context, "needs_chatbot_content_search", False
            )
            if run_chatbot_search:
                tasks.append(self.chatbot_content_search_service.search(user_message))
                task_names.append("chatbot_search")

            # 3. Run website/URL search only when needed (explicit ask or intent benefits from URL)
            run_website_search = persona_context and getattr(
                persona_context, "needs_website_search", False
            )
            if run_website_search:
                tasks.append(self.website_search_service.search(user_message))
                task_names.append("website_search")

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Unpack results
        agent_result = None
        db_recipes: List[Recipe] = []
        db_mixlists: List[Mixlist] = []
        relevant_url = None

        for i, (result, task_name) in enumerate(zip(results, task_names)):
            # Handle exceptions
            if isinstance(result, Exception):
                logger.error(
                    f"Error in parallel task '{task_name}': {result}", exc_info=result
                )
                if task_name == "agent":
                    # Agent failure is critical, re-raise
                    raise result
                # For other tasks, continue with empty results
                continue

            # Assign results based on task name
            if task_name == "agent":
                agent_result = result
            elif task_name == "chatbot_search":
                db_recipes, db_mixlists = result
            elif task_name == "website_search":
                relevant_url = result

        if agent_result is None:
            raise RuntimeError("Agent execution failed to return a result")

        envelope = agent_result.output
        # Note: We use agent_id from intent detection (line 213) for consistency
        # envelope.metadata.agent_id should match, but we've already made decisions based on intent

        with log_execution_time("Device Context Retrieval"):
            device_context = None
            if request.metadata and request.metadata.device:
                device_context = await self.device_service.get_device_context(
                    request.metadata.device
                )

        # with the new payload, build the action cards.
        with log_execution_time("Building action cards"):
            action_cards = await self._build_action_cards(
                envelope, request.metadata, user_message, persona_context
            )

        # After action_cards are generated by the LLM, handle device-type action cards data
        await self._populate_device_action_card_data(action_cards, device_context)

        payload = envelope.data
        response_text: str = getattr(payload, "response", "")
        recipes = getattr(payload, "recipes", [])

        # Filter recipes if user asked for a specific one (e.g., "spicy margarita")
        # This ensures we only return the matching recipe, not all 3+ recipes
        if agent_id == AgentName.RECIPE.value and recipes:
            is_single_recipe = self._is_single_recipe_request(
                user_message, recipes, persona_context
            )
            if is_single_recipe:
                recipes = self._filter_matching_recipe(
                    user_message, recipes, persona_context
                )

        # station configuration is extracted at later stage

        # Post flat recipes to external service when they're generated.
        if recipes and agent_id == AgentName.RECIPE.value:
            with log_execution_time("Posting flat recipes to external service"):
                # Build the full endpoint from the configured base URL.
                flat_recipe_url = (
                    f"{self.settings.defteros_prod_api_url.rstrip('/')}/recipes/flat"
                )
                try:
                    # X-User-Id header is derived from the chat user id
                    user_id = getattr(request, "user_id", None)
                    if user_id:
                        headers = {
                            "X-User-Id": str(user_id),
                        }
                        logger.info(f"Posting flat recipes with X-User-Id={user_id}")
                    else:
                        headers = {}
                        logger.warning(
                            "Posting flat recipes without X-User-Id header; user_id is missing"
                        )

                    for recipe in recipes:
                        # Serialize the flat recipe to JSON
                        flat_recipe_json = recipe.model_dump(
                            mode="json", exclude_none=True
                        )

                        # Prepare the payload for the external service
                        recipe_payload = {
                            "name": recipe.name,
                            "session_id": request.session_id,
                            "flat_recipe_content": flat_recipe_json,
                        }

                        # Make POST request to the external service
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                flat_recipe_url,
                                json=recipe_payload,
                                headers=headers,
                                timeout=30.0,
                            )
                            response.raise_for_status()

                            # Extract the UUID from response and attach it to the recipe
                            result = response.json()
                            recipe_uuid = result.get("uuid") or result.get("id")

                            # Attach the UUID to the recipe's full_recipe_id field
                            recipe.full_recipe_id = recipe_uuid

                            logger.info(
                                f"Successfully posted recipe '{recipe.name}' to external service. UUID: {recipe_uuid}"
                            )

                except httpx.HTTPError as e:
                    logger.exception(
                        f"HTTP error while posting flat recipes to external service: {e}"
                    )
                except Exception:
                    logger.exception("Failed to post flat recipes to external service")

        chatbot: ChatBotData
        if agent_id == AgentName.RECIPE.value:
            chatbot = ChatBotData(recipes=db_recipes, mixlists=db_mixlists)
        else:
            # Unpack the dict from the payload into the ChatBotData model
            chatbot = ChatBotData(**getattr(payload, "chatbot", {}))

        # TEMPORARILY DISABLED: Creating new parent ingredients from recipe agent
        # If recipe agent proposed new categories, create them (best-effort, non-blocking)
        # if agent_id == AgentName.RECIPE.value:
        #     try:
        #         await self.ingredient_service.create_new_parent_ingredients(payload)
        #     except Exception:
        #         logger.exception("Failed while creating new parent ingredients")

        response = ChatResponse(
            response=response_text,
            recipes=recipes,
            action_cards=action_cards,
            chatbot=chatbot,
            relevant_url=relevant_url,
        )

        with log_execution_time("Updating memory"):
            new_messages = agent_result.new_messages()
            messages_to_store: List[Dict[str, Any]] = []

            for msg in new_messages:
                if dataclasses.is_dataclass(msg):
                    msg_dict = dataclasses.asdict(msg)
                else:
                    msg_dict = vars(msg)

                # For recipe and setup_stations agents: Update assistant message with UUID-enriched recipes
                if (
                    agent_id in [AgentName.RECIPE.value, AgentName.SETUP_STATIONS.value]
                    and msg_dict.get("kind") == "response"
                ):
                    # The assistant message contains structured response in 'parts' with tool-call
                    # We need to update the recipes field with UUID-enriched versions
                    try:
                        # pydantic_ai messages have a 'parts' field containing tool calls
                        parts = msg_dict.get("parts", [])

                        for part in parts:
                            if (
                                isinstance(part, dict)
                                and part.get("part_kind") == "tool-call"
                            ):
                                # Check if this tool call has args with data containing recipes
                                args = part.get("args", {})
                                if isinstance(args, dict):
                                    data = args.get("data", {})
                                    if (
                                        isinstance(data, dict)
                                        and "recipes" in data
                                        and recipes
                                    ):
                                        # Replace recipes in data with UUID-enriched versions
                                        data["recipes"] = [
                                            r.model_dump(mode="json", exclude_none=True)
                                            for r in recipes
                                        ]
                                        logger.info(
                                            f"Updated {len(recipes)} recipes with UUIDs in message history for {agent_id}"
                                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to update recipes with UUIDs in message history: {e}",
                            exc_info=True,
                        )

                messages_to_store.append(msg_dict)  # type: ignore

            self.memory_service.append_history_as_dicts(
                request.user_id, request.session_id, messages_to_store
            )

        return response

    async def _identify_intent(
        self, user_message: str, history: List[ModelMessage]
    ) -> tuple[AgentName, Optional[PersonaContext]]:
        """
        Identify the intent from user message and return the appropriate agent enum and persona context.
        MVP1: Now returns tuple of (AgentName, PersonaContext) to enable persona-aware routing.
        """
        intent_history = await self.memory_service.prepend(
            history.copy(), AgentName.INTENT.value
        )
        with log_execution_time("Identifying intent"):
            run_result = await AGENTS[AgentName.INTENT].run(
                user_message, message_history=intent_history
            )
            intent_data = run_result.output.data
            intent = intent_data.intent.lower()

            # MVP1: Extract emotion, occasion, readiness from intent response
            emotion = getattr(intent_data, "emotion", "neutral")
            occasion = getattr(intent_data, "occasion", "unknown")
            readiness = getattr(intent_data, "readiness", "explore")
            confidence = intent_data.confidence
            # Dynamic tooling: only run ChatBot content / website search when needed
            needs_chatbot_content_search = getattr(
                intent_data, "needs_chatbot_content_search", False
            )
            needs_website_search = getattr(intent_data, "needs_website_search", False)

            logger.info(
                f"Intent classification: intent={intent}, emotion={emotion}, "
                f"occasion={occasion}, readiness={readiness}, confidence={confidence:.2f}, "
                f"needs_chatbot_content_search={needs_chatbot_content_search}, needs_website_search={needs_website_search}"
            )

            # MVP1: Create persona context and route
            persona_context = PersonaContext(
                intent=intent,
                emotion=emotion,
                occasion=occasion,
                readiness=readiness,
                event_tag=None,  # TODO: Add event tagging (WEEKEND_NIGHT, etc.)
                needs_chatbot_content_search=needs_chatbot_content_search,
                needs_website_search=needs_website_search,
            )

            # Route through persona router to get persona and response mode
            persona_context = self.persona_router.route(persona_context)

            logger.info(
                f"Persona routing: persona={persona_context.persona.value}, "
                f"response_mode={persona_context.response_mode.value}"
            )

            # Map intent to agent

            try:
                agent_enum = self._map_intent_to_agent(intent)
            except ValueError:
                logger.warning(f"Unknown intent: {intent}")
                # Fallback to CHAT agent for unknown intents
                agent_enum = AgentName.CHAT

            if confidence < 0.8:
                logger.warning(
                    f"Low confidence intent ({confidence:.2f}) for '{user_message}'. "
                    f"Continuing with {agent_enum.value} agent."
                )
        logger.info(f"ROUTING to: {agent_enum.value}")
        return agent_enum, persona_context

    def _map_intent_to_agent(self, intent: str) -> AgentName:
        """
        Map MVP1 intents to appropriate agents.
        MVP1 intents (rec, shots, host, inventory, mood, action, learn)
        are routed to the RECIPE agent, but with different persona contexts.
        'buy' intent is routed to the CHAT agent.
        """
        # Recipe-related intents → RECIPE agent
        recipe_intents = [
            "rec",
            "shots",
            "host",
            "inventory",
            "mood",
            "action",
            "learn",
        ]
        if intent in recipe_intents:
            return AgentName.RECIPE

        # Legacy intent mapping
        if intent in ["recipe", "looking_for_recipe"]:
            return AgentName.RECIPE

        # Direct agent mapping
        agent_map = {
            "chat": AgentName.CHAT,
            "banter": AgentName.CHAT,  # Banter maps to CHAT
            "buy": AgentName.CHAT,  # Buy intent handled by CHAT agent
            "device": AgentName.DEVICE,
            "setup_stations": AgentName.SETUP_STATIONS,
            "off_topic": AgentName.OFF_TOPIC,
        }

        if intent in agent_map:
            return agent_map[intent]

        raise ValueError(f"Unknown intent: {intent}")

    async def _run_agent(
        self,
        agent_enum: AgentName,
        request: ChatRequest,
        user_message: str,
        history: List[ModelMessage],
        persona_context: Optional[PersonaContext] = None,
    ) -> AgentRunResult[Envelope[Any]]:
        """
        Run the specified agent with appropriate context.
        MVP1: For RECIPE agent, injects persona-aware response templates into the message.
        """
        agent = AGENTS.get(agent_enum)
        if not agent:
            raise ValueError(f"No agent defined for intent '{agent_enum.value}'")

        # different history version based on agent name because of different system prompt insertion in history
        agent_history = await self.memory_service.prepend(
            history.copy(), agent_enum.value
        )

        # Add device context for device, chat, and recipe agent queries
        message = user_message
        with log_execution_time("Getting device context"):
            if agent_enum in (AgentName.DEVICE, AgentName.CHAT, AgentName.RECIPE):
                device_context_str = await self._get_device_context_for_llm(
                    request, user_message
                )

                context_parts = []
                if device_context_str:
                    # Wrap live device status in tags for clarity
                    context_parts.append(
                        f"<device_status_context>\n{device_context_str}\n</device_status_context>"
                    )

                # MVP1: Add persona context for RECIPE agent
                if agent_enum == AgentName.RECIPE and persona_context:
                    from app.services.response_templates import (
                        ResponseTemplateGenerator,
                    )

                    generator = ResponseTemplateGenerator()
                    persona_modifier = generator.generate_prompt_modifier(
                        persona_context
                    )
                    context_parts.append(persona_modifier)
                    logger.info(
                        f"Injected MVP1 persona context for {persona_context.persona.value} / {persona_context.response_mode.value}"
                    )

                # Add FAQ context only for device agent
                if agent_enum == AgentName.DEVICE:
                    faq_context_str = self._get_device_context_for_faq(user_message)
                    if faq_context_str:
                        # faq_context_str is already formatted with tags, but remove leading/trailing whitespace
                        context_parts.append(faq_context_str.strip())

                if context_parts:
                    # Join user message and all context blocks
                    full_context = "\n\n".join(context_parts)
                    message = f"{user_message}\n\n{full_context}"

            elif agent_enum == AgentName.SETUP_STATIONS:
                # Add current station configuration for setup_stations agent
                device_context_str = await self._get_device_context_for_setup_stations(
                    request
                )

                if device_context_str:
                    message = f"{user_message}\n\n{device_context_str}"

        with log_execution_time(f"Running agent {agent_enum.value}"):
            # TEMPORARILY DISABLED: Taxonomy insertion for recipe agent (was happening at system prompt appending stage in memory_service.prepend)
            result = await agent.run(message, message_history=agent_history)

        return result

    async def _vision_to_prompt(
        self, image_input: ImageInput, image_data: bytes, image_format: str
    ) -> str:
        result = await self.vision_service.analyze_image(
            image_input, image_data, image_format
        )

        if result.ingredients:
            names = ", ".join(i.name for i in result.ingredients)
            return f"[Ingredients context: The following ingredients are available: {names}]"
        return ""

    def _is_single_recipe_request(
        self,
        user_message: str,
        recipes: List[FlatRecipe],
        persona_context: Optional[PersonaContext] = None,
    ) -> bool:
        """
        Check if user requested a single specific recipe by name or action intent.

        Args:
            user_message: User's message
            recipes: List of recipes returned
            persona_context: Optional persona context to check for ACTION mode

        Returns:
            True if this is a single recipe request (user asked for specific recipe by name OR wants to make it)
        """
        if not user_message or not recipes:
            return False

        message_lower = user_message.lower().strip()

        # Check if user message contains any recipe name from the returned recipes
        # If user says "spicy margarita" and we have a recipe named "Spicy Margarita", it's a specific request
        for recipe in recipes:
            recipe_name = recipe.name.lower() if hasattr(recipe, "name") else ""
            if recipe_name and recipe_name in message_lower:
                return True

        # Check for action intent words (user wants to make/craft/prepare the recipe)
        # Examples: "make that one", "craft it", "let's do it", "perfect, make that one"
        action_keywords = [
            "make",
            "craft",
            "prepare",
            "let's do",
            "let's make",
            "let's craft",
            "do it",
            "make it",
            "craft it",
            "that one",
            "this one",
            "go with",
            "i'll take",
            "i want",
            "i'll have",
        ]
        # Check if message contains action keywords AND there's only 1 recipe (ACTION mode)
        has_action_intent = any(keyword in message_lower for keyword in action_keywords)
        if has_action_intent and len(recipes) == 1:
            return True

        # Check if persona_context indicates ACTION mode (readiness = "act")
        # This means user is ready to make the recipe
        if persona_context:
            if persona_context.readiness == "act" and len(recipes) == 1:
                return True
            # Also check if response mode is ACTION
            if (
                hasattr(persona_context, "response_mode")
                and persona_context.response_mode.value == "ACTION"
                and len(recipes) == 1
            ):
                return True

        return False

    def _filter_matching_recipe(
        self,
        user_message: str,
        recipes: List[FlatRecipe],
        persona_context: Optional[PersonaContext] = None,
    ) -> List[FlatRecipe]:
        """
        Filter recipes to only the one that matches the user's request.

        Args:
            user_message: User's message
            recipes: List of recipes returned
            persona_context: Optional persona context to check for ACTION mode

        Returns:
            Filtered list with only the matching recipe, or original list if no match
        """
        if not user_message or not recipes:
            return recipes

        message_lower = user_message.lower().strip()

        # Find recipe whose name appears in the user message
        for recipe in recipes:
            recipe_name = recipe.name.lower() if hasattr(recipe, "name") else ""
            if recipe_name and recipe_name in message_lower:
                # Return only this matching recipe
                return [recipe]

        # Check for action intent words (user wants to make/craft/prepare)
        # If ACTION mode with 1 recipe, return that recipe
        action_keywords = [
            "make",
            "craft",
            "prepare",
            "let's do",
            "let's make",
            "let's craft",
            "do it",
            "make it",
            "craft it",
            "that one",
            "this one",
            "go with",
            "i'll take",
            "i want",
            "i'll have",
        ]
        has_action_intent = any(keyword in message_lower for keyword in action_keywords)

        # If action intent AND only 1 recipe, return that recipe
        if has_action_intent and len(recipes) == 1:
            return recipes

        # Check if persona_context indicates ACTION mode
        if persona_context:
            if persona_context.readiness == "act" and len(recipes) == 1:
                return recipes
            if (
                hasattr(persona_context, "response_mode")
                and persona_context.response_mode.value == "ACTION"
                and len(recipes) == 1
            ):
                return recipes

        return recipes

    def _user_asked_for_device(self, user_message: str) -> bool:
        """Check if user specifically asked about device."""
        if not user_message:
            return False

        message_lower = user_message.lower()
        device_keywords = [
            "connect",
            "device",
            "setup",
            "machine",
            "chatbot",
            "clean",
            "troubleshoot",
            "fix",
            "help with",
            "my device",
            "my chatbot",
        ]
        return any(kw in message_lower for kw in device_keywords)

    def _user_asked_for_shop(self, user_message: str) -> bool:
        """Check if user specifically asked about shop/buying."""
        if not user_message:
            return False

        message_lower = user_message.lower()
        shop_keywords = [
            "buy",
            "purchase",
            "shop",
            "where to buy",
            "where can i buy",
            "shopping",
            "store",
            "ingredients",
            "need to buy",
        ]
        return any(kw in message_lower for kw in shop_keywords)

    def _detect_device_specific_intent(self, user_message: str) -> Optional[str]:
        """
        Detect specific device-related intent from user message.

        Returns:
            "setup" - user asked about setup/configuration
            "clean" - user asked about cleaning/maintenance
            "troubleshoot" - user asked about troubleshooting/issues
            "calibrate" - user asked about calibration
            "connect" - user asked about connection
            None - general device query, no specific intent
        """
        if not user_message:
            return None

        message_lower = user_message.lower()

        # Setup/configuration keywords
        if any(
            kw in message_lower
            for kw in ["setup", "set up", "configure", "configuration", "initial setup"]
        ):
            return "setup"

        # Clean/maintenance keywords
        if any(
            kw in message_lower
            for kw in ["clean", "cleaning", "maintenance", "maintain"]
        ):
            return "clean"

        # Troubleshoot keywords
        if any(
            kw in message_lower
            for kw in [
                "troubleshoot",
                "trouble",
                "problem",
                "issue",
                "error",
                "fix",
                "broken",
                "not working",
            ]
        ):
            return "troubleshoot"

        # Calibrate keywords
        if any(kw in message_lower for kw in ["calibrate", "calibration"]):
            return "calibrate"

        # Connect keywords
        if any(kw in message_lower for kw in ["connect", "connection", "pair", "link"]):
            return "connect"

        return None

    def _filter_device_action_cards(
        self,
        action_cards: List[ActionCard],
        device_status: str,
        device_intent: Optional[str],
    ) -> List[ActionCard]:
        """
        Filter device action cards based on connection status and user intent.

        Rules:
        - If disconnected: Only show "Connect Device" (essential card)
        - If connected + specific intent: Only show cards matching that intent
        - If connected + no specific intent: Only show essential cards (setup, clean)
        """
        if not action_cards:
            return []

        # If device is disconnected, only show Connect Device card
        if device_status == "disconnected":
            connect_card = next(
                (
                    card
                    for card in action_cards
                    if getattr(card, "action_id", None) == "redirect:connect_device"
                ),
                None,
            )
            if connect_card:
                return [connect_card]
            # If no connect card found, create one
            return [
                ActionCard(
                    type=ActionCardType.DEVICE,
                    label="Connect Device",
                    value="Connect chatbot device",
                    action_id="redirect:connect_device",
                    data={},
                )
            ]

        # Device is connected - filter based on specific intent
        if device_intent == "setup":
            # Only show setup-related cards
            filtered = [
                card
                for card in action_cards
                if "setup" in getattr(card, "action_id", "").lower()
                or "setup" in getattr(card, "label", "").lower()
            ]
            if filtered:
                return filtered

        elif device_intent == "clean":
            # Only show clean-related cards
            filtered = [
                card
                for card in action_cards
                if "clean" in getattr(card, "action_id", "").lower()
                or "clean" in getattr(card, "label", "").lower()
            ]
            if filtered:
                return filtered

        elif device_intent == "troubleshoot":
            # Only show troubleshoot-related cards
            filtered = [
                card
                for card in action_cards
                if "troubleshoot" in getattr(card, "action_id", "").lower()
                or "troubleshoot" in getattr(card, "label", "").lower()
                or "trouble" in getattr(card, "label", "").lower()
            ]
            if filtered:
                return filtered

        elif device_intent == "calibrate":
            # Only show calibrate-related cards
            filtered = [
                card
                for card in action_cards
                if "calibrate" in getattr(card, "action_id", "").lower()
                or "calibrate" in getattr(card, "label", "").lower()
            ]
            if filtered:
                return filtered

        elif device_intent == "connect":
            # Only show connect-related cards
            filtered = [
                card
                for card in action_cards
                if "connect" in getattr(card, "action_id", "").lower()
                or "connect" in getattr(card, "label", "").lower()
            ]
            if filtered:
                return filtered

        # Default: Device connected but no specific intent - show only ONE essential card
        # Priority: Setup > Clean (Connect Device not shown if already connected)
        setup_card = next(
            (
                card
                for card in action_cards
                if getattr(card, "action_id", None) == "redirect:setup_chatbot360"
            ),
            None,
        )
        if setup_card:
            return [setup_card]

        clean_card = next(
            (
                card
                for card in action_cards
                if getattr(card, "action_id", None) == "redirect:clean_device"
            ),
            None,
        )
        if clean_card:
            return [clean_card]

        # No essential cards found - return empty (no cards by default)
        return []

    async def _build_action_cards(
        self,
        envelope: Envelope[Any],
        metadata=None,
        user_message: str = "",
        persona_context: Optional[PersonaContext] = None,
    ) -> List[ActionCard]:
        agent_id = envelope.metadata.agent_id
        payload = envelope.data
        device_status: Optional[str] = None  # Initialize device_status
        action_cards: List[ActionCard] = []

        if agent_id == AgentName.CHAT.value:
            # CHAT agent: Default is NO action cards
            # Only show action cards if user specifically asked for device/shop (handled below)
            action_cards = []

        elif agent_id == AgentName.DEVICE.value:
            # DEVICE agent: Generate action cards via ACTION_CARD agent, then filter based on context
            response_text: str = getattr(payload, "response", "")
            if response_text:
                ac_env = await AGENTS[AgentName.ACTION_CARD].run(response_text)
                generated_cards = ac_env.output.data.action_cards

                # Get device status
                if (
                    metadata
                    and metadata.device
                    and hasattr(metadata.device, "connection_status")
                ):
                    device_status = metadata.device.connection_status
                else:
                    device_status = "disconnected"

                # Detect specific device intent
                device_intent = self._detect_device_specific_intent(user_message)

                # Filter cards based on device status and intent
                action_cards = self._filter_device_action_cards(
                    generated_cards, device_status, device_intent
                )
            else:
                action_cards = []

        elif agent_id == AgentName.RECIPE.value:
            # RECIPE agent: No action cards generated (craft action cards removed)
            action_cards = []

        elif agent_id == AgentName.SETUP_STATIONS.value:
            # Get recipes and station configuration from payload
            recipes: List[FlatRecipe] = getattr(payload, "recipes", [])
            station_config = getattr(payload, "station_configuration", None)

            # Build "Setup Stations" action card with configuration data
            if station_config:
                setup_card = ActionCard(
                    type=ActionCardType.DEVICE,
                    label="Setup Stations",
                    value="Setup my stations with these ingredients",
                    action_id="redirect:setup_stations",
                    data={
                        "station_configuration": self._safe_serialize(station_config)
                    },
                )
                action_cards.append(setup_card)

            # Craft action cards removed - no longer creating craft cards for recipes
            # Generate chat action cards using ACTION_CARD agent
            names = ", ".join(r.name for r in recipes) or "station setup"
            ac_prompt = (
                f"Suggest helpful chat action cards for {names} station configuration."
            )
            ac_env = await AGENTS[AgentName.ACTION_CARD].run(ac_prompt)
            chat_cards = ac_env.output.data.action_cards

            # Filter out redirect:setup_chatbot360 cards since we already have redirect:setup_stations
            # This prevents duplicate setup-related action cards
            chat_cards = [
                card
                for card in chat_cards
                if getattr(card, "action_id", None) != "redirect:setup_chatbot360"
            ]

            action_cards.extend(chat_cards)

        # Get device status for non-DEVICE agents (CHAT, RECIPE, etc.)
        # DEVICE agent already handled this above
        if agent_id != AgentName.DEVICE.value:
            if (
                metadata
                and metadata.device
                and hasattr(metadata.device, "connection_status")
            ):
                device_status = metadata.device.connection_status
            else:
                device_status = "disconnected"

            # Filter device/shop cards: Only show when specifically asked for
            user_asked_device = self._user_asked_for_device(user_message)
            user_asked_shop = self._user_asked_for_shop(user_message)

            # Add Connect Device when disconnected AND (user asked about device OR recipe response)
            # Show whenever we returned recipes (single or multiple, e.g. "classic daiquiri" with suggestions)
            recipes_from_payload: List[FlatRecipe] = getattr(payload, "recipes", [])
            has_recipe_response = (
                agent_id == AgentName.RECIPE.value and len(recipes_from_payload) >= 1
            )
            has_connect_card = any(
                getattr(c, "action_id", None) == "redirect:connect_device"
                for c in action_cards
            )
            show_connect_device = (
                device_status == "disconnected"
                and not has_connect_card
                and (user_asked_device or has_recipe_response)
            )
            if show_connect_device:
                action_cards.append(
                    ActionCard(
                        type=ActionCardType.DEVICE,
                        label="Connect Device",
                        value="Connect chatbot device",
                        action_id="redirect:connect_device",
                        data={},
                    )
                )

            # Only add shop card if user specifically asked about shop/buying
            if user_asked_shop and (
                not metadata
                or (
                    not metadata.device
                    or not getattr(metadata.device, "device_number", None)
                )
            ):
                action_cards.append(
                    ActionCard(
                        type=ActionCardType.SHOP,
                        label="ChatBot Shop",
                        value="I want to check out the ChatBot shop",
                        action_id="redirect:shop",
                        data={
                            "shop_label": "ChatBot Shop",
                            "shop_url": self.settings.shop_url,
                        },
                    )
                )

        return action_cards

    async def _populate_device_action_card_data(
        self,
        action_cards: List[ActionCard],
        device_context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Populate data for device action cards based on device context.
        This centralizes the action card data population logic.
        """
        if not device_context:
            return

        for ac in action_cards:
            if getattr(ac, "type", None) == ActionCardType.DEVICE:
                if getattr(ac, "action_id", None) == "redirect:clean_device":
                    # Get stations with some quantity for clean device action
                    stations = await self._get_stations_with_quantity(device_context)
                    ac.data = {"stations": stations}
                # Note: Other device action cards (e.g., redirect:connect_device, redirect:setup_stations)
                # already have their data populated when created, so no additional handling needed here

    def _get_device_context_for_faq(self, user_message: str, top_k: int = 3) -> str:
        """
        Retrieve relevant device documentation chunks for the user's query using DeviceInfoService.
        """
        try:
            results = self.device_info_service.search_faq(user_message, top_k=top_k)
            if not results:
                logger.info("No relevant device documentation found for query")
                return ""
            context_parts = []
            for i, (text, source, index) in enumerate(results, 1):
                context_parts.append(
                    f"Documentation Chunk {i} (Source: {source}):\n{text}"
                )
            device_context = "\n\n".join(context_parts)
            logger.info(
                f"Retrieved {len(results)} device documentation chunks for context"
            )
            return f"\n\n<device_documentation_context>\n{device_context}\n</device_documentation_context>\n"
        except Exception as e:
            logger.error(f"Error retrieving device context: {e}")
            return ""

    async def _get_stations_with_quantity(
        self, device_context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """
        Get list of station letters that have some remaining quantity.
        This centralizes the station extraction logic.
        """
        if not device_context:
            return []

        available_ingredients = device_context.get("available_ingredients", [])

        stations = []
        for ingredient_info in available_ingredients:
            station_number = ingredient_info.get("station")
            remaining_ml = ingredient_info.get("remaining_ml")
            if (
                station_number is not None
                and remaining_ml is not None
                and remaining_ml > 0
            ):
                stations.append(station_number)

        return stations

    async def _get_device_context_for_llm(
        self, request: ChatRequest, user_message: str
    ) -> str:
        """
        Get device context information for the agent from metadata provided by mobile app.
        """
        if not request.metadata or not request.metadata.device:
            return ""
        device_metadata = request.metadata.device
        device_context = await self.device_service.get_device_context(device_metadata)

        if not device_context:
            return f"Device {getattr(device_metadata, 'device_number', 'unknown')} - Error getting details"

        context_parts = []

        # Add connection status from metadata
        if "connection_status" in device_context:
            context_parts.append(
                f"Connection Status: {device_context['connection_status']}"
            )

        # Add hardware context information
        device_type = device_context.get("device_type")
        if device_type:
            context_parts.append(f"Device Type: {device_type}")

        available_ingredients = device_context.get("available_ingredients", [])
        if available_ingredients:
            ingredient_list = [
                f"{ing['ingredient']} (Station {ing['station']})"
                for ing in available_ingredients
            ]
            context_parts.append(f"Available Ingredients: {', '.join(ingredient_list)}")

        empty_stations = device_context.get("empty_stations", [])
        if empty_stations:
            context_parts.append(
                f"Empty Stations: {', '.join(map(str, empty_stations))}"
            )

        low_stock_stations = device_context.get("low_stock_stations", [])
        if low_stock_stations:
            low_stock_list = [
                f"{ing['ingredient']} (Station {ing['station']}, {ing['remaining_ml']}ml)"
                for ing in low_stock_stations
            ]
            context_parts.append(f"Low Stock: {', '.join(low_stock_list)}")

        return "; ".join(context_parts)

    async def _get_device_context_for_setup_stations(self, request: ChatRequest) -> str:
        """
        Get detailed device station configuration for the setup_stations agent.
        Returns a formatted JSON structure with complete station information.
        """
        if not request.metadata or not request.metadata.device:
            return ""

        device_metadata = request.metadata.device
        device_context = await self.device_service.get_device_context(device_metadata)

        if not device_context:
            logger.warning(
                f"Could not get device context for setup_stations agent. Device: {getattr(device_metadata, 'device_number', 'unknown')}"
            )
            return ""

        # Build detailed station configuration JSON
        config_data = {
            "device_type": device_context.get("device_type", "360"),
            "connection_status": device_context.get("connection_status", "unknown"),
        }

        # Add detailed station information
        stations_config = {}
        available_ingredients = device_context.get("available_ingredients", [])

        # Build stations A-F with ingredient details
        for ing_info in available_ingredients:
            station = ing_info.get("station")
            if station:
                station_data = {
                    "ingredient": ing_info.get("ingredient", "Unknown"),
                    "quantity_ml": ing_info.get("remaining_ml", 0),
                    "perishable": ing_info.get("perishable", False),
                }

                # Add category information if available
                if "category_primary" in ing_info:
                    station_data["category_primary"] = ing_info.get("category_primary")
                if "secondary_category" in ing_info:
                    station_data["secondary_category"] = ing_info.get(
                        "secondary_category"
                    )

                stations_config[station] = station_data

        # Mark empty stations
        empty_stations = device_context.get("empty_stations", [])
        for station in empty_stations:
            if station not in stations_config:
                stations_config[station] = {
                    "ingredient": None,
                    "quantity_ml": 0,
                    "empty": True,
                }

        config_data["stations"] = stations_config
        config_data["empty_stations"] = empty_stations

        # Add low stock information
        low_stock_stations = device_context.get("low_stock_stations", [])
        config_data["low_stock_stations"] = [
            ing.get("station") for ing in low_stock_stations if ing.get("station")
        ]

        # Format as tagged JSON for the LLM
        config_json = json.dumps(config_data, indent=2)
        return f"<current_station_configuration>\n{config_json}\n</current_station_configuration>"

    def _safe_serialize(self, obj: Any) -> Any:
        if obj is None:
            return None

        # Pydantic v2 models → JSON-safe
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json", exclude_none=True)

        # Pydantic URL types → string
        if isinstance(obj, AnyUrl):
            return str(obj)

        # Dataclasses → dict, then jsonable
        if dataclasses.is_dataclass(obj):
            return to_jsonable_python(dataclasses.asdict(obj))

        if isinstance(obj, list):
            return [self._safe_serialize(i) for i in obj]

        if isinstance(obj, dict):
            return {k: self._safe_serialize(v) for k, v in obj.items()}

        # Last resort: make anything else JSON-safe
        return to_jsonable_python(obj)
