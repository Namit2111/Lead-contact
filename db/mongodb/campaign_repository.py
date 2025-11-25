from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.interfaces.repositories import Campaign, CampaignRepository
from db.mongodb.schemas import CampaignDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class MongoCampaignRepository(CampaignRepository):
    """MongoDB implementation of CampaignRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else get_database()
        self.collection = self.database.campaigns

    def _document_to_campaign(self, doc: dict) -> Campaign:
        """Convert MongoDB document to Campaign domain model"""
        return Campaign(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            name=doc["name"],
            csv_source=doc["csv_source"],
            template_id=str(doc["template_id"]),
            status=doc["status"],
            total_contacts=doc["total_contacts"],
            processed=doc["processed"],
            sent=doc["sent"],
            failed=doc["failed"],
            trigger_run_id=doc.get("trigger_run_id"),
            error_message=doc.get("error_message"),
            created_at=doc["created_at"],
            started_at=doc.get("started_at"),
            completed_at=doc.get("completed_at"),
            updated_at=doc["updated_at"]
        )

    async def create_campaign(
        self,
        user_id: str,
        name: str,
        csv_source: str,
        template_id: str,
        total_contacts: int,
        status: str = "queued"
    ) -> Campaign:
        """Create a new campaign"""
        try:
            campaign_doc = CampaignDocument(
                user_id=PyObjectId(user_id),
                name=name,
                csv_source=csv_source,
                template_id=PyObjectId(template_id),
                status=status,
                total_contacts=total_contacts,
                processed=0,
                sent=0,
                failed=0
            )

            result = await self.collection.insert_one(
                campaign_doc.model_dump(by_alias=True, exclude={"id"})
            )

            created_doc = await self.collection.find_one({"_id": result.inserted_id})
            return self._document_to_campaign(created_doc)

        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            raise

    async def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(campaign_id)})
            return self._document_to_campaign(doc) if doc else None
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {str(e)}")
            return None

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Campaign]:
        """Get campaigns by user ID"""
        try:
            cursor = self.collection.find(
                {"user_id": ObjectId(user_id)}
            ).sort("created_at", -1).skip(skip).limit(limit)

            campaigns = []
            async for doc in cursor:
                campaigns.append(self._document_to_campaign(doc))

            return campaigns

        except Exception as e:
            logger.error(f"Error getting campaigns for user {user_id}: {str(e)}")
            return []

    async def update_status(
        self,
        campaign_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Campaign]:
        """Update campaign status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }

            if error_message:
                update_data["error_message"] = error_message

            if status == "running" and not await self._has_started(campaign_id):
                update_data["started_at"] = datetime.utcnow()

            if status in ["completed", "failed", "cancelled"]:
                update_data["completed_at"] = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(campaign_id)},
                {"$set": update_data},
                return_document=True
            )

            return self._document_to_campaign(result) if result else None

        except Exception as e:
            logger.error(f"Error updating campaign status {campaign_id}: {str(e)}")
            return None

    async def _has_started(self, campaign_id: str) -> bool:
        """Check if campaign has started_at timestamp"""
        doc = await self.collection.find_one(
            {"_id": ObjectId(campaign_id)},
            {"started_at": 1}
        )
        return doc and doc.get("started_at") is not None

    async def update_progress(
        self,
        campaign_id: str,
        processed: int,
        sent: int,
        failed: int
    ) -> Optional[Campaign]:
        """Update campaign progress"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(campaign_id)},
                {
                    "$set": {
                        "processed": processed,
                        "sent": sent,
                        "failed": failed,
                        "updated_at": datetime.utcnow()
                    }
                },
                return_document=True
            )

            return self._document_to_campaign(result) if result else None

        except Exception as e:
            logger.error(f"Error updating campaign progress {campaign_id}: {str(e)}")
            return None

    async def set_trigger_run_id(
        self,
        campaign_id: str,
        trigger_run_id: str
    ) -> Optional[Campaign]:
        """Set Trigger.dev run ID"""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(campaign_id)},
                {
                    "$set": {
                        "trigger_run_id": trigger_run_id,
                        "updated_at": datetime.utcnow()
                    }
                },
                return_document=True
            )

            return self._document_to_campaign(result) if result else None

        except Exception as e:
            logger.error(f"Error setting trigger run ID for campaign {campaign_id}: {str(e)}")
            return None

    async def count_by_user(self, user_id: str) -> int:
        """Count total campaigns for a user"""
        try:
            return await self.collection.count_documents({"user_id": ObjectId(user_id)})
        except Exception as e:
            logger.error(f"Error counting campaigns for user {user_id}: {str(e)}")
            return 0

    async def get_by_status(
        self,
        user_id: str,
        status: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Campaign]:
        """Get campaigns by status"""
        try:
            cursor = self.collection.find(
                {
                    "user_id": ObjectId(user_id),
                    "status": status
                }
            ).sort("created_at", -1).skip(skip).limit(limit)

            campaigns = []
            async for doc in cursor:
                campaigns.append(self._document_to_campaign(doc))

            return campaigns

        except Exception as e:
            logger.error(f"Error getting campaigns by status for user {user_id}: {str(e)}")
            return []

