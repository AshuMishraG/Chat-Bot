from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class IngredientCategory(BaseModel):
    primary: str = Field(
        ..., description="Primary category (base, mixer, additional, garnish)"
    )
    secondary: Optional[str] = Field(None, description="Sub-category")
    flavourTags: Optional[List[str]] = Field(
        default=[], description="Taste-related tags"
    )


class Ingredient(BaseModel):
    name: str
    quantity: float = Field(..., gt=0)
    unit: str
    category: Optional[IngredientCategory] = None
    optional: bool = False
    perishable: bool = False
    substitutes: List[str] = []
    notes: Optional[str] = None


class Image(BaseModel):
    url: HttpUrl
    alt: str = Field(..., max_length=200)
    photographer: Optional[str] = None


class Glassware(BaseModel):
    type: str
    chilled: bool = False
    size: Optional[str] = None
    notes: Optional[str] = None


class Recipe(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=50, max_length=1500)
    image: Optional[Image] = None
    ice: Optional[str] = None
    ingredients: List[Ingredient]
    instructions: List[str] = Field(
        ..., min_length=1, description="A list of steps to make the cocktail."
    )
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
    ] = Field(None, description="The primary technique used to mix the drink.")
    glassware: Glassware
    difficulty: Optional[Literal["easy", "moderate", "challenging", "expert"]] = Field(
        None, description="The difficulty level of the recipe."
    )
    preparationTime: Optional[int] = None
    totalTime: Optional[int] = None
    servingSize: Optional[int] = None
    tags: List[str] = []
    notes: Optional[str] = None
    source: Optional[str] = None
    variations: List[str] = []


class RecipeResponse(BaseModel):
    response: str
    recipes: List[Recipe] = []
