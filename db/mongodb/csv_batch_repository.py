from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from db.mongodb.schemas import CsvBatchDocument, PyObjectId
from db.mongodb.connection import get_database
from utils.logger import logger


class CsvBatch:
    """Domain model for CSV Batch"""
    def __init__(
        self,
        id: str,
        user_id: str,
        filename: str,
        total_rows: int,
        imported_count: int,
        duplicate_count: int,
        invalid_count: int,
        created_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.filename = filename
        self.total_rows = total_rows
        self.imported_count = imported_count
        self.duplicate_count = duplicate_count
        self.invalid_count = invalid_count
        self.created_at = created_at


class MongoCsvBatchRepository:
    """MongoDB implementation of CSV Batch Repository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection"""
        self.database = database if database is not None else get_database()
        self.collection = self.database.csv_batches

    def _document_to_domain(self, doc: Dict[str, Any]) -> CsvBatch:
        """Convert MongoDB document to domain model"""
        return CsvBatch(
            id=str(doc["_id"]),
            user_id=str(doc["user_id"]),
            filename=doc["filename"],
            total_rows=doc["total_rows"],
            imported_count=doc["imported_count"],
            duplicate_count=doc.get("duplicate_count", 0),
            invalid_count=doc.get("invalid_count", 0),
            created_at=doc["created_at"]
        )

    async def create_batch(
        self,
        user_id: str,
        filename: str,
        total_rows: int,
        imported_count: int,
        duplicate_count: int = 0,
        invalid_count: int = 0
    ) -> CsvBatch:
        """Create a new CSV batch record"""
        batch_doc = CsvBatchDocument(
            user_id=PyObjectId(user_id),
            filename=filename,
            total_rows=total_rows,
            imported_count=imported_count,
            duplicate_count=duplicate_count,
            invalid_count=invalid_count
        )

        doc_dict = batch_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        doc_dict["_id"] = result.inserted_id
        logger.info(f"Created CSV batch {result.inserted_id} for user {user_id}")
        
        return self._document_to_domain(doc_dict)

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[CsvBatch]:
        """Get CSV batches by user ID with pagination"""
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).skip(skip).limit(limit)

        batches = await cursor.to_list(length=limit)
        return [self._document_to_domain(doc) for doc in batches]

    async def get_by_id(self, batch_id: str) -> Optional[CsvBatch]:
        """Get CSV batch by ID"""
        doc = await self.collection.find_one({"_id": ObjectId(batch_id)})
        
        if doc:
            return self._document_to_domain(doc)
        return None

    async def count_by_user(self, user_id: str) -> int:
        """Count total CSV batches for a user"""
        count = await self.collection.count_documents({"user_id": ObjectId(user_id)})
        return count

    async def delete_by_id(self, batch_id: str) -> bool:
        """Delete a CSV batch by ID"""
        result = await self.collection.delete_one({"_id": ObjectId(batch_id)})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted CSV batch {batch_id}")
            return True
        return False
