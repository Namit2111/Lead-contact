from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId


class User:
    """User domain model"""
    def __init__(self, id: str, email: str, name: str, created_at: datetime):
        self.id = id
        self.email = email
        self.name = name
        self.created_at = created_at


class ProviderToken:
    """Provider token domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime,
        scope: List[str],
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.provider = provider
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = expiry
        self.scope = scope
        self.created_at = created_at
        self.updated_at = updated_at


class UserRepository(ABC):
    """Abstract repository for user operations"""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        pass

    @abstractmethod
    async def create_user(self, email: str, name: str) -> User:
        """Create a new user"""
        pass


class ProviderTokenRepository(ABC):
    """Abstract repository for provider token operations"""

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_by_user_and_provider(self, user_id: str, provider: str) -> Optional[ProviderToken]:
        """Get provider tokens by user and provider"""
        pass

    @abstractmethod
    async def update_tokens(
        self,
        token_id: str,
        access_token: str,
        refresh_token: str,
        expiry: datetime
    ) -> ProviderToken:
        """Update existing provider tokens"""
        pass


class Contact:
    """Contact domain model"""
    def __init__(
        self,
        id: str,
        user_id: str,
        email: str,
        name: Optional[str],
        company: Optional[str],
        phone: Optional[str],
        custom_fields: Dict[str, Any],
        source: str,
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.user_id = user_id
        self.email = email
        self.name = name
        self.company = company
        self.phone = phone
        self.custom_fields = custom_fields
        self.source = source
        self.created_at = created_at
        self.updated_at = updated_at


class ContactRepository(ABC):
    """Abstract repository for contact operations"""

    @abstractmethod
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
        pass

    @abstractmethod
    async def bulk_create_contacts(
        self,
        contacts_data: List[Dict[str, Any]]
    ) -> List[Contact]:
        """Create multiple contacts in bulk"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Get contacts by user ID with pagination"""
        pass

    @abstractmethod
    async def get_by_user_and_email(
        self,
        user_id: str,
        email: str
    ) -> Optional[Contact]:
        """Get contact by user ID and email"""
        pass

    @abstractmethod
    async def delete_by_id(self, contact_id: str) -> bool:
        """Delete a contact by ID"""
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Count total contacts for a user"""
        pass

    @abstractmethod
    async def get_csv_uploads_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of CSV uploads with contact counts for a user"""
        pass

    @abstractmethod
    async def get_contacts_by_source(
        self,
        user_id: str,
        source: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """Get contacts by user ID and CSV source"""
        pass
