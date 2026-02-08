"""
Utility functions for payment processing.
"""
from cryptography.fernet import Fernet
from django.conf import settings
from typing import Tuple


class PhoneNumberEncryption:
    """
    Utility class for encrypting, decrypting, and masking phone numbers.
    Uses Fernet symmetric encryption for secure storage of sensitive phone data.
    """
    
    def __init__(self):
        """Initialize the encryption cipher with the key from settings."""
        encryption_key = getattr(settings, 'PHONE_ENCRYPTION_KEY', None)
        if not encryption_key:
            raise ValueError(
                "PHONE_ENCRYPTION_KEY not found in settings. "
                "Generate one with: Fernet.generate_key()"
            )
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt(self, phone_number: str) -> str:
        """
        Encrypt a phone number for secure storage.
        
        Args:
            phone_number: Plain text phone number (e.g., "256708123456")
        
        Returns:
            Encrypted phone number as a string
        
        Example:
            >>> encryptor = PhoneNumberEncryption()
            >>> encrypted = encryptor.encrypt("256708123456")
            >>> encrypted
            'gAAAAABh...'
        """
        if not phone_number:
            raise ValueError("Phone number cannot be empty")
        
        encrypted_bytes = self.cipher.encrypt(phone_number.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, encrypted_phone: str) -> str:
        """
        Decrypt an encrypted phone number.
        
        Args:
            encrypted_phone: Encrypted phone number string
        
        Returns:
            Decrypted plain text phone number
        
        Example:
            >>> encryptor = PhoneNumberEncryption()
            >>> encrypted = encryptor.encrypt("256708123456")
            >>> decrypted = encryptor.decrypt(encrypted)
            >>> decrypted
            '256708123456'
        """
        if not encrypted_phone:
            raise ValueError("Encrypted phone number cannot be empty")
        
        decrypted_bytes = self.cipher.decrypt(encrypted_phone.encode())
        return decrypted_bytes.decode()
    
    def mask(self, phone_number: str) -> str:
        """
        Return a masked version of the phone number showing only first 3 and last 4 digits.
        
        Args:
            phone_number: Plain text phone number (e.g., "256708123456")
        
        Returns:
            Masked phone number (e.g., "256****3456")
        
        Example:
            >>> encryptor = PhoneNumberEncryption()
            >>> masked = encryptor.mask("256708123456")
            >>> masked
            '256****3456'
        """
        if not phone_number:
            return '****'
        
        if len(phone_number) < 8:
            return '****'
        
        return f"{phone_number[:3]}****{phone_number[-4:]}"


def validate_phone_number(phone_number: str) -> Tuple[bool, str]:
    """
    Validate phone number format for Uganda mobile money.
    
    Expected format: 256XXXXXXXXX (exactly 12 characters)
    - Must start with '256' (Uganda country code)
    - Must be exactly 12 characters long
    - All characters after '256' must be digits
    
    Args:
        phone_number: Phone number string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if phone number is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
    
    Examples:
        >>> validate_phone_number("256708123456")
        (True, '')
        
        >>> validate_phone_number("256708")
        (False, 'Phone number must be exactly 12 characters long')
        
        >>> validate_phone_number("255708123456")
        (False, 'Phone number must start with 256 (Uganda country code)')
        
        >>> validate_phone_number("256abc123456")
        (False, 'Phone number must contain only digits after country code')
    """
    if not phone_number:
        return False, "Phone number is required"
    
    if not isinstance(phone_number, str):
        return False, "Phone number must be a string"
    
    if len(phone_number) != 12:
        return False, "Phone number must be exactly 12 characters long"
    
    if not phone_number.startswith('256'):
        return False, "Phone number must start with 256 (Uganda country code)"
    
    if not phone_number[3:].isdigit():
        return False, "Phone number must contain only digits after country code"
    
    return True, ""
