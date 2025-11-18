import csv
import io
import re
from typing import List, Dict, Any, Tuple
from utils.logger import logger


class CsvService:
    """Service for processing CSV files"""

    # Standard CSV columns we expect
    STANDARD_FIELDS = {"email", "name", "company", "phone"}
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(re.match(CsvService.EMAIL_REGEX, email.strip()))

    @staticmethod
    async def parse_csv(
        file_content: bytes,
        user_id: str,
        filename: str
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse CSV file and extract contact data
        
        Returns:
            Tuple of (valid_contacts, error_messages)
        """
        valid_contacts = []
        errors = []
        
        try:
            # Decode file content
            content = file_content.decode('utf-8-sig')  # Handle BOM
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Check if email column exists
            if not csv_reader.fieldnames:
                errors.append("CSV file is empty or invalid")
                return valid_contacts, errors
            
            fieldnames = [f.lower().strip() for f in csv_reader.fieldnames]
            
            if 'email' not in fieldnames:
                errors.append("CSV must contain an 'email' column")
                return valid_contacts, errors
            
            # Process rows
            for idx, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                # Normalize keys to lowercase
                normalized_row = {k.lower().strip(): v.strip() if v else None 
                                 for k, v in row.items()}
                
                email = normalized_row.get('email')
                
                # Validate email
                if not email:
                    errors.append(f"Row {idx}: Missing email")
                    continue
                
                if not CsvService.validate_email(email):
                    errors.append(f"Row {idx}: Invalid email format '{email}'")
                    continue
                
                # Extract standard fields
                contact_data = {
                    "user_id": user_id,
                    "email": email.lower().strip(),
                    "name": normalized_row.get('name'),
                    "company": normalized_row.get('company'),
                    "phone": normalized_row.get('phone'),
                    "source": filename,
                    "custom_fields": {}
                }
                
                # Extract custom fields (any column not in standard fields)
                for key, value in normalized_row.items():
                    if key not in CsvService.STANDARD_FIELDS and value:
                        contact_data["custom_fields"][key] = value
                
                valid_contacts.append(contact_data)
            
            logger.info(f"Parsed CSV: {len(valid_contacts)} valid contacts, {len(errors)} errors")
            
        except UnicodeDecodeError:
            errors.append("File encoding error. Please ensure the file is UTF-8 encoded")
        except csv.Error as e:
            errors.append(f"CSV parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            errors.append(f"Unexpected error: {str(e)}")
        
        return valid_contacts, errors

    @staticmethod
    async def detect_duplicates(
        contacts_data: List[Dict[str, Any]],
        existing_emails: set
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Filter out duplicate contacts
        
        Returns:
            Tuple of (unique_contacts, duplicate_emails)
        """
        unique_contacts = []
        duplicate_emails = []
        seen_emails = set()
        
        for contact in contacts_data:
            email = contact["email"]
            
            # Check against existing emails in DB
            if email in existing_emails:
                duplicate_emails.append(email)
                continue
            
            # Check for duplicates within the CSV
            if email in seen_emails:
                duplicate_emails.append(email)
                continue
            
            seen_emails.add(email)
            unique_contacts.append(contact)
        
        return unique_contacts, duplicate_emails

