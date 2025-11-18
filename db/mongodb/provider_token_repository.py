from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.interfaces.repositories import ProviderTokenRepository, ProviderToken
from .schemas import ProviderTokenDocument
from .connection import get_database
from utils.logger import logger
from datetime import datetime
from bson import ObjectId


class MongoProviderTokenRepository(ProviderTokenRepository):
    """MongoDB implementation of ProviderTokenRepository"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database if database is not None else get_database()
        self.collection = self.database["provider_tokens"]

    async def save_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime,
        scope: List[str]
    ) -> ProviderToken:
        """Save provider tokens for a user"""
        try:
            # Check if tokens already exist for this user and provider
            existing = await self.get_by_user_and_provider(user_id, provider)
            if existing:
                # Update existing tokens
                return await self.update_tokens(
                    existing.id, access_token, refresh_token, expiry
                )

            token_doc = ProviderTokenDocument(
                user_id=ObjectId(user_id),
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry=expiry,
                scope=scope
            )

            result = await self.collection.insert_one(token_doc.dict(by_alias=True))

            return ProviderToken(
                id=str(result.inserted_id),
                user_id=user_id,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry=expiry,
                scope=scope,
                created_at=token_doc.created_at,
                updated_at=token_doc.updated_at
            )
        except Exception as e:
            logger.error(f"Error saving tokens for user {user_id}, provider {provider}: {e}")
            raise

    async def get_by_user_and_provider(self, user_id: str, provider: str) -> Optional[ProviderToken]:
        """Get provider tokens by user and provider"""
        try:
            doc = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "provider": provider
            })

            if doc:
                token_doc = ProviderTokenDocument(**doc)
                return ProviderToken(
                    id=str(token_doc.id),
                    user_id=str(token_doc.user_id),
                    provider=token_doc.provider,
                    access_token=token_doc.access_token,
                    refresh_token=token_doc.refresh_token,
                    expiry=token_doc.expiry,
                    scope=token_doc.scope,
                    created_at=token_doc.created_at,
                    updated_at=token_doc.updated_at
                )
            return None
        except Exception as e:
            logger.error(f"Error getting tokens for user {user_id}, provider {provider}: {e}")
            raise

    async def update_tokens(
        self,
        token_id: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime
    ) -> ProviderToken:
        """Update existing provider tokens"""
        try:
            update_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expiry": expiry,
                "updated_at": datetime.utcnow()
            }

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(token_id)},
                {"$set": update_data},
                return_document=True
            )

            if result:
                token_doc = ProviderTokenDocument(**result)
                return ProviderToken(
                    id=str(token_doc.id),
                    user_id=str(token_doc.user_id),
                    provider=token_doc.provider,
                    access_token=token_doc.access_token,
                    refresh_token=token_doc.refresh_token,
                    expiry=token_doc.expiry,
                    scope=token_doc.scope,
                    created_at=token_doc.created_at,
                    updated_at=token_doc.updated_at
                )
            else:
                raise ValueError(f"Token with id {token_id} not found")
        except Exception as e:
            logger.error(f"Error updating tokens for token_id {token_id}: {e}")
            raise
