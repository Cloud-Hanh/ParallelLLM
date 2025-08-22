"""
Tests for output format validation functionality.

This module tests the various output validators and their integration
with the Client class for automatic validation and retry.
"""

import json
import re
import unittest
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os

from src.pllm.validators import (
    OutputValidator, JsonValidator, TextValidator, RegexValidator,
    ValidationResult
)
from src.pllm.client import Client


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass."""
    
    def test_valid_result(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(is_valid=True, parsed_output={"key": "value"})
        
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.parsed_output, {"key": "value"})
        self.assertIsNone(result.retry_prompt)
    
    def test_invalid_result(self):
        """Test creating an invalid ValidationResult."""
        result = ValidationResult(
            is_valid=False,
            error_message="Invalid format",
            retry_prompt="Please fix the format"
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "Invalid format")
        self.assertEqual(result.retry_prompt, "Please fix the format")
        self.assertIsNone(result.parsed_output)


class TestJsonValidator(unittest.TestCase):
    """Test JsonValidator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = JsonValidator(max_retries=2)
    
    def test_valid_json_object(self):
        """Test validation of valid JSON object."""
        valid_json = '{"name": "John", "age": 30}'
        result = self.validator.validate(valid_json)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.parsed_output, {"name": "John", "age": 30})
        self.assertIsNone(result.error_message)
    
    def test_valid_json_array(self):
        """Test validation of valid JSON array."""
        valid_json = '[1, 2, 3, "test"]'
        result = self.validator.validate(valid_json)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.parsed_output, [1, 2, 3, "test"])
    
    def test_invalid_json_syntax(self):
        """Test validation of invalid JSON syntax."""
        invalid_json = '{"name": "John", "age": 30'  # Missing closing brace
        result = self.validator.validate(invalid_json)
        
        self.assertFalse(result.is_valid)
        # In non-strict mode, it tries to extract JSON and fails to find valid JSON
        self.assertIn("No valid JSON found", result.error_message)
        self.assertIsNotNone(result.retry_prompt)
    
    def test_extract_json_from_text(self):
        """Test extracting JSON from mixed text (non-strict mode)."""
        text_with_json = '''
        Here is the requested data:
        {"name": "Alice", "score": 95}
        Hope this helps!
        '''
        
        validator = JsonValidator(strict=False, extract_json=True)
        result = validator.validate(text_with_json)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.parsed_output, '{"name": "Alice", "score": 95}')
    
    def test_strict_mode_rejects_mixed_text(self):
        """Test that strict mode rejects mixed text."""
        text_with_json = '''
        Here is the data: {"name": "Bob"}
        '''
        
        validator = JsonValidator(strict=True)
        result = validator.validate(text_with_json)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid JSON format", result.error_message)
    
    def test_json_schema_validation_success(self):
        """Test successful JSON schema validation."""
        try:
            import jsonschema
            
            schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number", "minimum": 0}
                },
                "required": ["name", "age"]
            }
            
            validator = JsonValidator(schema=schema)
            valid_json = '{"name": "Charlie", "age": 25}'
            result = validator.validate(valid_json)
            
            self.assertTrue(result.is_valid)
            self.assertEqual(result.parsed_output, {"name": "Charlie", "age": 25})
            
        except ImportError:
            self.skipTest("jsonschema not installed")
    
    def test_json_schema_validation_failure(self):
        """Test failed JSON schema validation."""
        try:
            import jsonschema
            
            schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number", "minimum": 0}
                },
                "required": ["name", "age"]
            }
            
            validator = JsonValidator(schema=schema)
            invalid_json = '{"name": "Dave"}'  # Missing required "age" field
            result = validator.validate(invalid_json)
            
            self.assertFalse(result.is_valid)
            self.assertIn("JSON schema validation failed", result.error_message)
            
        except ImportError:
            self.skipTest("jsonschema not installed")
    
    def test_no_json_found_in_text(self):
        """Test when no JSON is found in text."""
        text_without_json = "This is just plain text with no JSON content."
        
        validator = JsonValidator(strict=False, extract_json=True)
        result = validator.validate(text_without_json)
        
        self.assertFalse(result.is_valid)
        self.assertIn("No valid JSON found", result.error_message)
    
    def test_retry_prompt_generation(self):
        """Test retry prompt generation for JSON validation failures."""
        invalid_json = '{"incomplete": true'
        result = self.validator.validate(invalid_json)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Your previous response had a JSON format error", result.retry_prompt)
        self.assertIn(invalid_json, result.retry_prompt)


class TestTextValidator(unittest.TestCase):
    """Test TextValidator functionality."""
    
    def test_custom_validator_function_success(self):
        """Test successful custom validation function."""
        def check_contains_keyword(text):
            return "important" in text.lower()
        
        validator = TextValidator(
            requirements="Text must contain the word 'important'",
            validator_func=check_contains_keyword
        )
        
        valid_text = "This is an important message."
        result = validator.validate(valid_text)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.parsed_output, valid_text)
    
    def test_custom_validator_function_failure(self):
        """Test failed custom validation function."""
        def check_contains_keyword(text):
            return "important" in text.lower()
        
        validator = TextValidator(
            requirements="Text must contain the word 'important'",
            validator_func=check_contains_keyword
        )
        
        invalid_text = "This is just a regular message."
        result = validator.validate(invalid_text)
        
        self.assertFalse(result.is_valid)
        self.assertIn("does not meet requirements", result.error_message)
        self.assertIn("Custom validation failed", result.retry_prompt)
    
    def test_validator_function_exception(self):
        """Test handling of validator function exceptions."""
        def faulty_validator(text):
            raise ValueError("Something went wrong")
        
        validator = TextValidator(
            requirements="Should not crash",
            validator_func=faulty_validator
        )
        
        result = validator.validate("any text")
        
        self.assertFalse(result.is_valid)
        self.assertIn("Validation function error", result.error_message)
    
    def test_no_validator_always_valid(self):
        """Test that without validator function, text is always valid."""
        validator = TextValidator(requirements="Any text is fine")
        
        result = validator.validate("This could be anything")
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.parsed_output, "This could be anything")
    
    def test_retry_prompt_generation(self):
        """Test retry prompt generation for text validation failures."""
        def always_fail(text):
            return False
        
        validator = TextValidator(
            requirements="Must be perfect",
            validator_func=always_fail
        )
        
        result = validator.validate("imperfect text")
        
        self.assertFalse(result.is_valid)
        self.assertIn("Your previous response did not meet the format requirements", result.retry_prompt)
        self.assertIn("Must be perfect", result.retry_prompt)
        self.assertIn("imperfect text", result.retry_prompt)


class TestRegexValidator(unittest.TestCase):
    """Test RegexValidator functionality."""
    
    def test_email_pattern_matching(self):
        """Test email pattern validation."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        validator = RegexValidator(
            pattern=email_pattern,
            requirements_description="Must be a valid email address"
        )
        
        # Test valid email
        valid_email = "user@example.com"
        result = validator.validate(valid_email)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.parsed_output, valid_email)
        
        # Test invalid email
        invalid_email = "not-an-email"
        result = validator.validate(invalid_email)
        self.assertFalse(result.is_valid)
        self.assertIn("does not match required pattern", result.error_message)
    
    def test_phone_number_pattern(self):
        """Test phone number pattern validation."""
        phone_pattern = r'^\+?1?-?\.?\s?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$'
        validator = RegexValidator(
            pattern=phone_pattern,
            requirements_description="Must be a valid US phone number"
        )
        
        # Test valid phone numbers
        valid_phones = [
            "123-456-7890",
            "(123) 456-7890",
            "123.456.7890",
            "+1-123-456-7890"
        ]
        
        for phone in valid_phones:
            result = validator.validate(phone)
            self.assertTrue(result.is_valid, f"Phone {phone} should be valid")
        
        # Test invalid phone number
        invalid_phone = "123-45-678"
        result = validator.validate(invalid_phone)
        self.assertFalse(result.is_valid)
    
    def test_compiled_regex_pattern(self):
        """Test using pre-compiled regex pattern."""
        compiled_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        validator = RegexValidator(
            pattern=compiled_pattern,
            requirements_description="Must be YYYY-MM-DD date format"
        )
        
        # Test valid date
        valid_date = "2023-12-25"
        result = validator.validate(valid_date)
        self.assertTrue(result.is_valid)
        
        # Test invalid date
        invalid_date = "25-12-2023"
        result = validator.validate(invalid_date)
        self.assertFalse(result.is_valid)
    
    def test_case_insensitive_matching(self):
        """Test case insensitive regex matching."""
        validator = RegexValidator(
            pattern=r'^hello world$',
            flags=re.IGNORECASE,
            requirements_description="Must say 'hello world' (case insensitive)"
        )
        
        # Test various cases
        valid_inputs = ["hello world", "Hello World", "HELLO WORLD", "Hello WORLD"]
        
        for input_text in valid_inputs:
            result = validator.validate(input_text)
            self.assertTrue(result.is_valid, f"'{input_text}' should match")
    
    def test_retry_prompt_generation(self):
        """Test retry prompt generation for regex validation failures."""
        validator = RegexValidator(
            pattern=r'^\d+$',
            requirements_description="Must be all digits"
        )
        
        invalid_input = "abc123"
        result = validator.validate(invalid_input)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Your previous response did not match the required format", result.retry_prompt)
        self.assertIn("Must be all digits", result.retry_prompt)
        self.assertIn("abc123", result.retry_prompt)


class TestClientIntegration(unittest.TestCase):
    """Test integration of validators with Client class."""
    
    def setUp(self):
        """Set up test fixtures with mock client."""
        # Create a temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        config_content = """
llm:
  use: "mock"
  mock:
    - api_key: "test"
      model: "test-model"
      rate_limit: 10
"""
        self.temp_config.write(config_content)
        self.temp_config.close()
        
        # We'll need to mock the LoadBalancer since we don't have real API keys
        with patch('src.pllm.client.LoadBalancer'):
            self.client = Client(self.temp_config.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_config.name)
    
    @patch('src.pllm.client.LoadBalancer')
    def test_generate_with_valid_json_validator(self, mock_balancer_class):
        """Test generate method with JSON validator that succeeds."""
        # Mock the balancer to return valid JSON
        mock_balancer_instance = Mock()
        mock_balancer_instance.execute_request = AsyncMock(return_value='{"result": "success"}')
        mock_balancer_instance._all_providers = Mock(return_value=iter([]))  # Return empty iterator
        mock_balancer_class.return_value = mock_balancer_instance
        
        client = Client(self.temp_config.name)
        validator = JsonValidator()
        
        # This should work since the mock returns valid JSON
        result = client.invoke("Generate a JSON response", output_validator=validator)
        
        self.assertEqual(result, '{"result": "success"}')
        mock_balancer_instance.execute_request.assert_called_once()
    
    @patch('src.pllm.client.LoadBalancer')
    def test_generate_with_json_validator_retry(self, mock_balancer_class):
        """Test generate method with JSON validator that needs retry."""
        # Mock the balancer to return invalid JSON first, then valid JSON
        mock_balancer_instance = Mock()
        mock_balancer_instance.execute_request = AsyncMock(
            side_effect=[
                'This is not JSON',  # First call returns invalid JSON
                '{"result": "success"}'  # Second call returns valid JSON
            ]
        )
        mock_balancer_instance._all_providers = Mock(return_value=iter([]))
        mock_balancer_class.return_value = mock_balancer_instance
        
        client = Client(self.temp_config.name)
        validator = JsonValidator(max_retries=2)
        
        # This should succeed after retry
        result = client.invoke("Generate a JSON response", output_validator=validator)
        
        self.assertEqual(result, '{"result": "success"}')
        # Should be called twice (original + 1 retry)
        self.assertEqual(mock_balancer_instance.execute_request.call_count, 2)
        
        # Check that retry prompt was added to the conversation
        second_call_args = mock_balancer_instance.execute_request.call_args_list[1]
        messages = second_call_args[1]['messages']  # Get messages from kwargs
        
        # Should have original message + assistant response + retry prompt
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]['content'], "Generate a JSON response")
        self.assertEqual(messages[1]['content'], "This is not JSON")
        self.assertIn("JSON format error", messages[2]['content'])
    
    @patch('src.pllm.client.LoadBalancer')
    def test_generate_with_validator_max_retries_exceeded(self, mock_balancer_class):
        """Test generate method when max retries is exceeded."""
        # Mock the balancer to always return invalid JSON
        mock_balancer_instance = Mock()
        mock_balancer_instance.execute_request = AsyncMock(return_value='invalid json content')
        mock_balancer_instance._all_providers = Mock(return_value=iter([]))
        mock_balancer_class.return_value = mock_balancer_instance
        
        client = Client(self.temp_config.name)
        validator = JsonValidator(max_retries=1)
        
        # This should raise ValueError after max retries
        with self.assertRaises(ValueError) as context:
            client.invoke("Generate a JSON response", output_validator=validator)
        
        self.assertIn("Output validation failed after 2 attempts", str(context.exception))
        # Should be called twice (original + 1 retry)
        self.assertEqual(mock_balancer_instance.execute_request.call_count, 2)
    
    @patch('src.pllm.client.LoadBalancer')
    def test_generate_with_text_validator(self, mock_balancer_class):
        """Test generate method with text validator."""
        mock_balancer_instance = Mock()
        mock_balancer_instance.execute_request = AsyncMock(return_value='This response contains the keyword!')
        mock_balancer_instance._all_providers = Mock(return_value=iter([]))
        mock_balancer_class.return_value = mock_balancer_instance
        
        client = Client(self.temp_config.name)
        
        def check_keyword(text):
            return 'keyword' in text
        
        validator = TextValidator(
            requirements="Must contain the word 'keyword'",
            validator_func=check_keyword
        )
        
        result = client.invoke("Generate text with specific keyword", output_validator=validator)
        
        self.assertEqual(result, 'This response contains the keyword!')
        mock_balancer_instance.execute_request.assert_called_once()
    
    @patch('src.pllm.client.LoadBalancer')
    def test_invoke_batch_with_validator(self, mock_balancer_class):
        """Test invoke_batch method with validator."""
        mock_balancer_instance = Mock()
        mock_balancer_instance.execute_request = AsyncMock(
            side_effect=['{"result": 1}', '{"result": 2}', '{"result": 3}']
        )
        mock_balancer_instance._all_providers = Mock(return_value=iter([]))
        mock_balancer_class.return_value = mock_balancer_instance
        
        client = Client(self.temp_config.name)
        validator = JsonValidator()
        
        prompts = ["Generate JSON 1", "Generate JSON 2", "Generate JSON 3"]
        results = client.invoke_batch(prompts, output_validator=validator)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], '{"result": 1}')
        self.assertEqual(results[1], '{"result": 2}')
        self.assertEqual(results[2], '{"result": 3}')
        
        # Should be called 3 times (once for each prompt)
        self.assertEqual(mock_balancer_instance.execute_request.call_count, 3)


if __name__ == '__main__':
    unittest.main()