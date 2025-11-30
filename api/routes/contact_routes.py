from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Query
from typing import Optional
from core.csv.models import (
    ContactUploadResponse,
    ContactListResponse,
    ContactStatsResponse,
    DeleteContactResponse,
    ContactItem,
    CsvUploadsListResponse,
    CsvUploadItem
)
from core.csv.csv_service import CsvService
from db.repository_factory import get_contact_repository
from utils.logger import logger


router = APIRouter(prefix="/contacts")

# File upload limits
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".csv", ".txt"}


def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> str:
    """Extract user ID from header"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User authentication required. Missing X-User-Id header")
    return x_user_id


@router.post("/upload", response_model=ContactUploadResponse)
async def upload_contacts(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(None)
):
    """
    Upload CSV file with contacts
    
    Expected CSV format:
    email,name,company,phone
    john@example.com,John Doe,Acme Inc,+1234567890
    """
    user_id = get_user_id_from_header(x_user_id)
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    file_ext = file.filename[file.filename.rfind('.'):].lower() if '.' in file.filename else ''
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Parse CSV
        csv_service = CsvService()
        contacts_data, parse_errors = await csv_service.parse_csv(
            content,
            user_id,
            file.filename
        )
        
        if parse_errors and not contacts_data:
            # All rows failed
            return ContactUploadResponse(
                success=False,
                total_rows=0,
                imported=0,
                duplicates=0,
                invalid=len(parse_errors),
                message=f"Failed to parse CSV: {'; '.join(parse_errors[:5])}"
            )
        
        # Get repository
        contact_repo = await get_contact_repository()
        
        # Detect duplicates within the CSV file only (not across all contacts)
        # Each CSV file is treated as a separate batch - same email can exist in different CSVs
        unique_contacts, duplicate_emails = await csv_service.detect_duplicates(
            contacts_data,
            set()  # Empty set - only detect duplicates within this CSV
        )
        
        # Bulk create contacts
        created_contacts = []
        if unique_contacts:
            created_contacts = await contact_repo.bulk_create_contacts(unique_contacts)
        
        # Convert to response models
        contact_items = [
            ContactItem(
                id=contact.id,
                email=contact.email,
                name=contact.name,
                company=contact.company,
                phone=contact.phone,
                custom_fields=contact.custom_fields,
                source=contact.source,
                created_at=contact.created_at,
                updated_at=contact.updated_at
            )
            for contact in created_contacts
        ]
        
        total_rows = len(contacts_data) + len(parse_errors)
        
        message_parts = []
        if created_contacts:
            message_parts.append(f"Successfully imported {len(created_contacts)} contacts")
        if duplicate_emails:
            message_parts.append(f"{len(duplicate_emails)} duplicates skipped")
        if parse_errors:
            message_parts.append(f"{len(parse_errors)} invalid rows")
        
        return ContactUploadResponse(
            success=len(created_contacts) > 0,
            total_rows=total_rows,
            imported=len(created_contacts),
            duplicates=len(duplicate_emails),
            invalid=len(parse_errors),
            message="; ".join(message_parts) if message_parts else "No contacts imported",
            contacts=contact_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading contacts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """List user's contacts with pagination"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        contact_repo = await get_contact_repository()
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Get contacts
        contacts = await contact_repo.get_by_user(user_id, skip=skip, limit=page_size)
        total = await contact_repo.count_by_user(user_id)
        
        # Convert to response models
        contact_items = [
            ContactItem(
                id=contact.id,
                email=contact.email,
                name=contact.name,
                company=contact.company,
                phone=contact.phone,
                custom_fields=contact.custom_fields,
                source=contact.source,
                created_at=contact.created_at,
                updated_at=contact.updated_at
            )
            for contact in contacts
        ]
        
        return ContactListResponse(
            contacts=contact_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing contacts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{contact_id}", response_model=DeleteContactResponse)
async def delete_contact(
    contact_id: str,
    x_user_id: Optional[str] = Header(None)
):
    """Delete a contact by ID"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        contact_repo = await get_contact_repository()
        
        # TODO: Add authorization check to ensure contact belongs to user
        success = await contact_repo.delete_by_id(contact_id)
        
        if success:
            return DeleteContactResponse(
                success=True,
                message="Contact deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Contact not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting contact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/by-source/{source:path}", response_model=DeleteContactResponse)
async def delete_contacts_by_source(
    source: str,
    x_user_id: Optional[str] = Header(None)
):
    """Delete all contacts from a specific CSV source"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        contact_repo = await get_contact_repository()
        
        deleted_count = await contact_repo.delete_by_source(user_id, source)
        
        if deleted_count > 0:
            return DeleteContactResponse(
                success=True,
                message=f"Successfully deleted {deleted_count} contacts from '{source}'"
            )
        else:
            raise HTTPException(status_code=404, detail=f"No contacts found for source '{source}'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting contacts by source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ContactStatsResponse)
async def get_contact_stats(
    x_user_id: Optional[str] = Header(None)
):
    """Get contact statistics for user"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        contact_repo = await get_contact_repository()
        
        # Get all contacts for stats
        all_contacts = await contact_repo.get_by_user(user_id, skip=0, limit=10000)
        
        # Calculate stats
        sources = {}
        for contact in all_contacts:
            source = contact.source
            sources[source] = sources.get(source, 0) + 1
        
        return ContactStatsResponse(
            total_contacts=len(all_contacts),
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Error getting contact stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploads", response_model=CsvUploadsListResponse)
async def get_csv_uploads(
    x_user_id: Optional[str] = Header(None)
):
    """Get list of CSV uploads for user"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        contact_repo = await get_contact_repository()
        
        # Get CSV uploads grouped by source
        uploads = await contact_repo.get_csv_uploads_by_user(user_id)
        
        # Convert to response models
        upload_items = [
            CsvUploadItem(
                source=upload["source"],
                contact_count=upload["contact_count"],
                first_uploaded=upload["first_uploaded"],
                last_uploaded=upload["last_uploaded"]
            )
            for upload in uploads
        ]
        
        return CsvUploadsListResponse(
            uploads=upload_items,
            total_uploads=len(upload_items)
        )
        
    except Exception as e:
        logger.error(f"Error getting CSV uploads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-source/{source}", response_model=ContactListResponse)
async def get_contacts_by_source(
    source: str,
    x_user_id: Optional[str] = Header(None),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Get contacts from a specific CSV source"""
    user_id = get_user_id_from_header(x_user_id)
    
    try:
        contact_repo = await get_contact_repository()
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Get contacts by source
        contacts = await contact_repo.get_contacts_by_source(
            user_id, source, skip=skip, limit=page_size
        )
        
        # Get total count for this source
        all_contacts = await contact_repo.get_contacts_by_source(
            user_id, source, skip=0, limit=10000
        )
        total = len(all_contacts)
        
        # Convert to response models
        contact_items = [
            ContactItem(
                id=contact.id,
                email=contact.email,
                name=contact.name,
                company=contact.company,
                phone=contact.phone,
                custom_fields=contact.custom_fields,
                source=contact.source,
                created_at=contact.created_at,
                updated_at=contact.updated_at
            )
            for contact in contacts
        ]
        
        return ContactListResponse(
            contacts=contact_items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting contacts by source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

