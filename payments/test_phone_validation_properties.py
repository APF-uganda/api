"""
Property-based tests for phone number validation.

Feature: mobile-money-payment-integration
Property 1: Phone Number Validation

For any string input to the phone number field, the validation function should 
return true only if the string matches the format 256XXXXXXXXX (where X is a 
digit 0-9) and has exactly 12 characters.

Validates: Requirements 1.2, 2.2
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from payments.utils import validate_phone_number


# Strategy for generating valid phone numbers (256 + 9 digits)
valid_phone_numbers = st.builds(
    lambda digits: f"256{digits}",
    digits=st.text(alphabet='0123456789', min_size=9, max_size=9)
)

# Strategy for generating invalid phone numbers with wrong length
wrong_length_phones = st.one_of(
    st.text(min_size=0, max_size=11),  # Too short
    st.text(min_size=13, max_size=50)  # Too long
)

# Strategy for generating phone numbers with wrong prefix
wrong_prefix_phones = st.builds(
    lambda prefix, digits: f"{prefix}{digits}",
    prefix=st.text(alphabet='0123456789', min_size=3, max_size=3).filter(lambda x: x != '256'),
    digits=st.text(alphabet='0123456789', min_size=9, max_size=9)
)

# Strategy for generating phone numbers with non-digit characters after prefix
non_digit_phones = st.builds(
    lambda suffix: f"256{suffix}",
    suffix=st.text(min_size=9, max_size=9).filter(lambda x: not x.isdigit())
)

# Strategy for any text
any_text = st.text(min_size=0, max_size=50)


class TestPhoneNumberValidationProperties:
    """Property-based tests for phone number validation."""
    
    @given(phone_number=valid_phone_numbers)
    @settings(max_examples=100)
    def test_valid_phone_numbers_pass_validation(self, phone_number):
        """
        Property: All valid phone numbers (256XXXXXXXXX) should pass validation.
        
        For any phone number that starts with '256' and has exactly 9 more digits,
        validation should return (True, '').
        """
        is_valid, error_message = validate_phone_number(phone_number)
        
        assert is_valid is True, \
            f"Valid phone number {phone_number} should pass validation"
        assert error_message == '', \
            f"Valid phone number should have empty error message, got: {error_message}"
    
    @given(phone_number=wrong_length_phones)
    @settings(max_examples=100)
    def test_wrong_length_phones_fail_validation(self, phone_number):
        """
        Property: Phone numbers with length != 12 should fail validation.
        
        For any phone number that doesn't have exactly 12 characters,
        validation should return (False, error_message).
        """
        assume(len(phone_number) != 12)  # Skip if accidentally generated 12 chars
        assume(phone_number != '')  # Skip empty strings (handled by separate check)
        
        is_valid, error_message = validate_phone_number(phone_number)
        
        assert is_valid is False, \
            f"Phone number with wrong length {len(phone_number)} should fail validation"
        assert error_message != '', \
            "Invalid phone number should have non-empty error message"
        # Empty strings get "required" message, others get "12 characters" message
        if phone_number:
            assert "12 characters" in error_message, \
                f"Error message should mention '12 characters', got: {error_message}"
    
    @given(phone_number=wrong_prefix_phones)
    @settings(max_examples=100)
    def test_wrong_prefix_phones_fail_validation(self, phone_number):
        """
        Property: Phone numbers not starting with '256' should fail validation.
        
        For any 12-character phone number that doesn't start with '256',
        validation should return (False, error_message).
        """
        is_valid, error_message = validate_phone_number(phone_number)
        
        assert is_valid is False, \
            f"Phone number with wrong prefix should fail validation: {phone_number}"
        assert error_message != '', \
            "Invalid phone number should have non-empty error message"
        assert "256" in error_message, \
            f"Error message should mention '256', got: {error_message}"
    
    @given(phone_number=non_digit_phones)
    @settings(max_examples=100)
    def test_non_digit_phones_fail_validation(self, phone_number):
        """
        Property: Phone numbers with non-digit characters after '256' should fail.
        
        For any phone number starting with '256' but containing non-digit 
        characters in the remaining 9 positions, validation should fail.
        """
        is_valid, error_message = validate_phone_number(phone_number)
        
        assert is_valid is False, \
            f"Phone number with non-digits should fail validation: {phone_number}"
        assert error_message != '', \
            "Invalid phone number should have non-empty error message"
        assert "digits" in error_message.lower(), \
            f"Error message should mention 'digits', got: {error_message}"
    
    @given(text=any_text)
    @settings(max_examples=100)
    def test_validation_returns_tuple(self, text):
        """
        Property: Validation should always return a tuple of (bool, str).
        
        For any input text, the validation function should return a tuple
        with a boolean as first element and a string as second element.
        """
        result = validate_phone_number(text)
        
        assert isinstance(result, tuple), \
            f"Validation should return a tuple, got {type(result)}"
        assert len(result) == 2, \
            f"Validation should return 2-element tuple, got {len(result)} elements"
        
        is_valid, error_message = result
        assert isinstance(is_valid, bool), \
            f"First element should be bool, got {type(is_valid)}"
        assert isinstance(error_message, str), \
            f"Second element should be str, got {type(error_message)}"
    
    @given(text=any_text)
    @settings(max_examples=100)
    def test_validation_logic_consistency(self, text):
        """
        Property: Validation logic should be consistent.
        
        For any input, if is_valid is True, error_message should be empty.
        If is_valid is False, error_message should be non-empty.
        """
        is_valid, error_message = validate_phone_number(text)
        
        if is_valid:
            assert error_message == '', \
                f"Valid input should have empty error message, got: {error_message}"
        else:
            assert error_message != '', \
                "Invalid input should have non-empty error message"
    
    @given(text=any_text)
    @settings(max_examples=100)
    def test_validation_matches_format_exactly(self, text):
        """
        Property: Validation should match the exact format 256XXXXXXXXX.
        
        For any input text, validation should return True if and only if:
        - Length is exactly 12
        - Starts with '256'
        - Remaining 9 characters are all digits
        """
        is_valid, _ = validate_phone_number(text)
        
        # Check if text matches the expected format
        expected_valid = (
            isinstance(text, str) and
            len(text) == 12 and
            text.startswith('256') and
            text[3:].isdigit()
        )
        
        assert is_valid == expected_valid, \
            f"Validation result {is_valid} doesn't match expected {expected_valid} for: {text}"
    
    def test_empty_string_fails_validation(self):
        """
        Property: Empty string should fail validation.
        """
        is_valid, error_message = validate_phone_number("")
        
        assert is_valid is False, \
            "Empty string should fail validation"
        assert "required" in error_message.lower(), \
            f"Error message should mention 'required', got: {error_message}"
    
    def test_none_value_fails_validation(self):
        """
        Property: None value should fail validation.
        """
        is_valid, error_message = validate_phone_number(None)
        
        assert is_valid is False, \
            "None value should fail validation"
        assert error_message != '', \
            "None value should have error message"
    
    @given(number=st.integers())
    @settings(max_examples=100)
    def test_non_string_types_fail_validation(self, number):
        """
        Property: Non-string types should fail validation.
        
        For any non-string input (e.g., integers), validation should fail.
        Note: The validation function checks for empty/None first, so
        non-string types get "required" message rather than "must be string".
        """
        is_valid, error_message = validate_phone_number(number)
        
        assert is_valid is False, \
            f"Non-string type {type(number)} should fail validation"
        assert error_message != '', \
            f"Non-string type should have error message"
        # The validation checks for empty/None first, so we get "required" message
        assert "required" in error_message.lower() or "string" in error_message.lower(), \
            f"Error message should mention 'required' or 'string', got: {error_message}"
    
    def test_specific_valid_examples(self):
        """
        Test specific valid phone number examples.
        """
        valid_examples = [
            "256700000000",
            "256701234567",
            "256777777777",
            "256788888888",
            "256799999999",
        ]
        
        for phone in valid_examples:
            is_valid, error_message = validate_phone_number(phone)
            assert is_valid is True, \
                f"Valid example {phone} should pass validation"
            assert error_message == '', \
                f"Valid example should have empty error message"
    
    def test_specific_invalid_examples(self):
        """
        Test specific invalid phone number examples.
        """
        invalid_examples = [
            ("256", "too short"),
            ("25670000000", "11 chars - too short"),
            ("2567000000000", "13 chars - too long"),
            ("255700000000", "wrong country code"),
            ("356700000000", "wrong country code"),
            ("256abc123456", "contains letters"),
            ("256 70000000", "contains space"),
            ("256-70000000", "contains dash"),
            ("+256700000000", "contains plus sign"),
        ]
        
        for phone, description in invalid_examples:
            is_valid, error_message = validate_phone_number(phone)
            assert is_valid is False, \
                f"Invalid example {phone} ({description}) should fail validation"
            assert error_message != '', \
                f"Invalid example should have error message"
