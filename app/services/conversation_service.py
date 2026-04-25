import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db.models import ConversationMessages

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def append_conversation_message(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        bot_message: str,
        message_turn_status: str = "success",
        action_cards: Optional[Dict[str, Any]] = None,
        ai_generated_recipe: Optional[List[Dict[str, Any]]] = None,
        chatbot_recipe: Optional[List[Dict[str, Any]]] = None,
        chatbot_mixlist: Optional[List[Dict[str, Any]]] = None,
        response_time: Optional[int] = None,
        device_type: Optional[str] = None,
    ) -> str:
        """
        Inserts a conversation message and returns the inserted row id.
        """
        try:
            msg = ConversationMessages(
                session_id=session_id,
                user_id=user_id,
                user_message=user_message,
                bot_message=bot_message,
                message_turn_status=message_turn_status,
                action_cards=action_cards,
                ai_generated_recipe=ai_generated_recipe,
                chatbot_recipe=chatbot_recipe,
                chatbot_mixlist=chatbot_mixlist,
                response_time=response_time,
                device_type=device_type,
            )
            self.db.add(msg)
            self.db.commit()
            # ensure 'id' is populated
            self.db.refresh(msg)
            return str(msg.id)  # Return UUID as a string
        except SQLAlchemyError:
            logger.exception(
                "append_conversation_message failed for %s/%s", user_id, session_id
            )
            self.db.rollback()
            return ""

    def set_response_time(self, message_id: str, ms: int) -> None:
        """
        Updates the response_time (ms) for an existing conversation message.
        """
        try:
            self.db.query(ConversationMessages).filter(
                ConversationMessages.id == message_id
            ).update({"response_time": ms})
            self.db.commit()
        except SQLAlchemyError:
            logger.exception("set_response_time failed for message id %s", message_id)
            self.db.rollback()

    def get_conversation_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        try:
            stmt = (
                select(
                    ConversationMessages,
                    func.count(ConversationMessages.id)
                    .over(partition_by=None)
                    .label("total_messages"),
                )
                .where(ConversationMessages.session_id == session_id)
                .order_by(ConversationMessages.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            results = self.db.execute(stmt).all()

            messages = []
            total_messages = 0
            if results:
                for row in results:
                    msg = row.ConversationMessages
                    messages.append(
                        {
                            "id": str(msg.id),
                            "session_id": msg.session_id,
                            "user_id": msg.user_id,
                            "user_message": msg.user_message,
                            "bot_message": msg.bot_message,
                            "message_turn_status": msg.message_turn_status,
                            "action_cards": msg.action_cards,
                            "ai_generated_recipe": msg.ai_generated_recipe,
                            "chatbot_recipe": msg.chatbot_recipe,
                            "chatbot_mixlist": msg.chatbot_mixlist,
                            "response_time": msg.response_time,
                            "device_type": msg.device_type,
                            "created_at": msg.created_at.isoformat(),
                        }
                    )
                total_messages = results[0].total_messages

            return {"messages": messages, "total_messages": total_messages}
        except SQLAlchemyError:
            logger.exception("get_conversation_messages failed for %s", session_id)
            return {"messages": [], "total_messages": 0}

    def list_conversation_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            # Subquery: last message time per session
            last_time_subq = (
                select(
                    ConversationMessages.session_id.label("session_id"),
                    func.max(ConversationMessages.created_at).label(
                        "last_message_time"
                    ),
                )
                .filter(ConversationMessages.user_id == user_id)
                .group_by(ConversationMessages.session_id)
                .subquery()
            )

            # Subquery: first user message per session using row_number() window
            rn = (
                func.row_number()
                .over(
                    partition_by=ConversationMessages.session_id,
                    order_by=ConversationMessages.created_at.asc(),
                )
                .label("rn")
            )

            first_msg_subq = (
                select(
                    ConversationMessages.session_id.label("session_id"),
                    ConversationMessages.user_message.label("first_user_message"),
                    ConversationMessages.bot_message.label("first_bot_message"),
                    rn,
                )
                .filter(ConversationMessages.user_id == user_id)
                .subquery()
            )

            # Join the two subqueries and pick rn == 1 for the first message
            stmt = (
                select(
                    last_time_subq.c.session_id,
                    last_time_subq.c.last_message_time,
                    first_msg_subq.c.first_user_message,
                    first_msg_subq.c.first_bot_message,
                )
                .join(
                    first_msg_subq,
                    (first_msg_subq.c.session_id == last_time_subq.c.session_id)
                    & (first_msg_subq.c.rn == 1),
                )
                .order_by(last_time_subq.c.last_message_time.desc())
            )

            results = self.db.execute(stmt).all()
            return [
                {
                    "session_id": row.session_id,
                    "last_message_time": row.last_message_time.isoformat(),
                    "first_user_message": (row.first_user_message or "").strip()
                    or (row.first_bot_message or ""),
                }
                for row in results
            ]
        except Exception:
            logger.exception(
                "Failed to list conversation sessions for user %s", user_id
            )
            return []
