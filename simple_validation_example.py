"""
Simple practical example of using output validation with ParallelLLM.

This example shows real usage scenarios with output format validation.
"""

import json
from src.pllm.client import Client
from src.pllm.validators import JsonValidator, TextValidator, RegexValidator


def example_json_validation():
    """Example of JSON format validation."""
    print("🔧 JSON Validation Example")
    print("-" * 30)
    
    # Create a JSON validator that can extract JSON from mixed text
    validator = JsonValidator(
        strict=False,       # Allow mixed text with JSON
        extract_json=True,  # Extract JSON from response
        max_retries=3       # Retry up to 3 times if validation fails
    )
    
    # Simulate usage (would work with real client)
    prompt = "Create a user profile in JSON format with name, age, and city"
    
    print(f"Prompt: {prompt}")
    print(f"Validator: JSON format (non-strict, extraction enabled)")
    print()
    
    # This would automatically validate and retry if needed:
    # result = client.invoke(prompt, output_validator=validator)
    
    # Simulate validation process
    print("Validation process:")
    print("1. First attempt - mixed text response:")
    mixed_response = 'Here is the user profile: {"name": "Alice", "age": 28, "city": "NYC"}'
    result = validator.validate(mixed_response)
    print(f"   Response: {mixed_response}")
    print(f"   Valid: {result.is_valid}")
    print(f"   Extracted: {result.parsed_output}")
    print()


def example_schema_validation():
    """Example of JSON schema validation."""
    print("📋 JSON Schema Validation Example")
    print("-" * 35)
    
    # Define a schema for product data
    product_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "price": {"type": "number", "minimum": 0},
            "category": {"type": "string"},
            "in_stock": {"type": "boolean"}
        },
        "required": ["name", "price", "category"]
    }
    
    try:
        validator = JsonValidator(
            schema=product_schema,
            strict=True,
            max_retries=2
        )
        
        print("Schema:", json.dumps(product_schema, indent=2))
        print()
        
        # Test valid JSON
        valid_json = '{"name": "Laptop", "price": 999.99, "category": "Electronics", "in_stock": true}'
        result = validator.validate(valid_json)
        print(f"Valid JSON test: {result.is_valid}")
        print(f"Data: {result.parsed_output}")
        print()
        
        # Test invalid JSON (missing required field)
        invalid_json = '{"name": "Mouse", "price": 29.99}'  # Missing category
        result = validator.validate(invalid_json)
        print(f"Invalid JSON test: {result.is_valid}")
        print(f"Error: {result.error_message}")
        print()
        
    except ImportError:
        print("⚠️ jsonschema package not installed")
        print("Install with: pip install jsonschema")
        print()


def example_custom_text_validation():
    """Example of custom text validation."""
    print("✅ Custom Text Validation Example")
    print("-" * 35)
    
    def contains_greeting_and_farewell(text):
        """Check if text contains both greeting and farewell."""
        text_lower = text.lower()
        has_greeting = any(greeting in text_lower for greeting in ["hello", "hi", "greetings"])
        has_farewell = any(farewell in text_lower for farewell in ["goodbye", "bye", "farewell"])
        return has_greeting and has_farewell
    
    validator = TextValidator(
        requirements="Must include both a greeting and a farewell",
        validator_func=contains_greeting_and_farewell,
        max_retries=2
    )
    
    # Test valid text
    valid_text = "Hello! Welcome to our service. We hope you enjoy it. Goodbye!"
    result = validator.validate(valid_text)
    print(f"Valid text: {result.is_valid}")
    print(f"Text: {valid_text}")
    print()
    
    # Test invalid text
    invalid_text = "Welcome to our service. We hope you enjoy it."
    result = validator.validate(invalid_text)
    print(f"Invalid text: {result.is_valid}")
    print(f"Text: {invalid_text}")
    print(f"Error: {result.error_message}")
    print()


def example_regex_validation():
    """Example of regex pattern validation."""
    print("🔍 Regex Pattern Validation Example")
    print("-" * 35)
    
    # Email pattern validator
    email_validator = RegexValidator(
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        requirements_description="Must be a valid email address format",
        max_retries=2
    )
    
    # Test valid email
    valid_email = "user@example.com"
    result = email_validator.validate(valid_email)
    print(f"Valid email: {result.is_valid}")
    print(f"Email: {valid_email}")
    print()
    
    # Test invalid email
    invalid_email = "not-an-email"
    result = email_validator.validate(invalid_email)
    print(f"Invalid email: {result.is_valid}")
    print(f"Text: {invalid_email}")
    print(f"Error: {result.error_message}")
    print()


def main():
    """Run all validation examples."""
    print("🤖 ParallelLLM Output Validation Examples")
    print("=" * 50)
    print()
    
    example_json_validation()
    example_schema_validation()
    example_custom_text_validation()
    example_regex_validation()
    
    print("💡 Integration with Client:")
    print("All these validators can be used with any Client method:")
    print()
    print("client.invoke(prompt, output_validator=validator)")
    print("client.generate(prompt, output_validator=validator)")
    print("client.chat(messages, output_validator=validator)")
    print("client.invoke_batch(prompts, output_validator=validator)")
    print()
    print("The client will automatically retry with improved prompts")
    print("if validation fails, up to the maximum retry limit.")


if __name__ == "__main__":
    main()