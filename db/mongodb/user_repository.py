from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.interfaces.repositories import UserRepository, User
from .schemas import UserDocument
from .connection import get_database
from utils.logger import logger
from datetime import datetime


class MongoUserRepository(UserRepository):
    """MongoDB implementation of UserRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database if database is not None else get_database()
        self.collection = self.database["users"]

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        try:
            doc = await self.collection.find_one({"email": email})
            if doc:
                user_doc = UserDocument(**doc)
                return User(
                    id=str(user_doc.id),
                    email=user_doc.email,
                    name=user_doc.name,
                    created_at=user_doc.created_at
                )
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise

    async def create_user(self, email: str, name: str) -> User:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await self.get_by_email(email)
            if existing_user:
                return existing_user

            user_doc = UserDocument(email=email, name=name)
            result = await self.collection.insert_one(user_doc.dict(by_alias=True))

            # Return the created user
            return User(
                id=str(result.inserted_id),
                email=email,
                name=name,
                created_at=user_doc.created_at
            )
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise
