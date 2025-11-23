from core.interfaces.repositories import UserRepository, ProviderTokenRepository, ContactRepository, TemplateRepository
from db.mongodb.user_repository import MongoUserRepository
from db.mongodb.provider_token_repository import MongoProviderTokenRepository
from db.mongodb.contact_repository import MongoContactRepository
from db.mongodb.template_repository import MongoTemplateRepository
from db.mongodb.connection import get_database, mongodb_connection
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional


class RepositoryFactory:
    """Factory for creating repository instances"""

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        self.database = database

    async def create_user_repository(self) -> UserRepository:
        """Create user repository instance"""
        if self.database is None:
            self.database = mongodb_connection.get_database()
        return MongoUserRepository(self.database)

    async def create_provider_token_repository(self) -> ProviderTokenRepository:
        """Create provider token repository instance"""
        if self.database is None:
            self.database = mongodb_connection.get_database()
        return MongoProviderTokenRepository(self.database)

    async def create_contact_repository(self) -> ContactRepository:
        """Create contact repository instance"""
        if self.database is None:
            self.database = mongodb_connection.get_database()
        return MongoContactRepository(self.database)

    async def create_template_repository(self) -> TemplateRepository:
        """Create template repository instance"""
        if self.database is None:
            self.database = mongodb_connection.get_database()
        return MongoTemplateRepository(self.database)


# Global factory instance
repository_factory = RepositoryFactory()


async def get_user_repository() -> UserRepository:
    """Convenience function to get user repository"""
    return await repository_factory.create_user_repository()


async def get_provider_token_repository() -> ProviderTokenRepository:
    """Convenience function to get provider token repository"""
    return await repository_factory.create_provider_token_repository()


async def get_contact_repository() -> ContactRepository:
    """Convenience function to get contact repository"""
    return await repository_factory.create_contact_repository()


async def get_template_repository() -> TemplateRepository:
    """Convenience function to get template repository"""
    return await repository_factory.create_template_repository()
