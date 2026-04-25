from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.models import ActionCard, FlatRecipe, Mixlist, Recipe


class ImageMetadata(BaseModel):
    source: Optional[Literal["camera", "gallery", "upload"]] = None
    timestamp: Optional[str] = None  # Assuming ISO 8601 string


class ImageInput(BaseModel):
    url: str = Field(
        ..., description="Base64 encoded image string, optionally as a Data URI."
    )
    metadata: Optional[ImageMetadata] = None


class DeviceMetadata(BaseModel):
    device_number: str = Field(..., description="Device number for Defteros lookup")
    connection_status: Optional[Literal["connected", "disconnected"]] = None


class UserInput(BaseModel):
    text: Optional[str] = None
    image: Optional[ImageInput] = None


class RequestMetadata(BaseModel):
    platform: Optional[Literal["web", "mobile", "backend", "demo_ui", "curl"]] = None
    app_version: Optional[str] = None
    language: Optional[str] = None
    device: Optional[DeviceMetadata] = None


class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    input: UserInput
    metadata: Optional[RequestMetadata] = None


class ChatBotData(BaseModel):
    recipes: List[Recipe] = []
    mixlists: List[Mixlist] = []


class ChatResponse(BaseModel):
    response: str
    recipes: List[FlatRecipe] = (
        []
    )  # Now contains flat recipes with indexed ingredient fields
    action_cards: List[ActionCard]
    chatbot: ChatBotData = Field(default_factory=ChatBotData)
    relevant_url: Optional[str] = None
    message_id: Optional[str] = Field(
        None, description="Unique message ID from conversation history"
    )


class ImageRequest(BaseModel):
    session_id: str
    image_url: str


class VectorSearchRequest(BaseModel):
    query: str


class FullRecipeRequest(BaseModel):
    """Request model for full recipe generation endpoint"""

    flat_recipe_json: dict[str, Any] = Field(
        ...,
        description="Flat recipe object with indexed ingredient fields to be converted to nested format (stored as JSONB)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "flat_recipe_json": {
                    "name": "Classic Margarita",
                    "description": "A refreshing tequila cocktail with lime and triple sec",
                    "no_ingredients": 3,
                    "ingredient_0": "Blanco Tequila",
                    "ingredient_type_0": "base",
                    "secondary_category_0": "tequila",
                    "perishable_0": False,
                    "quantity_0": "2 oz",
                    "ingredient_1": "Fresh Lime Juice",
                    "ingredient_type_1": "mixer",
                    "secondary_category_1": "citrus",
                    "perishable_1": True,
                    "quantity_1": "1 oz",
                    "ingredient_2": "Triple Sec",
                    "ingredient_type_2": "additional",
                    "secondary_category_2": "liqueur",
                    "perishable_2": False,
                    "quantity_2": "0.5 oz",
                    "full_recipe_id": "classic_margarita",
                }
            }
        }
    }


class FullRecipeResponse(BaseModel):
    """Response model for full recipe generation endpoint"""

    recipe: Optional[dict[str, Any]] = Field(
        None,
        description="Enriched recipe with nested ingredient structure and complete metadata",
    )
    response: str = Field(
        ...,
        description="Confirmation message about the recipe conversion",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "response": "Successfully converted Classic Margarita to full recipe format.",
                "recipe": {
                    "name": "Classic Margarita",
                    "description": "A timeless cocktail that balances tequila with bright citrus",
                    "ingredients": [
                        {
                            "name": "Blanco Tequila",
                            "quantity": 2,
                            "unit": "oz",
                            "category": {
                                "primary": "base",
                                "secondary": "tequila",
                                "flavourTags": ["agave", "crisp", "smooth"],
                            },
                            "optional": False,
                            "perishable": False,
                            "substitutes": ["Reposado Tequila", "Mezcal"],
                        }
                    ],
                    "instructions": [
                        "Rim glass with salt (optional)",
                        "Add all ingredients to shaker with ice",
                        "Shake vigorously for 10-15 seconds",
                        "Strain into prepared glass",
                    ],
                    "mixingTechnique": "shaken",
                    "glassware": {"type": "rocks", "chilled": True, "size": "standard"},
                    "difficulty": "easy",
                    "preparationTime": 3,
                    "totalTime": 3,
                    "servingSize": 1,
                    "tags": ["classic", "citrus", "tequila", "refreshing"],
                },
            }
        }
    }


class FeedbackMetadata(BaseModel):
    """Metadata for feedback requests"""

    platform: Optional[str] = Field(
        None, description="Platform: ios, android, web, etc."
    )
    appVersion: Optional[str] = Field(None, description="App version")
    model: Optional[str] = Field(None, description="AI model used")
    locale: Optional[str] = Field(None, description="User locale")
    conversationTurn: Optional[int] = Field(
        None, description="Turn number in the conversation"
    )


class PostFeedbackRequest(BaseModel):
    """Request model for posting user feedback on conversation messages"""

    sessionId: str = Field(..., description="Session ID of the conversation")
    messageId: str = Field(..., description="Message ID being rated")
    userId: str = Field(..., description="User ID providing the feedback")
    rating: Literal["thumbs_up", "thumbs_down"] = Field(
        ..., description="User rating: thumbs_up or thumbs_down"
    )
    reason: str = Field(..., description="Reason for the rating")
    comment: Optional[str] = Field(None, description="Additional user comment")
    timestamp: str = Field(..., description="Timestamp of feedback (ISO 8601)")
    branch: Optional[str] = Field(
        None, description="Branch identifier for feedback collection"
    )
    metadata: Optional[FeedbackMetadata] = Field(
        None, description="Additional metadata about the feedback context"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "sessionId": "conv_8f2c91",
                "messageId": "msg_ai_42",
                "userId": "user_12345",
                "rating": "thumbs_down",
                "reason": "incorrect",
                "comment": "It suggested an ingredient that doesn't exist.",
                "timestamp": "2026-02-03T14:23:02Z",
                "branch": "main",
                "metadata": {
                    "platform": "ios",
                    "appVersion": "1.4.2",
                    "model": "gpt-5.2",
                    "locale": "en-US",
                    "conversationTurn": 7,
                },
            }
        }
    }


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""

    success: bool = Field(
        ..., description="Whether the feedback was successfully posted"
    )
    message: str = Field(..., description="Response message")
    feedback_id: Optional[str] = Field(
        None, description="Database ID of the posted feedback"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Feedback posted successfully",
                "feedback_id": "a7f8b2c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
            }
        }
    }


class GetFeedbackResponse(BaseModel):
    """Response model for retrieving feedback by message_id"""

    success: bool = Field(..., description="Whether feedback was found")
    message: str = Field(..., description="Response message")
    feedback: Optional[dict] = Field(None, description="Feedback data if found")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Feedback found",
                "feedback": {
                    "feedback_id": "a7f8b2c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
                    "message_id": "9132c05b-afc3-4ffc-9919-7c74673fd075",
                    "session_id": "conv_8f2c91",
                    "user_id": "user_12345",
                    "rating": "thumbs_up",
                    "reason": "helpful",
                    "comment": "Great response!",
                    "conversation_turn": "5",
                    "branch": "main",
                    "locale": "en-US",
                    "app_version": "1.4.2",
                    "platform": "ios",
                    "created_at": "2026-02-07T09:29:01.742Z",
                },
            }
        }
    }
