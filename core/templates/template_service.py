import re
from typing import List, Dict, Any
from utils.logger import logger


class TemplateService:
    """Service for processing email templates"""

    # Regex to match variables in format {{variable_name}}
    VARIABLE_PATTERN = r'\{\{(\w+)\}\}'

    @staticmethod
    def extract_variables(text: str) -> List[str]:
        """
        Extract all variables from template text
        
        Args:
            text: Template text containing {{variable}} placeholders
            
        Returns:
            List of unique variable names
        """
        matches = re.findall(TemplateService.VARIABLE_PATTERN, text)
        return list(set(matches))  # Remove duplicates

    @staticmethod
    def extract_template_variables(subject: str, body: str) -> List[str]:
        """
        Extract all variables from subject and body
        
        Args:
            subject: Email subject line
            body: Email body text
            
        Returns:
            List of unique variable names from both subject and body
        """
        subject_vars = TemplateService.extract_variables(subject)
        body_vars = TemplateService.extract_variables(body)
        
        all_vars = list(set(subject_vars + body_vars))
        logger.info(f"Extracted {len(all_vars)} unique variables: {all_vars}")
        
        return sorted(all_vars)

    @staticmethod
    def render_template(template_text: str, data: Dict[str, Any]) -> str:
        """
        Render template by replacing variables with actual data
        
        Args:
            template_text: Template text with {{variable}} placeholders
            data: Dictionary of variable_name -> value mappings
            
        Returns:
            Rendered text with variables replaced
        """
        rendered = template_text
        
        # Find all variables in template
        variables = TemplateService.extract_variables(template_text)
        
        for var in variables:
            placeholder = f"{{{{{var}}}}}"
            value = data.get(var, f"[{var}]")  # Use [var] if not found
            
            # Convert None to empty string
            if value is None:
                value = ""
            
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered

    @staticmethod
    def validate_template(subject: str, body: str) -> tuple[bool, List[str]]:
        """
        Validate template format
        
        Args:
            subject: Email subject line
            body: Email body text
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if subject is empty
        if not subject or not subject.strip():
            errors.append("Subject line cannot be empty")
        
        # Check if body is empty
        if not body or not body.strip():
            errors.append("Email body cannot be empty")
        
        # Check for malformed variables (e.g., {variable} instead of {{variable}})
        malformed_pattern = r'\{(?!\{)(\w+)\}(?!\})'
        
        malformed_in_subject = re.findall(malformed_pattern, subject)
        if malformed_in_subject:
            errors.append(f"Malformed variables in subject: {malformed_in_subject}. Use {{{{variable}}}} format")
        
        malformed_in_body = re.findall(malformed_pattern, body)
        if malformed_in_body:
            errors.append(f"Malformed variables in body: {malformed_in_body}. Use {{{{variable}}}} format")
        
        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def preview_template(
        subject: str,
        body: str,
        sample_data: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """
        Generate preview of template with sample data
        
        Args:
            subject: Email subject line
            body: Email body text
            sample_data: Optional sample data for preview
            
        Returns:
            Dictionary with rendered subject and body
        """
        if sample_data is None:
            # Use default sample data
            sample_data = {
                "name": "John Doe",
                "email": "john@example.com",
                "company": "Acme Inc",
                "phone": "+1234567890"
            }
        
        rendered_subject = TemplateService.render_template(subject, sample_data)
        rendered_body = TemplateService.render_template(body, sample_data)
        
        return {
            "subject": rendered_subject,
            "body": rendered_body
        }

