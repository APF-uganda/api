"""
Property-based tests for phone number encryption.

Feature: mobile-money-payment-integration
Property 5: Sensitive Data Encryption

For any Payment_Transaction record stored in the database, the phone_number field 
should be encrypted such that the stored value is different from the plaintext value, 
and decrypting the stored value should return the original plaintext phone number.

Validates: Requirements 3.5, 7.5
"""
import pytest
from hypothesis import given, strategies as st, settings
from payments.utils import PhoneNumberEncryption


# Strategy for generating valid phone numbers
valid_phone_numbers = st.builds(
    lambda digits: f"256{digits}",
    digits=st.text(alphabet='0123456789', min_size=9, max_size=9)
)

# Strategy for generating any text (including invalid phone numbers)
any_text = st.text(min_size=1, max_size=50)


class TestPhoneNumberEncryptionProperties:
    """Property-based tests for phone number encryption."""
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_encryption_produces_different_value(self, phone_number):
        """
        Property: Encrypted value must be different from plaintext.
        
        For any valid phone number, the encrypted value should not equal 
        the original plaintext value.
        """
        encryptor = PhoneNumberEncryption()
        encrypted = encryptor.encrypt(phone_number)
        
        # Encrypted value must be different from plaintext
        assert encrypted != phone_number, \
            f"Encrypted value should differ from plaintext: {phone_number}"
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_decrypt_returns_original_value(self, phone_number):
        """
        Property: Decryption must return the original plaintext.
        
        For any valid phone number, encrypting and then decrypting 
        should return the exact original value.
        """
        encryptor = PhoneNumberEncryption()
        encrypted = encryptor.encrypt(phone_number)
        decrypted = encryptor.decrypt(encrypted)
        
        # Decrypted value must equal original plaintext
        assert decrypted == phone_number, \
            f"Decrypted value must equal original: expected {phone_number}, got {decrypted}"
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_encryption_is_deterministic(self, phone_number):
        """
        Property: Encrypting the same value twice produces different ciphertexts.
        
        Fernet encryption includes a timestamp and random IV, so encrypting 
        the same plaintext twice should produce different ciphertexts.
        This is a security feature to prevent pattern analysis.
        """
        encryptor = PhoneNumberEncryption()
        encrypted1 = encryptor.encrypt(phone_number)
        encrypted2 = encryptor.encrypt(phone_number)
        
        # Due to Fernet's use of timestamp and IV, encryptions should differ
        # (This is actually non-deterministic encryption, which is more secure)
        assert encrypted1 != encrypted2, \
            "Fernet encryption should produce different ciphertexts for same plaintext"
        
        # But both should decrypt to the same original value
        decrypted1 = encryptor.decrypt(encrypted1)
        decrypted2 = encryptor.decrypt(encrypted2)
        assert decrypted1 == phone_number
        assert decrypted2 == phone_number
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_encrypted_value_is_string(self, phone_number):
        """
        Property: Encrypted value must be a string.
        
        For any valid phone number, the encrypted value should be 
        a string type (for database storage).
        """
        encryptor = PhoneNumberEncryption()
        encrypted = encryptor.encrypt(phone_number)
        
        assert isinstance(encrypted, str), \
            f"Encrypted value must be a string, got {type(encrypted)}"
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_encrypted_value_is_not_empty(self, phone_number):
        """
        Property: Encrypted value must not be empty.
        
        For any valid phone number, the encrypted value should have 
        non-zero length.
        """
        encryptor = PhoneNumberEncryption()
        encrypted = encryptor.encrypt(phone_number)
        
        assert len(encrypted) > 0, \
            "Encrypted value must not be empty"
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_mask_hides_middle_digits(self, phone_number):
        """
        Property: Masked phone number must hide middle digits.
        
        For any valid phone number (256XXXXXXXXX), the masked version 
        should show only first 3 digits (256) and last 4 digits, 
        with **** in the middle.
        """
        encryptor = PhoneNumberEncryption()
        masked = encryptor.mask(phone_number)
        
        # Check format: 256****XXXX
        assert masked.startswith('256'), \
            f"Masked number should start with '256', got {masked}"
        assert '****' in masked, \
            f"Masked number should contain '****', got {masked}"
        assert masked.endswith(phone_number[-4:]), \
            f"Masked number should end with last 4 digits of {phone_number}, got {masked}"
        assert len(masked) == 11, \
            f"Masked number should be 11 characters (256****XXXX), got {len(masked)}"
    
    @given(text=any_text)
    @settings(max_examples=100)
    def test_encrypt_any_text_succeeds(self, text):
        """
        Property: Encryption should work for any non-empty text.
        
        The encryption function should be able to encrypt any string,
        not just valid phone numbers.
        """
        encryptor = PhoneNumberEncryption()
        
        # Should not raise an exception
        encrypted = encryptor.encrypt(text)
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        
        # Should be able to decrypt back
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == text
    
    def test_encrypt_empty_string_raises_error(self):
        """
        Property: Encrypting empty string should raise ValueError.
        """
        encryptor = PhoneNumberEncryption()
        
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            encryptor.encrypt("")
    
    def test_decrypt_empty_string_raises_error(self):
        """
        Property: Decrypting empty string should raise ValueError.
        """
        encryptor = PhoneNumberEncryption()
        
        with pytest.raises(ValueError, match="Encrypted phone number cannot be empty"):
            encryptor.decrypt("")
    
    def test_mask_empty_string_returns_placeholder(self):
        """
        Property: Masking empty string should return placeholder.
        """
        encryptor = PhoneNumberEncryption()
        masked = encryptor.mask("")
        
        assert masked == '****', \
            f"Masking empty string should return '****', got {masked}"
    
    @given(short_text=st.text(min_size=1, max_size=7))
    @settings(max_examples=100)
    def test_mask_short_text_returns_placeholder(self, short_text):
        """
        Property: Masking text shorter than 8 characters returns placeholder.
        """
        encryptor = PhoneNumberEncryption()
        masked = encryptor.mask(short_text)
        
        assert masked == '****', \
            f"Masking short text should return '****', got {masked}"
