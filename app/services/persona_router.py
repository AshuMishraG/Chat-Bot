"""
PersonaRouter Service

Routes intent + emotion + occasion → persona → response mode
This is the core decision engine for MVP1 that determines:
1. Which persona to activate (Host, Date Night, Solo Ritual, Party Chaos, Beginner)
2. Which response template to use
3. Whether action cards should appear
"""

import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PersonaType(str, Enum):
    """MVP1 Persona Types"""

    HOST = "host"  # The Host (anxious → confident)
    DATE_NIGHT = "date_night"  # Date Night / Flirt
    SOLO_RITUAL = "solo_ritual"  # Solo Ritual / Self-Care
    PARTY_CHAOS = "party_chaos"  # Party / Shots
    BEGINNER = "beginner"  # Beginner / Curious


class ResponseMode(str, Enum):
    """Response template modes"""

    PRESCRIPTION = "prescription"  # Explore mode: 3 options + pick
    REFINEMENT = "refinement"  # Narrow mode: 2 variations
    ACTION = "action"  # Act mode: 1 recipe + steps + cards
    HOST_MODE = "host_mode"  # Host: flight/batch
    MOOD_MODE = "mood_mode"  # Mood: vibe-based
    EDUCATION = "education"  # Learn: explanation + example
    BANTER = "banter"  # Banter: joke + recommend


class PersonaContext(BaseModel):
    """Complete context for persona routing"""

    intent: str
    emotion: str
    occasion: str
    readiness: str
    event_tag: Optional[str] = None  # e.g., "WEEKEND_NIGHT", "SUMMER"

    # Dynamic tooling: only run when explicitly asked or needed for intent
    needs_chatbot_content_search: bool = False
    needs_website_search: bool = False

    # Outputs (populated by router)
    persona: Optional[PersonaType] = None
    response_mode: Optional[ResponseMode] = None


class PersonaRouter:
    """
    Routes intent + emotion + occasion → persona → response mode

    This is the decision engine that determines:
    1. Which persona to activate
    2. Which response template to use
    3. Whether action cards should appear
    """

    def route(self, context: PersonaContext) -> PersonaContext:
        """
        Main routing logic: determines persona and response mode

        Args:
            context: PersonaContext with intent, emotion, occasion, readiness

        Returns:
            PersonaContext with persona and response_mode populated
        """
        # Step 1: Determine persona
        context.persona = self._determine_persona(context)

        # Step 2: Determine response mode
        context.response_mode = self._determine_response_mode(context)

        logger.info(
            f"Persona routing: intent={context.intent}, emotion={context.emotion}, "
            f"occasion={context.occasion}, readiness={context.readiness} → "
            f"persona={context.persona.value}, mode={context.response_mode.value}"
        )

        return context

    def _determine_persona(self, context: PersonaContext) -> PersonaType:
        """
        Decision tree for persona selection

        Priority order:
        1. Check explicit HOST intent or occasion
        2. Check MOOD + ROMANTIC combination (Date Night)
        3. Check SHOTS + excitement (Party Chaos)
        4. Check LEARN or CURIOUS (Beginner)
        5. Check STRESSED/RELAXED (Solo Ritual)
        6. Default to Solo Ritual
        """
        intent = context.intent.lower()
        emotion = context.emotion.lower()
        occasion = context.occasion.lower()

        # HOST persona (highest priority)
        if intent == "host" or occasion == "host":
            return PersonaType.HOST

        # DATE NIGHT persona
        if (intent == "mood" and emotion == "romantic") or occasion == "date":
            return PersonaType.DATE_NIGHT

        # PARTY CHAOS persona
        if (intent == "shots" or occasion == "pregame") and emotion in [
            "excited",
            "neutral",
        ]:
            # Check if it's weekend night for extra party energy
            if context.event_tag == "WEEKEND_NIGHT":
                logger.info("Weekend night detected - amplifying party energy")
            return PersonaType.PARTY_CHAOS

        # BEGINNER persona
        if intent == "learn" or emotion == "curious":
            return PersonaType.BEGINNER

        # SOLO RITUAL persona
        if emotion in ["stressed", "relaxed", "sad"] or occasion == "solo":
            return PersonaType.SOLO_RITUAL

        # RECOVERY mode (special case of Solo Ritual)
        if emotion == "hangover" or occasion == "recovery":
            return PersonaType.SOLO_RITUAL

        # Default fallback
        logger.info("No specific persona match - defaulting to SOLO_RITUAL")
        return PersonaType.SOLO_RITUAL

    def _determine_response_mode(self, context: PersonaContext) -> ResponseMode:
        """
        Maps (persona + readiness + intent) → response mode

        Response mode determines template structure and action card behavior
        """
        intent = context.intent.lower()
        readiness = context.readiness.lower()
        persona = context.persona

        # Special intent-driven modes (override persona/readiness)
        if intent == "host":
            return ResponseMode.HOST_MODE

        if intent == "learn":
            return ResponseMode.EDUCATION

        if intent == "banter":
            return ResponseMode.BANTER

        if intent in ["action", "buy"]:
            return ResponseMode.ACTION

        if intent == "mood":
            return ResponseMode.MOOD_MODE

        # Readiness-driven modes for recipe intents
        if readiness == "act":
            return ResponseMode.ACTION

        if readiness == "narrow":
            return ResponseMode.REFINEMENT

        if readiness == "explore":
            return ResponseMode.PRESCRIPTION

        # Default
        logger.warning(f"No specific response mode match - defaulting to PRESCRIPTION")
        return ResponseMode.PRESCRIPTION

    def should_show_action_cards(self, context: PersonaContext) -> bool:
        """
        Determines if action cards should appear

        Hard rules (from MVP1 spec + updates):
        - Show if readiness == ACT
        - Show if intent == ACTION or BUY or SETUP_STATIONS
        - Do NOT show for HOST intent (user requested removal)
        - Do NOT show if readiness == EXPLORE or NARROW
        """
        readiness = context.readiness.lower()
        intent = context.intent.lower()

        if readiness == "act":
            return True

        # HOST intent removed from this list per user request
        if intent in ["action", "buy", "setup_stations"]:
            return True

        return False

    def get_persona_traits(self, persona: PersonaType) -> dict:
        """
        Returns personality traits for a given persona
        Used for prompt customization and response generation
        """
        traits = {
            PersonaType.HOST: {
                "tone": "confident, organized, effortless cool",
                "goal": "make hosting easy and impressive",
                "energy": "calm but exciting",
                "key_phrases": ["lineup", "batch", "impress", "easy win"],
            },
            PersonaType.DATE_NIGHT: {
                "tone": "smooth, flirty, classy",
                "goal": "create chemistry and impress",
                "energy": "seductive but sophisticated",
                "key_phrases": ["sexy", "smooth", "chemistry", "dangerous"],
            },
            PersonaType.SOLO_RITUAL: {
                "tone": "calm, premium, sophisticated",
                "goal": "self-care and comfort",
                "energy": "quiet luxury",
                "key_phrases": ["treat yourself", "perfect", "unwind", "premium"],
            },
            PersonaType.PARTY_CHAOS: {
                "tone": "hype, savage, playful",
                "goal": "maximize fun and energy",
                "energy": "nightlife chaos",
                "key_phrases": ["shots", "fast", "hype", "dangerous", "pregame"],
            },
            PersonaType.BEGINNER: {
                "tone": "encouraging, educational, aspirational",
                "goal": "build confidence and knowledge",
                "energy": "supportive",
                "key_phrases": ["easy", "learn", "you'll look pro", "simple"],
            },
        }
        return traits.get(persona, traits[PersonaType.SOLO_RITUAL])
