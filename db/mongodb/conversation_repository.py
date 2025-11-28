from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.interfaces.repositories import Conversation, ConversationMessage
from db.mongodb.schemas import ConversationDocument, ConversationMessageDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class MongoConversationRepository:
    """MongoDB implementation for conversations"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database if database is not None else get_database()
        self.conversations = self.database.conversations
        self.messages = self.database.conversation_messages

    def _doc_to_conversation(self, doc: dict) -> Conversation:
        """Convert document to Conversation model"""
        return Conversation(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            campaign_id=doc["campaign_id"],
            email_log_id=doc["email_log_id"],
            contact_email=doc["contact_email"],
            gmail_thread_id=doc["gmail_thread_id"],
            status=doc.get("status", "active"),
            message_count=doc.get("message_count", 1),
            auto_replies_sent=doc.get("auto_replies_sent", 0),
            last_message_at=doc.get("last_message_at"),
            last_reply_at=doc.get("last_reply_at"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    def _doc_to_message(self, doc: dict) -> ConversationMessage:
        """Convert document to ConversationMessage model"""
        return ConversationMessage(
            id=str(doc["_id"]),
            conversation_id=str(doc["conversation_id"]),
            campaign_id=doc["campaign_id"],
            direction=doc["direction"],
            from_email=doc["from_email"],
            to_email=doc["to_email"],
            subject=doc["subject"],
            body=doc["body"],
            gmail_message_id=doc["gmail_message_id"],
            is_auto_reply=doc.get("is_auto_reply", False),
            sent_at=doc["sent_at"],
            created_at=doc["created_at"]
        )

    async def create_conversation(
        self,
        user_id: str,
        campaign_id: str,
        email_log_id: str,
        contact_email: str,
        gmail_thread_id: str
    ) -> Conversation:
        """Create a new conversation"""
        doc = ConversationDocument(
            user_id=PyObjectId(user_id),
            campaign_id=campaign_id,
            email_log_id=email_log_id,
            contact_email=contact_email,
            gmail_thread_id=gmail_thread_id,
            status="active",
            message_count=1,
            auto_replies_sent=0,
            last_message_at=datetime.utcnow()
        )

        result = await self.conversations.insert_one(
            doc.model_dump(by_alias=True, exclude={"id"})
        )

        created = await self.conversations.find_one({"_id": result.inserted_id})
        logger.info(f"Created conversation {result.inserted_id} for thread {gmail_thread_id}")
        return self._doc_to_conversation(created)

    async def get_by_thread_id(self, gmail_thread_id: str) -> Optional[Conversation]:
        """Get conversation by Gmail thread ID"""
        doc = await self.conversations.find_one({"gmail_thread_id": gmail_thread_id})
        return self._doc_to_conversation(doc) if doc else None

    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        doc = await self.conversations.find_one({"_id": ObjectId(conversation_id)})
        return self._doc_to_conversation(doc) if doc else None

    async def get_by_campaign(
        self,
        campaign_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """Get conversations for a campaign"""
        cursor = self.conversations.find(
            {"campaign_id": campaign_id}
        ).sort("last_message_at", -1).skip(skip).limit(limit)

        conversations = []
        async for doc in cursor:
            conversations.append(self._doc_to_conversation(doc))
        return conversations

    async def count_by_campaign(self, campaign_id: str) -> int:
        """Count conversations for a campaign"""
        return await self.conversations.count_documents({"campaign_id": campaign_id})

    async def update_on_reply(
        self,
        conversation_id: str,
        is_inbound: bool = True
    ) -> Optional[Conversation]:
        """Update conversation when a new message is received/sent"""
        update = {
            "$inc": {"message_count": 1},
            "$set": {
                "last_message_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }

        if is_inbound:
            update["$set"]["last_reply_at"] = datetime.utcnow()

        result = await self.conversations.find_one_and_update(
            {"_id": ObjectId(conversation_id)},
            update,
            return_document=True
        )
        return self._doc_to_conversation(result) if result else None

    async def increment_auto_replies(self, conversation_id: str) -> Optional[Conversation]:
        """Increment auto-reply count"""
        result = await self.conversations.find_one_and_update(
            {"_id": ObjectId(conversation_id)},
            {
                "$inc": {"auto_replies_sent": 1, "message_count": 1},
                "$set": {
                    "last_message_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return self._doc_to_conversation(result) if result else None

    async def update_status(
        self,
        conversation_id: str,
        status: str
    ) -> Optional[Conversation]:
        """Update conversation status"""
        result = await self.conversations.find_one_and_update(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
            return_document=True
        )
        return self._doc_to_conversation(result) if result else None

    # Message methods
    async def add_message(
        self,
        conversation_id: str,
        campaign_id: str,
        direction: str,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        gmail_message_id: str,
        is_auto_reply: bool = False,
        sent_at: Optional[datetime] = None
    ) -> ConversationMessage:
        """Add a message to conversation"""
        doc = ConversationMessageDocument(
            conversation_id=PyObjectId(conversation_id),
            campaign_id=campaign_id,
            direction=direction,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=body,
            gmail_message_id=gmail_message_id,
            is_auto_reply=is_auto_reply,
            sent_at=sent_at or datetime.utcnow()
        )

        result = await self.messages.insert_one(
            doc.model_dump(by_alias=True, exclude={"id"})
        )

        created = await self.messages.find_one({"_id": result.inserted_id})
        return self._doc_to_message(created)

    async def get_messages(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConversationMessage]:
        """Get messages in a conversation"""
        cursor = self.messages.find(
            {"conversation_id": ObjectId(conversation_id)}
        ).sort("sent_at", 1).skip(skip).limit(limit)

        messages = []
        async for doc in cursor:
            messages.append(self._doc_to_message(doc))
        return messages

    async def message_exists(self, gmail_message_id: str) -> bool:
        """Check if a message already exists (to avoid duplicates)"""
        count = await self.messages.count_documents({"gmail_message_id": gmail_message_id})
        return count > 0

    async def get_active_conversations_for_campaign(self, campaign_id: str) -> List[Conversation]:
        """Get active conversations for a campaign"""
        cursor = self.conversations.find({
            "campaign_id": campaign_id,
            "status": "active"
        })

        conversations = []
        async for doc in cursor:
            conversations.append(self._doc_to_conversation(doc))
        return conversations

