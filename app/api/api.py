import base64
import binascii
import json
import logging
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

import requests
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_embeddings_db
from app.core.config import Settings, get_settings
from app.models.models import (
    HomeCard,
    HomeCardCreate,
    HomeCardSummary,
    StatusResponse,
    VisionResult,
)
from app.models.service_models import (
    ChatRequest,
    ChatResponse,
    FeedbackResponse,
    FullRecipeRequest,
    FullRecipeResponse,
    GetFeedbackResponse,
    ImageInput,
    ImageRequest,
    PostFeedbackRequest,
    VectorSearchRequest,
)
from app.services.chatbot_content_search_service import ChatBotContentSearchService
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.device_info_service import DeviceInfoService
from app.services.device_service import DeviceService
from app.services.image_cache_service import ImageCacheService
from app.services.ingredient_service import IngredientService
from app.services.memory_service import MemoryService
from app.services.vision_service import VisionService
from app.services.website_search_service import WebsiteSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_image_cache_service(db: Session = Depends(get_db)) -> ImageCacheService:
    return ImageCacheService(db=db)


def get_ingredient_service() -> IngredientService:
    return IngredientService()


def get_memory_service(
    db: Session = Depends(get_db),
    ingredient_service: IngredientService = Depends(get_ingredient_service),
) -> MemoryService:
    return MemoryService(db=db, ingredient_service=ingredient_service)


def get_chatbot_content_search_service(
    db: Session = Depends(get_embeddings_db),
) -> ChatBotContentSearchService:
    return ChatBotContentSearchService(db=db)


def get_website_search_service(db: Session = Depends(get_db)) -> WebsiteSearchService:
    return WebsiteSearchService(db=db)


def get_device_service() -> DeviceService:
    return DeviceService()


def get_vision_service(
    image_cache_service: ImageCacheService = Depends(get_image_cache_service),
    ingredient_service: IngredientService = Depends(
        get_ingredient_service
    ),  # Added ingredient_service dependency
) -> VisionService:
    return VisionService(
        image_cache_service=image_cache_service,
        ingredient_service=ingredient_service,  # Pass ingredient_service
    )


def get_device_info_service(db: Session = Depends(get_db)) -> DeviceInfoService:
    return DeviceInfoService(db=db)


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    return ConversationService(db=db)


def get_chat_service(
    vision_service: VisionService = Depends(get_vision_service),
    memory_service: MemoryService = Depends(get_memory_service),
    chatbot_content_search_service: ChatBotContentSearchService = Depends(
        get_chatbot_content_search_service
    ),
    website_search_service: WebsiteSearchService = Depends(get_website_search_service),
    device_info_service: DeviceInfoService = Depends(get_device_info_service),
    device_service: DeviceService = Depends(get_device_service),
    ingredient_service: IngredientService = Depends(get_ingredient_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return ChatService(
        vision_service=vision_service,
        memory_service=memory_service,
        device_info_service=device_info_service,
        device_service=device_service,
        ingredient_service=ingredient_service,
        chatbot_content_search_service=chatbot_content_search_service,
        website_search_service=website_search_service,
        conversation_service=conversation_service,
        settings=settings,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    multi: str = "on",
    x_user_id: Optional[str] = Header(None, alias="x-user-id"),
    x_user_session_id: Optional[str] = Header(None, alias="x-user-session-id"),
    chat_service: ChatService = Depends(get_chat_service),
    db: Session = Depends(get_db),
):
    # Preserves compatibility: accept `multi` param just in case.
    # If user_id or session_id are not provided in the request body, try to get them from headers
    if not request.user_id and x_user_id:
        request.user_id = x_user_id
    if not request.session_id and x_user_session_id:
        request.session_id = x_user_session_id

    # Validate that user_id and session_id are now present
    if not request.user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id is required, either in body or x-user-id header.",
        )
    if not request.session_id:
        raise HTTPException(
            status_code=400,
            detail="session_id is required, either in body or x-user-session-id header.",
        )

    if not request.input.text and not request.input.image:
        raise HTTPException(
            status_code=400, detail="Please provide a message or an image."
        )

    response = await chat_service.handle_chat_request(request)
    db.commit()  # Commit all changes made during the request
    return response


@router.post("/image", response_model=VisionResult)
async def analyze_image(
    request: ImageRequest,
    vision_service: VisionService = Depends(get_vision_service),
    db: Session = Depends(get_db),
):
    """
    Analyzes a single image provided via URL or base64 data.
    """
    encoded_image_str = request.image_url
    media_type = "image/jpeg"
    image_data: bytes

    # --- Refactored to handle getting raw image_data for caching ---
    if encoded_image_str.startswith("http"):
        try:
            response = requests.get(encoded_image_str, timeout=10)
            response.raise_for_status()
            image_data = response.content
            media_type = response.headers.get("Content-Type", "image/jpeg")
        except requests.RequestException as e:
            raise HTTPException(
                status_code=400, detail=f"Unable to download image: {e}"
            )

    elif encoded_image_str.startswith("data:image/"):
        header, encoded_data = encoded_image_str.split(",", 1)
        media_type = header.split(";")[0].split(":")[1]
        image_data = base64.b64decode(encoded_data)
    else:
        # Assuming raw base64 if no prefix
        try:
            image_data = base64.b64decode(encoded_image_str)
        except (binascii.Error, TypeError):
            raise HTTPException(status_code=400, detail="Invalid base64 image data.")

    # Re-create the data URI from the validated raw bytes to ensure consistency
    data_uri = (
        f"data:{media_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
    )

    # Pass the necessary data to the vision service
    result = await vision_service.analyze_image(
        ImageInput(url=data_uri), image_data, media_type
    )
    db.commit()  # Commit potential cache updates
    return result


@router.post("/image/multipart", response_model=List[VisionResult])
async def analyze_multiple_images(
    session_id: str = Form(...),
    image: List[UploadFile] = File(...),
    vision_service: VisionService = Depends(get_vision_service),
    db: Session = Depends(get_db),
):
    """
    Analyzes multiple images uploaded via multipart/form-data.
    """
    SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
    results = []

    for img_file in image:
        if (
            not img_file.content_type
            or img_file.content_type not in SUPPORTED_IMAGE_TYPES
        ):
            continue

        content = await img_file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            continue

        media_type = img_file.content_type
        encoded_image = base64.b64encode(content).decode("utf-8")
        data_uri = f"data:{media_type};base64,{encoded_image}"

        # Pass the raw content and media type to the service for caching
        result = await vision_service.analyze_image(
            ImageInput(url=data_uri), content, media_type
        )
        results.append(result)

    db.commit()  # Commit all cache updates from the loop
    return results


from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.core.config import get_settings

# --- Cache API ---
# --- Test Endpoints ---
# TODO: Move these to a separate file
# TODO: Decide which ones to keep and then use the ImageCacheService
from app.core.db.models import HomeCardDB, ImageCache


@router.delete("/cache/old")
async def clear_old_cache(days: int = 30, db: Session = Depends(get_db)):
    """Clear cache entries older than specified days"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get old entries
        old_entries = (
            db.query(ImageCache).filter(ImageCache.last_accessed < cutoff_date).all()
        )

        # Delete old entries
        deleted_count = (
            db.query(ImageCache).filter(ImageCache.last_accessed < cutoff_date).delete()
        )

        db.commit()

        return {
            "message": f"Cleared cache entries older than {days} days",
            "deleted_images": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error clearing old cache: {str(e)}"
        )


@router.get("/cache/search")
async def search_cache(
    image_format: Optional[str] = None,
    min_confidence: Optional[float] = None,
    min_access_count: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Search cache entries with filters"""
    try:
        query = db.query(ImageCache)

        if image_format:
            query = query.filter(ImageCache.image_format == image_format)

        if min_confidence is not None:
            query = query.filter(ImageCache.analysis_confidence >= min_confidence)

        if min_access_count is not None:
            query = query.filter(ImageCache.access_count >= min_access_count)

        results = query.order_by(ImageCache.last_accessed.desc()).limit(100).all()

        return {
            "results": [
                {
                    "id": img.id,
                    "perceptual_hash": img.perceptual_hash,
                    "image_format": img.image_format,
                    "file_size_mb": round(img.file_size / (1024 * 1024), 2),  # type: ignore
                    "analysis_confidence": img.analysis_confidence,
                    "access_count": img.access_count,
                    "last_accessed": img.last_accessed.isoformat(),
                    "created_at": img.created_at.isoformat(),
                    "ingredients_count": len(img.ingredients) if img.ingredients else 0,  # type: ignore
                }
                for img in results
            ],
            "total_found": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching cache: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats(db: Session = Depends(get_db)):
    """Get cache statistics"""
    try:
        # Get total cached images
        total_images = db.query(func.count(ImageCache.id)).scalar()

        # Get cache hit rate (approximate)
        total_accesses = db.query(func.sum(ImageCache.access_count)).scalar() or 0

        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_accesses = (
            db.query(ImageCache).filter(ImageCache.last_accessed >= yesterday).count()
        )

        # Get most accessed images
        top_images = (
            db.query(ImageCache)
            .order_by(ImageCache.access_count.desc())
            .limit(10)
            .all()
        )

        # Get cache size in bytes
        total_size = db.query(func.sum(ImageCache.file_size)).scalar() or 0

        return {
            "total_cached_images": total_images,
            "total_accesses": total_accesses,
            "recent_accesses_24h": recent_accesses,
            "total_cache_size_bytes": total_size,
            "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_enabled": get_settings().image_cache_enabled,
            "hash_threshold": get_settings().hash_threshold,
            "top_accessed_images": [
                {
                    "id": img.id,
                    "access_count": img.access_count,
                    "last_accessed": img.last_accessed.isoformat(),
                    "image_format": img.image_format,
                    "file_size_mb": round(img.file_size / (1024 * 1024), 2),  # type: ignore
                }
                for img in top_images
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting cache stats: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache(db: Session = Depends(get_db)):
    """Clear all cached images"""
    try:
        # Clear database cache
        deleted_count = db.query(ImageCache).delete()
        db.commit()

        return {
            "message": "Cache cleared successfully",
            "deleted_images": deleted_count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


# --- Session API ---


@router.get("/user/{user_id}/sessions")
async def list_user_sessions(
    user_id: str, memory_service: MemoryService = Depends(get_memory_service)
):
    """
    List all session ids (conversations) for a given user.
    """
    sessions = memory_service.list_sessions_for_user(user_id)
    return {"user_id": user_id, "sessions": sessions}


@router.get("/session/{session_id}/history")
async def session_history(
    session_id: str, memory_service: MemoryService = Depends(get_memory_service)
):
    """
    Returns the full message history for a session, formatted for UI replay.
    This endpoint normalizes complex 'tool-call' messages into a simple text
    format for easy rendering in the UI.
    """
    history_dicts = memory_service.get_full_session_history_as_dicts(
        session_id=session_id
    )

    if not history_dicts:
        raise HTTPException(
            status_code=404, detail="No history found for this session ID."
        )

    processed_history = []
    for msg_dict in history_dicts:
        # Check if this message is a response with a tool call that needs simplifying for the UI
        parts = msg_dict.get("parts", [])
        if (
            msg_dict.get("kind") == "response"
            and parts
            and isinstance(parts, list)
            and len(parts) > 0
        ):

            first_part = parts[0]
            if (
                isinstance(first_part, dict)
                and first_part.get("part_kind") == "tool-call"
                and first_part.get("tool_name") == "final_result"
            ):

                try:
                    # The 'args' field is already a dictionary because the DB driver
                    # deserialized the JSON column upon retrieval.
                    args_data = first_part.get("args", {})
                    # Ensure args_data is a dict before proceeding
                    if not isinstance(args_data, dict):
                        # If args was a string for some reason, try to load it
                        args_data = json.loads(args_data or "{}")

                    response_text = args_data.get("data", {}).get("response", "")

                    if response_text:
                        # Create a new, simplified message dictionary for the UI
                        simplified_msg_dict = msg_dict.copy()  # Start with a copy
                        simplified_msg_dict["parts"] = [
                            {
                                "content": response_text,
                                "part_kind": "text",  # This is a simple kind the UI can always render
                            }
                        ]
                        # Add action cards if they exist on the original message
                        if "action_cards" in msg_dict:
                            simplified_msg_dict["action_cards"] = msg_dict[
                                "action_cards"
                            ]

                        processed_history.append(simplified_msg_dict)
                        continue  # Skip to the next message in the history loop
                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                    logger.warning(
                        f"Could not normalize tool-call message, falling back to original. Error: {e}"
                    )
                    # If parsing fails for any reason, fall back to adding the original complex message
                    pass

        # If the message doesn't need normalization, or if normalization fails, add it as is.
        processed_history.append(msg_dict)

    return {"session_id": session_id, "history": processed_history}


@router.get("/analytics/user/{user_id}/sessions")
async def list_conversation_sessions(
    user_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    List all conversation session ids for a given user for analytics.
    """
    sessions = conversation_service.list_conversation_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions}


@router.get("/analytics/session/{session_id}/messages")
async def get_conversation_messages(
    session_id: str,
    limit: int = 100,  # Default limit for pagination
    offset: int = 0,  # Default offset for pagination
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """
    Returns the full conversation messages for a session for analytics.
    """
    messages_data = conversation_service.get_conversation_messages(
        session_id, limit, offset
    )
    messages = messages_data["messages"]
    total_messages = messages_data["total_messages"]

    if not messages:
        return {
            "session_id": None,
            "user_id": None,
            "total_messages": 0,
            "messages": [],
        }

    # Extracts and displays user_id and session_id once
    user_id = messages[0].get("user_id") if isinstance(messages, list) else None
    sanitized_messages = [
        {k: v for k, v in msg.items() if k not in ("session_id", "user_id")}
        for msg in messages
    ]
    sanitized_messages.reverse()

    return {
        "session_id": session_id,
        "user_id": user_id,
        "total_messages": total_messages,
        "messages": sanitized_messages,
    }


# --- Status API ---


@router.get("/status", response_model=StatusResponse)
async def status():
    return StatusResponse(status="ok", message="Shaken not stirred")


# --- Home Card API ---


@router.post("/home-cards", response_model=List[HomeCard])
def replace_home_cards(cards: List[HomeCardCreate], db: Session = Depends(get_db)):
    logger.info("POST /home-cards endpoint called to replace all cards")
    logger.debug(f"Received {len(cards)} new cards to insert")

    try:
        logger.debug("Deleting existing HomeCardDB records")
        db.query(HomeCardDB).delete()

        # Step 2: Add new cards
        for idx, card in enumerate(cards):
            try:
                db_card = HomeCardDB(
                    title=card.title,
                    prompt=card.prompt,
                    status=(card.status == "online"),
                )
                db.add(db_card)
                logger.debug(f"Queued card {idx + 1}: {card.title}")
            except Exception as e:
                logger.error(f"Failed to construct DB object for card {idx + 1}: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid data for card {idx + 1}: {e}",
                )

        # Step 3: Commit all changes
        db.commit()
        logger.info("Successfully committed new card list")

    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error during card replacement. Rolled back transaction."
        )
        raise HTTPException(status_code=500, detail="Unexpected error occurred")

    # Step 4: Fetch and return updated card list
    try:
        new_cards = db.query(HomeCardDB).order_by(HomeCardDB.created_at).all()
        logger.info(f"Returning {len(new_cards)} newly inserted cards")
        return [
            HomeCard(
                id=getattr(card, "id"),
                title=getattr(card, "title"),
                prompt=getattr(card, "prompt"),
                status="online" if getattr(card, "status") else "offline",
            )
            for card in new_cards
        ]
    except Exception as e:
        logger.exception("Failed to fetch or serialize newly inserted cards")
        raise HTTPException(
            status_code=500, detail="Failed to return newly inserted cards"
        )


@router.get(
    "/home-cards",
    response_model=Union[List[HomeCard], List[HomeCardSummary]],
    summary="Get home cards",
)
def get_home_cards(status: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Retrieves home cards.
    - By default (no query parameter), returns all cards for the admin view.
    - If `status=online`, returns a summary of only online cards for the client view.
    """
    if status == "online":
        try:
            logger.debug("Querying HomeCardDB for summaries of online cards")
            cards = (
                db.query(HomeCardDB)
                .filter(HomeCardDB.status == True)
                .order_by(HomeCardDB.created_at)
                .all()
            )
            logger.info(f"Retrieved {len(cards)} online card summaries from database")
            return [
                HomeCardSummary(
                    title=getattr(card, "title"), prompt=getattr(card, "prompt")
                )
                for card in cards
            ]
        except Exception as e:
            logger.exception("Database query failed for online home card summaries")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve online home card summaries"
            )

    # Default admin view: return all cards
    try:
        logger.debug("Querying HomeCardDB for all cards (admin view)")
        cards = db.query(HomeCardDB).order_by(HomeCardDB.created_at).all()
        logger.info(f"Retrieved {len(cards)} cards (including offline) from database")
    except Exception as e:
        logger.exception("Database query failed for admin home cards")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve admin home cards"
        )

    result = []
    for card in cards:
        try:
            home_card = HomeCard(
                id=getattr(card, "id"),
                title=getattr(card, "title"),
                prompt=getattr(card, "prompt"),
                status="online" if getattr(card, "status") else "offline",
            )
            result.append(home_card)
        except Exception as e:
            logger.error(
                f"Error converting card ID {getattr(card, 'id', 'UNKNOWN')} to HomeCard: {e}"
            )
            continue

    logger.info("Successfully processed all admin home cards")
    return result


@router.get("/hardware/context/{device_number}")
async def get_hardware_context(
    device_number: str,
    device_service: DeviceService = Depends(get_device_service),
):
    """
    Get hardware connection context for a specific device.
    This endpoint provides comprehensive device information including station ingredients
    by integrating with the defteros-service API.
    """
    try:
        # The service expects an object with a .device_number attribute.
        device_metadata = SimpleNamespace(device_number=device_number)
        context = await device_service.get_device_context(device_metadata)
        return {"device_number": device_number, "context": context, "success": True}
    except Exception as e:
        logger.error(f"Error getting hardware context for device {device_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get hardware context for device {device_number}",
        )


@router.post("/vector_search")
async def vector_search(request: VectorSearchRequest, db: Session = Depends(get_db)):
    from scripts.vector_search import vector_search_logic

    results = await vector_search_logic(request.query)
    if not results:
        raise HTTPException(status_code=404, detail="No similar recipe found.")

    # results is a list of (RecipeEmbeddings, distance) tuples
    return [
        {
            "recipe_id": recipe.recipe_id,
            "recipe_summary": recipe.recipe_summary,
            "similarity": 1 - distance,
        }
        for recipe, distance in results
    ]


@router.post("/get_full_recipe", response_model=FullRecipeResponse)
async def generate_full_recipe(
    request: FullRecipeRequest,
) -> FullRecipeResponse:
    """
    Convert a flat recipe to a full nested recipe format.

    Args:
        request: Request containing flat recipe object with indexed ingredient fields

    Returns:
        FullRecipeResponse with enriched recipe in nested format and confirmation message

    Raises:
        HTTPException: 500 if conversion fails
    """
    from app.agents.spec import AGENTS, AgentName

    try:
        # Use the flat recipe dict directly (no parsing needed)
        flat_recipe_dict = request.flat_recipe_json
        recipe_name = flat_recipe_dict.get("name", "Unknown Recipe")

        logger.info(f"Converting flat recipe to nested format: {recipe_name}")

        # Pass the flat recipe as a user message to the agent
        # Note: The instruction text helps the LLM understand context
        # indent=2 makes logs readable at minimal token cost (~20 extra tokens)
        user_message = f"Please convert this flat recipe to full nested format:\n\n{json.dumps(flat_recipe_dict, indent=2)}"
        result = await AGENTS[AgentName.FULL_RECIPE].run(user_message)

        # Extract the recipe from the envelope
        envelope = result.output
        payload = envelope.data

        # Return the generated nested recipe
        return FullRecipeResponse(
            recipe=payload.recipe.model_dump() if payload.recipe else None,
            response=payload.response,
        )
    except Exception as e:
        logger.error(f"Error converting flat recipe to nested: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to convert recipe")


@router.post("/post_feedback")
async def post_feedback(
    request: PostFeedbackRequest,
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """
    endpoint to post feedback about conversation messages

    Args:
        request: Request contain message ID along with user feedback attributes like rating, remarks etc.
            - rating: "thumbs_up" or "thumbs_down"
            - reason: One of: accurate, helpful, complete, incorrect, irrelevant,
                      too_short, too_long, incomplete, unsafe, other

    Returns:
        FeedbackResponse with success status and feedback_id

    Raises:
        HTTPException: 400 if messageId is invalid UUID
        HTTPException: 404 if messageId does not exist in conversation_messages
        HTTPException: 409 if feedback already exists for this message
        HTTPException: 500 if feedback posting fails
    """
    from uuid import UUID

    from app.core.db.models import ChatBotFeedback, ConversationMessages

    try:
        # Validate and parse messageId as UUID
        try:
            message_uuid = UUID(request.messageId)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid UUID format for message_id: {request.messageId}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid messageId format. Must be a valid UUID.",
            )

        # Verify that the message_id exists in conversation_messages table
        message_exists = (
            db.query(ConversationMessages)
            .filter(ConversationMessages.id == message_uuid)
            .first()
        )

        if not message_exists:
            logger.warning(f"Message not found: {request.messageId}")
            raise HTTPException(
                status_code=404,
                detail=f"Message with ID {request.messageId} not found",
            )

        # Check if feedback already exists for this message_id
        existing_feedback = (
            db.query(ChatBotFeedback)
            .filter(ChatBotFeedback.message_id == message_uuid)
            .first()
        )

        if existing_feedback:
            logger.info(f"Feedback already exists for message_id: {request.messageId}")
            raise HTTPException(
                status_code=409,
                detail=f"Feedback already exists for message {request.messageId}",
            )

        # Extract conversation turn from metadata if available
        conversation_turn = None
        if request.metadata and request.metadata.conversationTurn is not None:
            conversation_turn = str(request.metadata.conversationTurn)

        # Create new feedback entry
        new_feedback = ChatBotFeedback(
            message_id=message_uuid,
            comment=request.comment,
            session_id=request.sessionId,
            user_id=request.userId,
            rating=request.rating,
            reason=request.reason,
            conversation_turn=conversation_turn,
            branch=request.branch,
        )

        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)

        logger.info(f"Feedback posted successfully for message_id: {request.messageId}")
        return FeedbackResponse(
            success=True,
            message="Feedback posted successfully",
            feedback_id=str(new_feedback.id),
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 400 for invalid UUID)
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error posting feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to post feedback",
        )


@router.get("/get_feedback/{message_id}")
async def get_feedback(
    message_id: str,
    db: Session = Depends(get_db),
) -> GetFeedbackResponse:
    """
    Endpoint to retrieve feedback for a specific message ID

    Args:
        message_id: The UUID of the message to get feedback for

    Returns:
        GetFeedbackResponse with feedback data if found

    Raises:
        HTTPException: 400 if message_id is invalid UUID
        HTTPException: 500 if retrieval fails
    """
    from uuid import UUID

    from app.core.db.models import ChatBotFeedback

    try:
        # Validate and parse message_id as UUID
        try:
            message_uuid = UUID(message_id)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid UUID format for message_id: {message_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid message_id format. Must be a valid UUID.",
            )

        # Query feedback by message_id
        feedback = (
            db.query(ChatBotFeedback)
            .filter(ChatBotFeedback.message_id == message_uuid)
            .first()
        )

        if not feedback:
            logger.info(f"No feedback found for message_id: {message_id}")
            return GetFeedbackResponse(
                success=False,
                message="No feedback found for this message",
                feedback=None,
            )

        # Build feedback response data
        feedback_data = {
            "feedback_id": str(feedback.id),
            "message_id": str(feedback.message_id),
            "session_id": feedback.session_id,
            "user_id": feedback.user_id,
            "rating": feedback.rating,
            "reason": feedback.reason,
            "comment": feedback.comment,
            "conversation_turn": feedback.conversation_turn,
            "branch": feedback.branch,
            "locale": feedback.locale,
            "app_version": feedback.app_version,
            "platform": feedback.platform,
            "created_at": (
                feedback.created_at.isoformat() if feedback.created_at else None
            ),
        }

        logger.info(f"Feedback found for message_id: {message_id}")
        return GetFeedbackResponse(
            success=True,
            message="Feedback found",
            feedback=feedback_data,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 400 for invalid UUID)
        raise
    except Exception as e:
        logger.error(f"Error retrieving feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feedback",
        )


@router.get("/feedback/stats")
async def get_feedback_stats(db: Session = Depends(get_db)):
    """Get feedback statistics for dashboard"""
    from datetime import datetime, timedelta, timezone

    from app.core.db.models import ChatBotFeedback

    try:
        # Total feedback
        total_feedback = db.query(func.count(ChatBotFeedback.id)).scalar() or 0

        # Thumbs up/down counts
        thumbs_up = (
            db.query(func.count(ChatBotFeedback.id))
            .filter(ChatBotFeedback.rating == "thumbs_up")
            .scalar()
            or 0
        )

        thumbs_down = (
            db.query(func.count(ChatBotFeedback.id))
            .filter(ChatBotFeedback.rating == "thumbs_down")
            .scalar()
            or 0
        )

        # Ratio
        thumbs_up_ratio = (
            (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0
        )

        # Unique users
        unique_users = (
            db.query(func.count(func.distinct(ChatBotFeedback.user_id))).scalar() or 0
        )

        # Recent feedback (24h)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_feedback = (
            db.query(func.count(ChatBotFeedback.id))
            .filter(ChatBotFeedback.created_at >= yesterday)
            .scalar()
            or 0
        )

        # Feedback by branch
        branch_stats = (
            db.query(ChatBotFeedback.branch, func.count(ChatBotFeedback.id).label("count"))
            .group_by(ChatBotFeedback.branch)
            .all()
        )

        # Feedback by reason
        reason_stats = (
            db.query(ChatBotFeedback.reason, func.count(ChatBotFeedback.id).label("count"))
            .group_by(ChatBotFeedback.reason)
            .all()
        )

        # Feedback by platform
        platform_stats = (
            db.query(ChatBotFeedback.platform, func.count(ChatBotFeedback.id).label("count"))
            .group_by(ChatBotFeedback.platform)
            .all()
        )

        return {
            "total_feedback": total_feedback,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "thumbs_up_ratio": round(thumbs_up_ratio, 1),
            "unique_users": unique_users,
            "recent_feedback_24h": recent_feedback,
            "branch_stats": [
                {"branch": b or "unknown", "count": c} for b, c in branch_stats
            ],
            "reason_stats": [
                {"reason": r or "unknown", "count": c} for r, c in reason_stats
            ],
            "platform_stats": [
                {"platform": p or "unknown", "count": c} for p, c in platform_stats
            ],
        }

    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get feedback stats")


@router.get("/feedback/search")
async def search_feedback(
    rating: Optional[str] = None,
    reason: Optional[str] = None,
    branch: Optional[str] = None,
    platform: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    has_comment: Optional[bool] = None,
    date_from: Optional[str] = None,  # ISO format: 2026-02-01
    date_to: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Search and filter feedback with pagination"""
    from datetime import datetime

    from app.core.db.models import ChatBotFeedback

    try:
        query = db.query(ChatBotFeedback)

        # Apply filters
        if rating:
            query = query.filter(ChatBotFeedback.rating == rating)

        if reason:
            query = query.filter(ChatBotFeedback.reason == reason)

        if branch:
            query = query.filter(ChatBotFeedback.branch == branch)

        if platform:
            query = query.filter(ChatBotFeedback.platform == platform)

        if user_id:
            query = query.filter(ChatBotFeedback.user_id.ilike(f"%{user_id}%"))

        if session_id:
            query = query.filter(ChatBotFeedback.session_id.ilike(f"%{session_id}%"))

        if has_comment:
            query = query.filter(ChatBotFeedback.comment.isnot(None))
            query = query.filter(ChatBotFeedback.comment != "")

        if date_from:
            date_from_obj = datetime.fromisoformat(date_from)
            query = query.filter(ChatBotFeedback.created_at >= date_from_obj)

        if date_to:
            date_to_obj = datetime.fromisoformat(date_to)
            query = query.filter(ChatBotFeedback.created_at <= date_to_obj)

        # Get total count before pagination
        total_count = query.count()

        # Order by created_at desc (most recent first)
        query = query.order_by(ChatBotFeedback.created_at.desc())

        # Paginate
        results = query.limit(limit).offset(offset).all()

        # Format results
        feedback_list = []
        for feedback in results:
            feedback_list.append(
                {
                    "id": str(feedback.id),
                    "message_id": str(feedback.message_id),
                    "session_id": feedback.session_id,
                    "user_id": feedback.user_id,
                    "rating": feedback.rating,
                    "reason": feedback.reason,
                    "comment": feedback.comment,
                    "conversation_turn": feedback.conversation_turn,
                    "branch": feedback.branch,
                    "locale": feedback.locale,
                    "app_version": feedback.app_version,
                    "platform": feedback.platform,
                    "created_at": (
                        feedback.created_at.isoformat() if feedback.created_at else None
                    ),
                }
            )

        return {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "results": feedback_list,
        }

    except Exception as e:
        logger.error(f"Error searching feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search feedback")


@router.get("/feedback/export")
async def export_feedback_csv(
    rating: Optional[str] = None,
    reason: Optional[str] = None,
    branch: Optional[str] = None,
    platform: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export feedback as CSV for analytics"""
    import csv
    import io
    from datetime import datetime

    from fastapi.responses import StreamingResponse
    from app.core.db.models import ChatBotFeedback

    try:

        query = db.query(ChatBotFeedback)

        # Apply same filters as search
        if rating:
            query = query.filter(ChatBotFeedback.rating == rating)
        if reason:
            query = query.filter(ChatBotFeedback.reason == reason)
        if branch:
            query = query.filter(ChatBotFeedback.branch == branch)
        if platform:
            query = query.filter(ChatBotFeedback.platform == platform)
        if date_from:
            query = query.filter(
                ChatBotFeedback.created_at >= datetime.fromisoformat(date_from)
            )
        if date_to:
            query = query.filter(
                ChatBotFeedback.created_at <= datetime.fromisoformat(date_to)
            )

        results = query.order_by(ChatBotFeedback.created_at.desc()).all()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "ID",
                "Message ID",
                "Session ID",
                "User ID",
                "Rating",
                "Reason",
                "Comment",
                "Conversation Turn",
                "Branch",
                "Locale",
                "App Version",
                "Platform",
                "Created At",
            ]
        )

        # Write data
        for feedback in results:
            writer.writerow(
                [
                    str(feedback.id),
                    str(feedback.message_id),
                    feedback.session_id,
                    feedback.user_id,
                    feedback.rating,
                    feedback.reason or "",
                    feedback.comment or "",
                    feedback.conversation_turn or "",
                    feedback.branch or "",
                    feedback.locale or "",
                    feedback.app_version or "",
                    feedback.platform or "",
                    feedback.created_at.isoformat() if feedback.created_at else "",
                ]
            )

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=feedback_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            },
        )

    except Exception as e:
        logger.error(f"Error exporting feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export feedback")
        
