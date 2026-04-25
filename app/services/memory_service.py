import logging
from typing import Any, Dict, List, cast

from pydantic_ai.messages import ModelMessage, ModelRequest, SystemPromptPart
from sqlalchemy import asc, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.agents.spec import AGENT_SPECS, AgentName
from app.core.db.models import Messages
from app.services.ingredient_service import IngredientService

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, db: Session, ingredient_service: IngredientService):
        """
        The service is initialized with a database session.
        It now handles data as flexible dictionaries to support custom fields.
        """
        self.db = db
        self.ingredient_service = ingredient_service

    def get_history_as_dicts(
        self,
        user_id: str,
        session_id: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves message history as a list of dictionaries, limited by number of turns.
        """
        try:
            stmt = (
                select(Messages.message_history)
                .where(
                    Messages.user_id == user_id,
                    Messages.session_id == session_id,
                )
                .order_by(desc(Messages.created_at))
            )
            turns_result = self.db.execute(stmt).scalars().all()
            turns = cast(List[List[Dict[str, Any]]], turns_result or [])
        except SQLAlchemyError:
            logger.exception("get_history failed for %s/%s", user_id, session_id)
            return []

        # Only keep the last `limit` turns (in correct order)
        selected_turns = list(reversed(turns[:limit]))
        collected: List[Dict[str, Any]] = []
        for turn in selected_turns:
            collected.extend(turn)

        return collected

    def append_history_as_dicts(
        self,
        user_id: str,
        session_id: str,
        msgs_as_dicts: List[Dict[str, Any]],
    ) -> None:
        """
        Appends a list of message dictionaries to the history for a single turn.
        """
        if not msgs_as_dicts:
            return
        try:
            self.db.add(
                Messages(
                    user_id=user_id,
                    session_id=session_id,
                    message_history=msgs_as_dicts,
                )
            )
        except SQLAlchemyError:
            logger.exception(
                "append_message_to_history failed for %s/%s", user_id, session_id
            )

    def get_full_session_history_as_dicts(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the complete, ordered message history for a session as dicts.
        """
        try:
            stmt = (
                select(Messages.message_history)
                .where(Messages.session_id == session_id)
                .order_by(asc(Messages.created_at))
            )
            turns_result = self.db.execute(stmt).scalars().all()
            turns = cast(List[List[Dict[str, Any]]], turns_result or [])

            history = [message_dict for turn in turns for message_dict in turn]
            return history
        except SQLAlchemyError:
            logger.exception(f"get_full_session_history failed for {session_id}")
            return []

    def list_sessions_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            stmt = (
                self.db.query(
                    Messages.session_id,
                    func.max(Messages.created_at).label("last_message_time"),
                )
                .filter(Messages.user_id == user_id)
                .group_by(Messages.session_id)
                .order_by(func.max(Messages.created_at).desc())
            )
            results = stmt.all()
            return [
                {
                    "session_id": row.session_id,
                    "last_message_time": row.last_message_time.isoformat(),
                }
                for row in results
            ]
        except Exception as e:
            logging.exception("Failed to list sessions for user %s", user_id)
            return []

    # This method is a helper for ChatService; it does not touch the DB.
    async def prepend(
        self,
        history: List[ModelMessage],
        agent_id: str,
    ) -> List[ModelMessage]:
        try:
            spec = AGENT_SPECS[AgentName(agent_id)]
        except (KeyError, ValueError):
            raise ValueError(f"Unknown agent_id: {agent_id}")

        if spec:
            system_prompt = spec.system_prompt

        # Taxonomy block insertion for recipe agent
        if agent_id == "recipe":
            try:
                taxonomy = await self.ingredient_service.list_parent_ingredients()
                taxonomy_block = self.ingredient_service.build_taxonomy_block(
                    taxonomy
                )  # the list_parent_ingredients function can itself fetch the taxonomy
                if taxonomy_block:
                    system_prompt = f"{spec.system_prompt}\n\n{taxonomy_block}"
            except Exception as err:
                logger.error(
                    f"Unexpected error while building taxonomy block for RECIPE agent: {err}",
                    exc_info=True,
                )


        system_msg = ModelRequest(parts=[SystemPromptPart(content=system_prompt)])
        return [system_msg, *history]
