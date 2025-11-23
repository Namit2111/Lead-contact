from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.interfaces.repositories import Template, TemplateRepository
from db.mongodb.schemas import TemplateDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class MongoTemplateRepository(TemplateRepository):
    """MongoDB implementation of TemplateRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else get_database()
        self.collection = self.database.templates

    def _document_to_domain(self, doc: Dict[str, Any]) -> Template:
        """Convert MongoDB document to domain model"""
        return Template(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            name=doc["name"],
            subject=doc["subject"],
            body=doc["body"],
            variables=doc.get("variables", []),
            is_active=doc.get("is_active", True),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    async def create_template(
        self,
        user_id: str,
        name: str,
        subject: str,
        body: str,
        variables: List[str]
    ) -> Template:
        """Create a new template"""
        template_doc = TemplateDocument(
            user_id=PyObjectId(user_id),
            name=name,
            subject=subject,
            body=body,
            variables=variables,
            is_active=True
        )

        doc_dict = template_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        doc_dict["_id"] = result.inserted_id
        logger.info(f"Created template {result.inserted_id} for user {user_id}")
        
        return self._document_to_domain(doc_dict)

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """Get templates by user ID with pagination"""
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).skip(skip).limit(limit)

        templates = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in templates]

    async def get_by_id(self, template_id: str) -> Optional[Template]:
        """Get template by ID"""
        doc = await self.collection.find_one({"_id": ObjectId(template_id)})
        
        if doc:
            return self._document_to_domain(doc)
        return None

    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        variables: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Template:
        """Update an existing template"""
        update_data = {"updated_at": datetime.utcnow()}
        
        if name is not None:
            update_data["name"] = name
        if subject is not None:
            update_data["subject"] = subject
        if body is not None:
            update_data["body"] = body
        if variables is not None:
            update_data["variables"] = variables
        if is_active is not None:
            update_data["is_active"] = is_active

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(template_id)},
            {"$set": update_data},
            return_document=True
        )

        if result:
            logger.info(f"Updated template {template_id}")
            return self._document_to_domain(result)
        
        raise ValueError(f"Template {template_id} not found")

    async def delete_by_id(self, template_id: str) -> bool:
        """Delete a template by ID"""
        result = await self.collection.delete_one({"_id": ObjectId(template_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted template {template_id}")
            return True
        return False

    async def count_by_user(self, user_id: str) -> int:
        """Count total templates for a user"""
        count = await self.collection.count_documents({"user_id": ObjectId(user_id)})
        return count

