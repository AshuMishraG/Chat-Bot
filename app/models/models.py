from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID as UUIDType

from pydantic import BaseModel, Field, HttpUrl


class IngredientCategory(BaseModel):
    primary: str = Field(
        ..., description="Primary category (base, mixer, additional, garnish)"
    )
    secondary: Optional[str] = Field(
        None, description="Secondary category(vodka, gin, rum, juice, citrus, etc.)"
    )
    flavourTags: Optional[List[str]] = Field(
        default=[], description="Taste-related tags"
    )


class Ingredient(BaseModel):
    name: str
    quantity: float = Field(..., gt=0)
    unit: str
    category: Optional[IngredientCategory] = None
    optional: bool = False
    perishable: bool | None = None
    substitutes: List[str] = []
    notes: Optional[str] = None


class VisionIngredient(BaseModel):
    name: str
    category: Optional[IngredientCategory] = None
    substitutes: List[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    perishable: bool | None = None


# type: Literal["base", "mixer", "garnish", "additional"]


class VisionResult(BaseModel):
    ingredients: Optional[List[VisionIngredient]] = None


class VisionResult_llm(BaseModel):
    ingredients: Optional[List[VisionIngredient]] = None
    new_parent_ingredients: Optional[List[Dict[str, Any]]] = None


class Image(BaseModel):
    url: HttpUrl
    alt: Optional[str] = Field(None, max_length=200)  # Optional: API may return only url
    photographer: Optional[str] = None


class Glassware(BaseModel):
    type: str
    chilled: bool = False
    size: Optional[str] = None
    notes: Optional[str] = None


class Recipe(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1500)
    slug: Optional[str] = None
    image: Optional[Image] = None
    ice: Optional[str] = None
    ingredients: List[Ingredient]
    instructions: List[str] = Field(..., min_length=1)
    mixingTechnique: Optional[
        Literal[
            "shaken",
            "stirred",
            "built",
            "layered",
            "muddled",
            "blended",
            "thrown",
            "rolled",
            "strained",
        ]
    ] = None
    glassware: Glassware
    difficulty: Optional[Literal["easy", "moderate", "challenging", "expert"]] = None
    preparationTime: Optional[int] = None
    totalTime: Optional[int] = None
    servingSize: Optional[int] = None
    tags: List[str] = []
    notes: Optional[str] = None
    source: Optional[str] = None
    variations: List[str] = []
    author: Optional[Dict[str, Any]] = None
    chatbot_360_compatible: bool = False
    deprecated_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FlatRecipe(BaseModel):
    """
    Flat recipe schema where ingredients are stored as indexed fields.
    Supports up to 10 ingredients (indices 0-9).
    Example: ingredient_0, ingredient_type_0, secondary_category_0, perishable_0, quantity_0, etc.
    Each ingredient has: name, type (primary category), secondary category, perishable flag, and quantity.
    """

    name: str
    description: str
    no_ingredients: int

    # Explicitly defined ingredient fields (0-9) for structured output
    ingredient_0: Optional[str] = Field(None, description="First ingredient name")
    ingredient_type_0: Optional[str] = Field(
        None, description="Type: base|mixer|additional|garnish"
    )
    secondary_category_0: Optional[str] = Field(
        None, description="Secondary category: vodka, gin, rum, juice, citrus, etc."
    )
    perishable_0: Optional[bool] = Field(
        None, description="Whether the ingredient is perishable"
    )
    quantity_0: Optional[str] = Field(
        None, description="Quantity with unit, e.g. '2 oz'"
    )

    ingredient_1: Optional[str] = None
    ingredient_type_1: Optional[str] = None
    secondary_category_1: Optional[str] = None
    perishable_1: Optional[bool] = None
    quantity_1: Optional[str] = None

    ingredient_2: Optional[str] = None
    ingredient_type_2: Optional[str] = None
    secondary_category_2: Optional[str] = None
    perishable_2: Optional[bool] = None
    quantity_2: Optional[str] = None

    ingredient_3: Optional[str] = None
    ingredient_type_3: Optional[str] = None
    secondary_category_3: Optional[str] = None
    perishable_3: Optional[bool] = None
    quantity_3: Optional[str] = None

    ingredient_4: Optional[str] = None
    ingredient_type_4: Optional[str] = None
    secondary_category_4: Optional[str] = None
    perishable_4: Optional[bool] = None
    quantity_4: Optional[str] = None

    ingredient_5: Optional[str] = None
    ingredient_type_5: Optional[str] = None
    secondary_category_5: Optional[str] = None
    perishable_5: Optional[bool] = None
    quantity_5: Optional[str] = None

    ingredient_6: Optional[str] = None
    ingredient_type_6: Optional[str] = None
    secondary_category_6: Optional[str] = None
    perishable_6: Optional[bool] = None
    quantity_6: Optional[str] = None

    ingredient_7: Optional[str] = None
    ingredient_type_7: Optional[str] = None
    secondary_category_7: Optional[str] = None
    perishable_7: Optional[bool] = None
    quantity_7: Optional[str] = None

    ingredient_8: Optional[str] = None
    ingredient_type_8: Optional[str] = None
    secondary_category_8: Optional[str] = None
    perishable_8: Optional[bool] = None
    quantity_8: Optional[str] = None

    ingredient_9: Optional[str] = None
    ingredient_type_9: Optional[str] = None
    secondary_category_9: Optional[str] = None
    perishable_9: Optional[bool] = None
    quantity_9: Optional[str] = None

    full_recipe_id: Optional[str] = None

    model_config = {
        "extra": "allow"
    }  # Allows additional fields beyond 10 ingredients if needed


class RecipeAgentResponse(BaseModel):
    """Recipe agent response - returns recipes in flat format with indexed ingredient fields"""

    response: str
    recipes: List[FlatRecipe] = []
    new_parent_ingredients: List[Dict[str, Any]] = []


class SingleRecipeAgentResponse(BaseModel):
    response: str
    recipe: Recipe


class FullRecipeAgentResponse(BaseModel):
    """Full recipe agent response - returns a single recipe with nested ingredient structure"""

    response: str
    recipe: Recipe


class ChatAgentResponse(BaseModel):
    response: str


class DeviceAgentResponse(BaseModel):
    response: str


class IntentType(str, Enum):
    """MVP1 Intent Types"""

    # Recipe intents
    REC = "rec"
    SHOTS = "shots"
    HOST = "host"
    INVENTORY = "inventory"
    MOOD = "mood"
    ACTION = "action"
    BUY = "buy"
    LEARN = "learn"

    # Meta intents
    BANTER = "banter"
    CHAT = "chat"

    # Device intents (legacy, kept for compatibility)
    RECIPE = "recipe"  # Legacy - maps to REC
    LOOKING_FOR_RECIPE = "looking_for_recipe"  # Legacy - maps to REC
    DEVICE = "device"
    SETUP_STATIONS = "setup_stations"

    # Fallback
    OFF_TOPIC = "off_topic"


class EmotionType(str, Enum):
    """User emotional states"""

    STRESSED = "stressed"
    EXCITED = "excited"
    ROMANTIC = "romantic"
    RELAXED = "relaxed"
    CURIOUS = "curious"
    SAD = "sad"
    HANGOVER = "hangover"
    NEUTRAL = "neutral"


class OccasionType(str, Enum):
    """Social occasion context"""

    DATE = "date"
    HOST = "host"
    SOLO = "solo"
    PREGAME = "pregame"
    CELEBRATE = "celebrate"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


class ReadinessType(str, Enum):
    """User readiness to take action"""

    EXPLORE = "explore"
    NARROW = "narrow"
    ACT = "act"


class IntentAgentResponse(BaseModel):
    """Response from intent classification agent with full context (MVP1)"""

    intent: str = Field(..., description="Classified intent type")
    emotion: str = Field(..., description="Detected emotional state")
    occasion: str = Field(..., description="Social occasion context")
    readiness: str = Field(..., description="User readiness level")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    # Dynamic tooling: only run these when explicitly asked or needed for the intent
    needs_chatbot_content_search: bool = Field(
        False,
        description="True when user explicitly asks for recipe/content search or intent requires ChatBot recipes/mixlists (rec, shots, host, inventory, mood, action, learn).",
    )
    needs_website_search: bool = Field(
        False,
        description="True when user explicitly asks for a link/URL/website or intent would benefit from a relevant ChatBot URL (e.g. device, learn, buy).",
    )


class StationSetup(BaseModel):
    """Configuration for a single station in the ChatBot 360"""

    ingredient: str = Field(
        ...,
        description="Specific ingredient name (e.g., 'Blanco Tequila', 'Fresh Lime Juice')",
    )
    secondary_category: str = Field(
        ...,
        description="Secondary category from taxonomy (e.g., 'tequila', 'citrus', 'rum')",
    )
    category_primary: str = Field(
        ..., description="Primary category: base|mixer|additional|garnish"
    )
    perishable: bool = Field(..., description="Whether the ingredient is perishable")
    reason: str = Field(
        ...,
        description="Brief explanation why this ingredient is recommended for this station",
    )


class SetupStationsAgentResponse(BaseModel):
    """Response from setup stations agent with full 6-station configuration"""

    response: str = Field(
        ..., description="Engaging message explaining the setup recommendation"
    )
    station_configuration: Optional[Dict[str, StationSetup]] = Field(
        None,
        description="Complete 6-station setup keyed by station letter (A, B, C, D, E, F). Null for ChatBot Coaster or when device is disconnected.",
    )
    recipes: List[FlatRecipe] = Field(
        default=[], description="Recipes that can be made with this station setup"
    )
    makeable_recipes: List[str] = Field(
        default=[],
        description="List of recipe names that can be crafted with this configuration",
    )


class ActionCardType(str, Enum):
    CHAT = "chat"
    DEVICE = "device"
    SHOP = "shop"


# TODO: add a scoring mechanism to the action cards
class ActionCard(BaseModel):
    type: ActionCardType = ActionCardType.CHAT
    label: str  # label to be rendered in the UI
    value: str  # the message the user would type if they selected the action card
    action_id: str  # Unique ID to describe what action this represents
    data: Dict[str, Any]  # any additional data to be passed to the action card


class ActionCardResponse(BaseModel):
    action_cards: List[ActionCard]


class OffTopicAgentResponse(BaseModel):
    response: str


class WebsiteAgentResponse(BaseModel):
    """Response from website agent determining if a URL should be returned"""

    should_return_url: bool = Field(
        ..., description="Whether a URL would be helpful for this query"
    )
    url: Optional[str] = Field(
        None, description="The most relevant URL if should_return_url is True"
    )
    reason: Optional[str] = Field(None, description="Brief reason for the decision")


class ImageAnalysisCache(BaseModel):
    """Pydantic model for image analysis cache operations - Simplified"""

    perceptual_hash: str
    image_size: str
    image_format: str
    file_size: int
    ingredients: Optional[List[dict]] = None
    analysis_confidence: Optional[float] = None
    created_at: datetime
    last_accessed: datetime
    access_count: int


class StatusResponse(BaseModel):
    status: str
    message: str


class Mixlist(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    slug: Optional[str] = None
    author: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    image: Optional[Image] = None
    chatbot_360_compatible: bool = False
    recipes: List[Recipe] = []
    deprecated_id: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MixlistAgentResponse(BaseModel):
    response: str
    mixlists: List[Mixlist] = []


class CombinedAgentResponse(BaseModel):
    intent: str = Field(..., pattern="^(recipe|device|chat|off_topic)$")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0."
    )
    response: str
    recipes: List[Recipe] = []
    action_cards: List[ActionCard] = []
    chatbot: Dict[str, Any] = {}


class HomeCard(BaseModel):
    id: UUIDType
    title: str
    prompt: str
    status: str = "online"


class HomeCardCreate(BaseModel):
    title: str
    prompt: str
    status: str = "online"


class HomeCardSummary(BaseModel):
    title: str
    prompt: str
