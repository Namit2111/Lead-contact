from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.interfaces.repositories import Contact, ContactRepository
from db.mongodb.schemas import ContactDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class MongoContactRepository(ContactRepository):
    """MongoDB implementation of ContactRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else get_database()
        self.collection = self.database.contacts

    def _document_to_domain(self, doc: Dict[str, Any]) -> Contact:
        """Convert MongoDB document to domain model"""
        return Contact(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            email=doc["email"],
            name=doc.get("name"),
            company=doc.get("company"),
            phone=doc.get("phone"),
            custom_fields=doc.get("custom_fields", {}),
            source=doc["source"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )

    async def create_contact(
        self,
        user_id: str,
        email: str,
        name: Optional[str],
        company: Optional[str],
        phone: Optional[str],
        custom_fields: Dict[str, Any],
        source: str
    ) -> Contact:
        """Create a new contact"""
        contact_doc = ContactDocument(
            user_id=PyObjectId(user_id),
            email=email.lower().strip(),
            name=name,
            company=company,
            phone=phone,
            custom_fields=custom_fields,
            source=source
        )

        doc_dict = contact_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        doc_dict["_id"] = result.inserted_id
        logger.info(f"Created contact {result.inserted_id} for user {user_id}")
        
        return self._document_to_domain(doc_dict)

    async def bulk_create_contacts(
        self,
        contacts_data: List[Dict[str, Any]]
    ) -> List[Contact]:
        """Create multiple contacts in bulk"""
        if not contacts_data:
            return []

        documents = []
        for data in contacts_data:
            contact_doc = ContactDocument(
                user_id=PyObjectId(data["user_id"]),
                email=data["email"].lower().strip(),
                name=data.get("name"),
                company=data.get("company"),
                phone=data.get("phone"),
                custom_fields=data.get("custom_fields", {}),
                source=data["source"]
            )
            documents.append(contact_doc.model_dump(by_alias=True, exclude={"id"}))

        result = await self.collection.insert_many(documents)
        logger.info(f"Created {len(result.inserted_ids)} contacts in bulk")

        # Fetch created documents
        created_contacts = await self.collection.find(
            {"_id": {"$in": result.inserted_ids}}
        ).to_list(length=len(result.inserted_ids))

        return [self._document_to_domain(doc) for doc in created_contacts]

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Get contacts by user ID with pagination"""
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).skip(skip).limit(limit)

        contacts = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in contacts]

    async def get_by_user_and_email(
        self,
        user_id: str,
        email: str
    ) -> Optional[Contact]:
        """Get contact by user ID and email"""
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "email": email.lower().strip()
        })

        if doc:
            return self._document_to_domain(doc)
        return None

    async def delete_by_id(self, contact_id: str) -> bool:
        """Delete a contact by ID"""
        result = await self.collection.delete_one({"_id": ObjectId(contact_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted contact {contact_id}")
            return True
        return False

    async def count_by_user(self, user_id: str) -> int:
        """Count total contacts for a user"""
        count = await self.collection.count_documents({"user_id": ObjectId(user_id)})
        return count

    async def get_csv_uploads_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of CSV uploads with contact counts for a user"""
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {
                "$group": {
                    "_id": "$source",
                    "contact_count": {"$sum": 1},
                    "first_uploaded": {"$min": "$created_at"},
                    "last_uploaded": {"$max": "$created_at"}
                }
            },
            {"$sort": {"last_uploaded": -1}}
        ]
        
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        uploads = []
        for result in results:
            uploads.append({
                "source": result["_id"],
                "contact_count": result["contact_count"],
                "first_uploaded": result["first_uploaded"],
                "last_uploaded": result["last_uploaded"]
            })
        
        return uploads

    async def get_contacts_by_source(
        self,
        user_id: str,
        source: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Get contacts by user ID and CSV source"""
        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "source": source
        }).sort("created_at", -1).skip(skip).limit(limit)

        contacts = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in contacts]

