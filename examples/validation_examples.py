"""
Example usage of output format validation in ParallelLLM.

This script demonstrates how to use the various output validators
to ensure LLM responses conform to specific formats.
"""

import json
import re
from src.pllm.client import Client
from src.pllm.validators import JsonValidator, TextValidator, RegexValidator


def main():
    """Demonstrate various output validation examples."""
    
    print("🤖 ParallelLLM Output Validation Examples")
    print("=" * 50)
    
    # Note: This example assumes you have a valid config file
    # For demo purposes, we'll show the code structure
    config_path = "examples/example_config.yaml"
    
    try:
        client = Client(config_path)
    except Exception as e:
        print(f"⚠️  Note: Could not initialize client: {e}")
        print("This example shows the code structure for using validators.\n")
    
    # Example 1: JSON Format Validation
    print("📝 Example 1: JSON Format Validation")
    print("-" * 30)
    
    json_validator = JsonValidator(
        max_retries=3,
        strict=False,  # Allow extraction from mixed text
        extract_json=True
    )
    
    print("Validator created for JSON format validation.")
    print("Example usage:")
    print("""
    result = client.invoke(
        "Generate a JSON object with user info including name and age",
        output_validator=json_validator
    )
    """)
    print()
    
    # Example 2: JSON Schema Validation
    print("📋 Example 2: JSON Schema Validation")
    print("-" * 35)
    
    user_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number", "minimum": 0},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["name", "age"]
    }
    
    try:
        schema_validator = JsonValidator(
            schema=user_schema,
            max_retries=2
        )
        print("Schema validator created successfully.")
        print("Schema:", json.dumps(user_schema, indent=2))
    except ImportError:
        print("⚠️  jsonschema package not installed. Install with: pip install jsonschema")
    
    print("Example usage:")
    print("""
    result = client.generate(
        "Create a user profile with name, age, and email",
        output_validator=schema_validator
    )
    """)
    print()
    
    # Example 3: Text Format Validation with Custom Function
    print("✅ Example 3: Custom Text Validation")
    print("-" * 35)
    
    def validate_email_in_text(text):
        """Custom validator to check if text contains a valid email."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return bool(re.search(email_pattern, text))
    
    text_validator = TextValidator(
        requirements="Response must contain at least one valid email address",
        validator_func=validate_email_in_text,
        max_retries=2
    )
    
    print("Custom text validator created.")
    print("Example usage:")
    print("""
    result = client.chat([
        {"role": "user", "content": "Generate a business contact with email"}
    ], output_validator=text_validator)
    """)
    print()
    
    # Example 4: Regex Pattern Validation
    print("🔍 Example 4: Regex Pattern Validation")
    print("-" * 35)
    
    # Phone number validator
    phone_validator = RegexValidator(
        pattern=r'^\+?1?-?\.?\s?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})$',
        requirements_description="Must contain a valid US phone number format",
        max_retries=2
    )
    
    print("Phone number regex validator created.")
    print("Example usage:")
    print("""
    result = client.invoke(
        "Generate only a US phone number in standard format",
        output_validator=phone_validator
    )
    """)
    print()
    
    # Example 5: Batch Processing with Validation
    print("📦 Example 5: Batch Processing with Validation")
    print("-" * 40)
    
    batch_validator = JsonValidator(strict=True)  # Strict JSON only
    
    print("Batch validation example:")
    print("""
    prompts = [
        "Generate JSON for user Alice with age 25",
        "Generate JSON for user Bob with age 30", 
        "Generate JSON for user Carol with age 28"
    ]
    
    results = client.invoke_batch(
        prompts,
        output_validator=batch_validator
    )
    
    # All results will be valid JSON or validation will retry
    for i, result in enumerate(results):
        user_data = json.loads(result)
        print(f"User {i+1}: {user_data}")
    """)
    print()
    
    # Example 6: Advanced JSON with Complex Schema
    print("🏗️  Example 6: Complex Schema Validation")
    print("-" * 38)
    
    complex_schema = {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string", "minLength": 1},
                        "preferences": {
                            "type": "object",
                            "properties": {
                                "theme": {"type": "string", "enum": ["light", "dark"]},
                                "notifications": {"type": "boolean"}
                            }
                        }
                    },
                    "required": ["id", "name"]
                }
            },
            "total": {"type": "integer", "minimum": 0}
        },
        "required": ["users", "total"]
    }
    
    print("Complex schema for user list validation:")
    print(json.dumps(complex_schema, indent=2))
    print()
    
    # Example 7: Error Handling
    print("⚠️  Example 7: Error Handling")
    print("-" * 28)
    
    print("""
    try:
        result = client.invoke(
            "Generate some data",
            output_validator=strict_json_validator
        )
        print("Validation succeeded:", result)
    except ValueError as e:
        if "Output validation failed" in str(e):
            print("All validation attempts failed:", e)
        else:
            raise  # Re-raise if it's a different error
    """)
    print()
    
    print("✨ Validation Features Summary:")
    print("- Automatic retry with detailed error feedback")
    print("- Support for JSON, custom text, and regex validation")
    print("- Optional JSON Schema validation")
    print("- Flexible extraction from mixed text")
    print("- Configurable retry limits")
    print("- Full integration with all Client methods")
    print()
    
    print("💡 Tips:")
    print("- Use strict=False for JSON extraction from explanatory text")
    print("- Combine multiple validators for complex requirements")
    print("- Set appropriate max_retries based on your use case")
    print("- Use custom validation functions for domain-specific rules")


if __name__ == "__main__":
    main()