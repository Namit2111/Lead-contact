from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings
from utils.logger import logger


class MongoDBConnection:
    """MongoDB connection manager using Motor"""

    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.database: AsyncIOMotorDatabase = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.mongo_uri)
            self.database = self.client[settings.mongo_db_name]
            # Test the connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB database: {settings.mongo_db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client is not None:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance"""
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database


# Global connection instance
mongodb_connection = MongoDBConnection()


async def get_database() -> AsyncIOMotorDatabase:
    """Convenience function to get database instance"""
    return mongodb_connection.get_database()
