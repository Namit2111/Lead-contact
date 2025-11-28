from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.interfaces.repositories import EmailLog, EmailLogRepository
from db.mongodb.schemas import EmailLogDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class MongoEmailLogRepository(EmailLogRepository):
    """MongoDB implementation of EmailLogRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else get_database()
        self.collection = self.database.email_logs

    def _document_to_domain(self, doc: Dict[str, Any]) -> EmailLog:
        """Convert MongoDB document to domain model"""
        return EmailLog(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            campaign_id=doc.get("campaign_id"),
            contact_id=str(doc["contact_id"]),
            template_id=str(doc["template_id"]),
            to_email=doc["to_email"],
            subject=doc["subject"],
            body=doc["body"],
            status=doc["status"],
            error_message=doc.get("error_message"),
            sent_at=doc.get("sent_at"),
            created_at=doc["created_at"],
            gmail_message_id=doc.get("gmail_message_id"),
            gmail_thread_id=doc.get("gmail_thread_id"),
            reply_count=doc.get("reply_count", 0)
        )

    async def create_log(
        self,
        user_id: str,
        campaign_id: Optional[str],
        contact_id: str,
        template_id: str,
        to_email: str,
        subject: str,
        body: str,
        status: str,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        gmail_message_id: Optional[str] = None,
        gmail_thread_id: Optional[str] = None
    ) -> EmailLog:
        """Create a new email log entry"""
        log_doc = EmailLogDocument(
            user_id=PyObjectId(user_id),
            campaign_id=campaign_id,
            contact_id=PyObjectId(contact_id),
            template_id=PyObjectId(template_id),
            to_email=to_email,
            subject=subject,
            body=body,
            status=status,
            error_message=error_message,
            sent_at=sent_at,
            gmail_message_id=gmail_message_id,
            gmail_thread_id=gmail_thread_id
        )

        doc_dict = log_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        doc_dict["_id"] = result.inserted_id
        logger.info(f"Created email log {result.inserted_id} for {to_email}")
        
        return self._document_to_domain(doc_dict)

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[EmailLog]:
        """Get email logs by user ID with pagination"""
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).skip(skip).limit(limit)

        logs = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in logs]

    async def get_by_campaign(
        self,
        campaign_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[EmailLog]:
        """Get email logs by campaign ID"""
        cursor = self.collection.find(
            {"campaign_id": campaign_id}
        ).sort("created_at", -1).skip(skip).limit(limit)

        logs = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in logs]

    async def count_by_user(self, user_id: str) -> int:
        """Count total email logs for a user"""
        count = await self.collection.count_documents({"user_id": ObjectId(user_id)})
        return count

    async def get_by_user_and_status(
        self,
        user_id: str,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[EmailLog]:
        """Get email logs by user ID and status"""
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id), "status": status}
        ).sort("created_at", -1).skip(skip).limit(limit)

        logs = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in logs]

    async def count_by_user_and_status(self, user_id: str, status: str) -> int:
        """Count email logs for a user with specific status"""
        count = await self.collection.count_documents({
            "user_id": ObjectId(user_id),
            "status": status
        })
        return count

    async def get_by_campaign_and_status(
        self,
        campaign_id: str,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[EmailLog]:
        """Get email logs by campaign ID and status"""
        cursor = self.collection.find(
            {"campaign_id": campaign_id, "status": status}
        ).sort("created_at", -1).skip(skip).limit(limit)

        logs = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in logs]

    async def count_by_campaign_and_status(self, campaign_id: str, status: str) -> int:
        """Count email logs for a campaign with specific status"""
        count = await self.collection.count_documents({
            "campaign_id": campaign_id,
            "status": status
        })
        return count

    async def count_by_campaign(self, campaign_id: str) -> int:
        """Count total email logs for a campaign"""
        count = await self.collection.count_documents({"campaign_id": campaign_id})
        return count

    async def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get statistics for a campaign"""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        stats = {
            "total": 0,
            "sent": 0,
            "failed": 0,
            "pending": 0
        }
        
        for result in results:
            status = result["_id"]
            count = result["count"]
            stats["total"] += count
            if status in stats:
                stats[status] = count
        
        return stats

    async def get_by_thread_id(self, gmail_thread_id: str) -> Optional[EmailLog]:
        """Get email log by Gmail thread ID"""
        doc = await self.collection.find_one({"gmail_thread_id": gmail_thread_id})
        if doc:
            return self._document_to_domain(doc)
        return None

    async def get_threads_for_campaign(self, campaign_id: str) -> List[EmailLog]:
        """Get all email logs with thread IDs for a campaign"""
        cursor = self.collection.find({
            "campaign_id": campaign_id,
            "gmail_thread_id": {"$ne": None}
        })
        logs = await cursor.to_list(length=10000)
        return [self._document_to_domain(doc) for doc in logs]

    async def increment_reply_count(self, email_log_id: str) -> None:
        """Increment reply count for an email log"""
        await self.collection.update_one(
            {"_id": ObjectId(email_log_id)},
            {"$inc": {"reply_count": 1}}
        )

