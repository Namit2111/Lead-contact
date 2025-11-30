from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.interfaces.repositories import Prompt, PromptRepository
from db.mongodb.schemas import PromptDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class MongoPromptRepository(PromptRepository):
    """MongoDB implementation of PromptRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else get_database()
        self.collection = self.database.prompts

    def _document_to_domain(self, doc: Dict[str, Any]) -> Prompt:
        """Convert MongoDB document to domain model"""
        return Prompt(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            name=doc["name"],
            description=doc.get("description"),
            prompt_text=doc["prompt_text"],
            is_default=doc.get("is_default", False),
            is_active=doc.get("is_active", True),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    async def create_prompt(
        self,
        user_id: str,
        name: str,
        prompt_text: str,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> Prompt:
        """Create a new prompt"""
        # If this is set as default, unset other defaults first
        if is_default:
            await self.collection.update_many(
                {"user_id": ObjectId(user_id), "is_default": True},
                {"$set": {"is_default": False, "updated_at": datetime.utcnow()}}
            )

        prompt_doc = PromptDocument(
            user_id=PyObjectId(user_id),
            name=name,
            description=description,
            prompt_text=prompt_text,
            is_default=is_default
        )

        doc_dict = prompt_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)

        doc_dict["_id"] = result.inserted_id
        logger.info(f"Created prompt {result.inserted_id} for user {user_id}")

        return self._document_to_domain(doc_dict)

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Prompt]:
        """Get prompts by user ID with pagination"""
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id), "is_active": True}
        ).sort("created_at", -1).skip(skip).limit(limit)

        prompts = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in prompts]

    async def get_by_id(self, prompt_id: str) -> Optional[Prompt]:
        """Get prompt by ID"""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(prompt_id)})
            if doc:
                return self._document_to_domain(doc)
            return None
        except Exception as e:
            logger.error(f"Error getting prompt {prompt_id}: {str(e)}")
            return None

    async def get_default_for_user(self, user_id: str) -> Optional[Prompt]:
        """Get user's default prompt"""
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "is_default": True,
            "is_active": True
        })
        if doc:
            return self._document_to_domain(doc)
        return None

    async def update_prompt(
        self,
        prompt_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        prompt_text: Optional[str] = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Prompt]:
        """Update an existing prompt"""
        update_data = {"updated_at": datetime.utcnow()}

        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if prompt_text is not None:
            update_data["prompt_text"] = prompt_text
        if is_active is not None:
            update_data["is_active"] = is_active
        if is_default is not None:
            update_data["is_default"] = is_default
            # If setting as default, unset other defaults
            if is_default:
                doc = await self.collection.find_one({"_id": ObjectId(prompt_id)})
                if doc:
                    await self.collection.update_many(
                        {"user_id": doc["user_id"], "is_default": True, "_id": {"$ne": ObjectId(prompt_id)}},
                        {"$set": {"is_default": False, "updated_at": datetime.utcnow()}}
                    )

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(prompt_id)},
            {"$set": update_data},
            return_document=True
        )

        if result:
            logger.info(f"Updated prompt {prompt_id}")
            return self._document_to_domain(result)
        return None

    async def set_as_default(self, user_id: str, prompt_id: str) -> Optional[Prompt]:
        """Set a prompt as the user's default (unsets other defaults)"""
        # Unset all defaults for this user
        await self.collection.update_many(
            {"user_id": ObjectId(user_id), "is_default": True},
            {"$set": {"is_default": False, "updated_at": datetime.utcnow()}}
        )

        # Set the new default
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(prompt_id), "user_id": ObjectId(user_id)},
            {"$set": {"is_default": True, "updated_at": datetime.utcnow()}},
            return_document=True
        )

        if result:
            logger.info(f"Set prompt {prompt_id} as default for user {user_id}")
            return self._document_to_domain(result)
        return None

    async def delete_by_id(self, prompt_id: str) -> bool:
        """Delete a prompt by ID (soft delete by setting is_active=False)"""
        result = await self.collection.update_one(
            {"_id": ObjectId(prompt_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )

        if result.modified_count > 0:
            logger.info(f"Soft deleted prompt {prompt_id}")
            return True
        return False

    async def count_by_user(self, user_id: str) -> int:
        """Count total active prompts for a user"""
        count = await self.collection.count_documents({
            "user_id": ObjectId(user_id),
            "is_active": True
        })
        return count

