from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from db.mongodb.schemas import CalendarTokenDocument, PyObjectId
from db.mongodb.connection import mongodb_connection
from utils.logger import logger


class MongoCalendarRepository:
    """MongoDB repository for calendar integration tokens"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else mongodb_connection.get_database()
        self.collection = self.database.calendar_tokens

    def _document_to_dict(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB document to dict"""
        return {
            "id": str(doc["_id"]),
            "user_id": str(doc["user_id"]),
            "provider": doc["provider"],
            "api_key": doc["api_key"],  # In production, decrypt here
            "username": doc["username"],
            "event_type_id": doc.get("event_type_id"),
            "event_type_slug": doc.get("event_type_slug"),
            "event_type_name": doc.get("event_type_name"),
            "is_active": doc.get("is_active", True),
            "cal_tools_enabled": doc.get("cal_tools_enabled", True),  # Default to enabled
            "created_at": doc["created_at"],
            "updated_at": doc["updated_at"]
        }

    async def save_calendar_token(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        username: str,
        event_type_id: Optional[int] = None,
        event_type_slug: Optional[str] = None,
        event_type_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save or update calendar token for a user"""
        # Check if token already exists
        existing = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "provider": provider
        })

        calendar_doc = CalendarTokenDocument(
            user_id=PyObjectId(user_id),
            provider=provider,
            api_key=api_key,
            username=username,
            event_type_id=event_type_id,
            event_type_slug=event_type_slug,
            event_type_name=event_type_name
        )

        doc_dict = calendar_doc.model_dump(by_alias=True, exclude={"id"})
        doc_dict["updated_at"] = datetime.utcnow()

        if existing:
            # Update existing
            result = await self.collection.find_one_and_update(
                {"_id": existing["_id"]},
                {"$set": doc_dict},
                return_document=True
            )
            logger.info(f"Updated calendar token for user {user_id}")
            return self._document_to_dict(result)
        else:
            # Create new
            result = await self.collection.insert_one(doc_dict)
            result_doc = await self.collection.find_one({"_id": result.inserted_id})
            logger.info(f"Created calendar token for user {user_id}")
            return self._document_to_dict(result_doc)

    async def get_by_user(self, user_id: str, provider: str = "cal.com") -> Optional[Dict[str, Any]]:
        """Get calendar token for a user"""
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "provider": provider,
            "is_active": True
        })
        if doc:
            return self._document_to_dict(doc)
        return None

    async def delete_by_user(self, user_id: str, provider: str = "cal.com") -> bool:
        """Delete calendar token for a user"""
        result = await self.collection.delete_one({
            "user_id": ObjectId(user_id),
            "provider": provider
        })
        if result.deleted_count > 0:
            logger.info(f"Deleted calendar token for user {user_id}")
            return True
        return False

    async def update_event_type(
        self,
        user_id: str,
        event_type_id: int,
        event_type_slug: str,
        event_type_name: str
    ) -> Optional[Dict[str, Any]]:
        """Update selected event type for a user's calendar"""
        result = await self.collection.find_one_and_update(
            {"user_id": ObjectId(user_id), "provider": "cal.com"},
            {
                "$set": {
                    "event_type_id": event_type_id,
                    "event_type_slug": event_type_slug,
                    "event_type_name": event_type_name,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        if result:
            return self._document_to_dict(result)
        return None

    async def toggle_cal_tools(
        self,
        user_id: str,
        enabled: bool
    ) -> Optional[Dict[str, Any]]:
        """Toggle AI calendar tools (get availability, book meetings)"""
        result = await self.collection.find_one_and_update(
            {"user_id": ObjectId(user_id), "provider": "cal.com"},
            {
                "$set": {
                    "cal_tools_enabled": enabled,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        if result:
            logger.info(f"Cal tools {'enabled' if enabled else 'disabled'} for user {user_id}")
            return self._document_to_dict(result)
        return None

