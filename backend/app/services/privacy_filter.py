"""
Privacy filter service to remove personal information from responses
"""
from typing import Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)


class PrivacyFilter:
    """Service to filter out personal information from data"""
    
    # Patterns to detect personal information
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:\d{4,5}[-.\s]?\d{4})\b')
    CPF_PATTERN = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
    NUSP_PATTERN = re.compile(r'\b\d{7,8}\b')  # USP student number
    
    # Fields to always remove
    SENSITIVE_FIELDS = {
        'nome_completo', 'nome', 'email', 'telefone', 'phone',
        'cpf', 'rg', 'nusp', 'endereco', 'address'
    }
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
        """
        Filter sensitive information from a dictionary
        
        Args:
            data: Dictionary to filter
            deep: Whether to recursively filter nested structures
        
        Returns:
            Filtered dictionary
        """
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        
        for key, value in data.items():
            # Skip sensitive fields
            if key.lower() in cls.SENSITIVE_FIELDS:
                continue
            
            # Process nested structures if deep filtering is enabled
            if deep:
                if isinstance(value, dict):
                    filtered[key] = cls.filter_dict(value, deep=True)
                elif isinstance(value, list):
                    filtered[key] = cls.filter_list(value)
                elif isinstance(value, str):
                    filtered[key] = cls.filter_string(value)
                else:
                    filtered[key] = value
            else:
                filtered[key] = value
        
        return filtered
    
    @classmethod
    def filter_list(cls, data: List[Any]) -> List[Any]:
        """Filter sensitive information from a list"""
        filtered = []
        
        for item in data:
            if isinstance(item, dict):
                filtered.append(cls.filter_dict(item, deep=True))
            elif isinstance(item, list):
                filtered.append(cls.filter_list(item))
            elif isinstance(item, str):
                filtered.append(cls.filter_string(item))
            else:
                filtered.append(item)
        
        return filtered
    
    @classmethod
    def filter_string(cls, text: str) -> str:
        """
        Filter sensitive information from a string
        
        Args:
            text: String to filter
        
        Returns:
            Filtered string
        """
        if not text:
            return text
        
        # Replace emails
        text = cls.EMAIL_PATTERN.sub('[EMAIL_REMOVED]', text)
        
        # Replace phone numbers
        text = cls.PHONE_PATTERN.sub('[PHONE_REMOVED]', text)
        
        # Replace CPF
        text = cls.CPF_PATTERN.sub('[CPF_REMOVED]', text)
        
        # Don't replace all numbers as they might be important data
        # Only replace potential NUSP in specific contexts
        
        return text
    
    @classmethod
    def filter_report_data(cls, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter a report's data specifically
        
        Args:
            report_data: Report data from database
        
        Returns:
            Filtered report data
        """
        filtered = report_data.copy()
        
        # Remove entire sections with personal data
        if 'estagiario' in filtered:
            # Keep only non-sensitive fields
            if isinstance(filtered['estagiario'], dict):
                filtered['estagiario'] = {
                    'curso': filtered['estagiario'].get('curso'),
                    # Add other non-sensitive fields as needed
                }
        
        # Remove supervisor entirely
        if 'supervisor' in filtered:
            del filtered['supervisor']
        
        # Keep company information but filter any personal data in text
        if 'sobre_empresa' in filtered:
            filtered['sobre_empresa'] = cls.filter_string(filtered['sobre_empresa'])
        
        if 'conclusao' in filtered:
            filtered['conclusao'] = cls.filter_string(filtered['conclusao'])
        
        # Filter activities
        if 'atividades_realizadas' in filtered and isinstance(filtered['atividades_realizadas'], list):
            filtered['atividades_realizadas'] = cls.filter_list(filtered['atividades_realizadas'])
        
        return filtered
    
    @classmethod
    def filter_response_text(cls, text: str) -> str:
        """
        Final filter for response text before sending to user
        
        Args:
            text: Response text
        
        Returns:
            Filtered text
        """
        # Additional safety check on final response
        text = cls.filter_string(text)
        
        # Remove any remaining personal names (heuristic)
        # This is aggressive and might remove legitimate company names
        # Use with caution
        
        return text
    
    @classmethod
    def validate_safe_response(cls, response: str) -> bool:
        """
        Validate that a response doesn't contain sensitive information
        
        Args:
            response: Response text to validate
        
        Returns:
            True if response appears safe, False otherwise
        """
        # Check for obvious patterns
        if cls.EMAIL_PATTERN.search(response):
            logger.warning("Response contains email address")
            return False
        
        if cls.PHONE_PATTERN.search(response):
            logger.warning("Response contains phone number")
            return False
        
        if cls.CPF_PATTERN.search(response):
            logger.warning("Response contains CPF")
            return False
        
        return True
