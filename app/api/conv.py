import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.agents.prompts import SINGLE_RECIPE_AGENT_PROMPT
from app.agents.spec import Envelope, gemini_model
from app.core.logtools import log_execution_time
from app.models.models import Glassware, Ingredient, IngredientCategory, Recipe
from app.models.service_models import ActionCard, ChatBotData, ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter()


class FlatIngredient(BaseModel):
    name: str
    quantity: float = Field(..., gt=0)
    unit: str
    category_primary: str = Field(
        ..., description="Primary category (base, mixer, additional, garnish)"
    )
    category_secondary: Optional[str] = Field(None, description="Sub-category")
    category_flavour_tags: Optional[List[str]] = Field(
        default=[], description="Taste-related tags"
    )
    optional: bool = False
    perishable: bool = False
    substitutes: List[str] = []
    notes: Optional[str] = None


class FlatRecipe(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1500)
    #    image: Optional[Image] = None
    ice: Optional[str] = None
    ingredients: List[FlatIngredient]
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
    glassware_type: str
    glassware_chilled: bool = False
    glassware_size: Optional[str] = None
    glassware_notes: Optional[str] = None
    difficulty: Optional[Literal["easy", "moderate", "challenging", "expert"]] = None
    preparationTime: Optional[int] = None
    totalTime: Optional[int] = None
    servingSize: Optional[int] = None
    tags: List[str] = []
    notes: Optional[str] = None
    source: Optional[str] = None
    variations: List[str] = []
    author: Optional[Dict[str, Any]] = None
    # chatbot_360_compatible: bool = False
    # deprecated_id: Optional[int] = None
    # created_at: Optional[datetime] = None
    # updated_at: Optional[datetime] = None


class SingleRecipeAgentResponse(BaseModel):
    response: str
    recipe: List[FlatRecipe]


def convert_flat_to_nested_recipe(flat_recipe: FlatRecipe) -> Recipe:
    nested_glassware = Glassware(
        type=flat_recipe.glassware_type,
        chilled=flat_recipe.glassware_chilled,
        size=flat_recipe.glassware_size,
        notes=flat_recipe.glassware_notes,
    )

    nested_ingredients = [
        Ingredient(
            name=ing.name,
            quantity=ing.quantity,
            unit=ing.unit,
            optional=ing.optional,
            perishable=ing.perishable,
            substitutes=ing.substitutes,
            notes=ing.notes,
            category=IngredientCategory(
                primary=ing.category_primary,
                secondary=ing.category_secondary,
                flavourTags=ing.category_flavour_tags,
            ),
        )
        for ing in flat_recipe.ingredients
    ]

    recipe_data = flat_recipe.model_dump()

    for key in list(recipe_data.keys()):
        if key.startswith("glassware_"):
            recipe_data.pop(key)

    # Update with the newly created nested objects
    recipe_data["glassware"] = nested_glassware
    recipe_data["ingredients"] = nested_ingredients

    return Recipe(**recipe_data)


class ChatResponse(BaseModel):
    response: str
    recipes: List[Recipe] = []
    action_cards: List[ActionCard]
    chatbot: ChatBotData = Field(default_factory=ChatBotData)


@router.post("/conv", response_model=ChatResponse)
async def conv(request: ChatRequest):
    if request.input.text:
        user_message: str = (request.input.text or "").strip()
    else:
        user_message = ""
    agent = Agent(
        # model="openai:gpt-4o",
        model=gemini_model,
        output_type=Envelope[SingleRecipeAgentResponse],
        system_prompt=SINGLE_RECIPE_AGENT_PROMPT,
        name="single_recipe",
        retries=3,
    )
    with log_execution_time("Complete back and forth with agent"):
        agent_result = await agent.run(user_message)
    envelope = agent_result.output
    payload = envelope.data
    response_text: str = getattr(payload, "response", "")
    recipes: List[FlatRecipe] = getattr(payload, "recipe", [])
    logger.info(f"There are {len(recipes)} recipes")

    return ChatResponse(
        response=response_text,
        recipes=[convert_flat_to_nested_recipe(recipe) for recipe in recipes],
        action_cards=[],
        chatbot=ChatBotData(
            recipes=[],
            mixlists=[],
        ),
    )


@router.post("/conv_nested", response_model=ChatResponse)
async def conv_nested(request: ChatRequest):
    if request.input.text:
        user_message: str = (request.input.text or "").strip()
    else:
        user_message = ""

    from app.agents.prompts import RECIPE_AGENT_PROMPT
    from app.models.models import RecipeAgentResponse

    agent = Agent(
        # model="openai:gpt-4o",
        model=gemini_model,
        output_type=Envelope[RecipeAgentResponse],
        system_prompt=RECIPE_AGENT_PROMPT,
        name="recipe",
        retries=3,
    )
    with log_execution_time("Complete back and forth with agent"):
        agent_result = await agent.run(user_message)
    envelope = agent_result.output
    payload = envelope.data
    response_text: str = getattr(payload, "response", "")
    recipes: List[Recipe] = getattr(payload, "recipes", [])
    logger.info(f"There are {len(recipes)} recipes")
    return ChatResponse(
        response=response_text,
        recipes=recipes,
        action_cards=[],
        chatbot=ChatBotData(
            recipes=[],
            mixlists=[],
        ),
    )
