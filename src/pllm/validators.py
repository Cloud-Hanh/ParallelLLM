"""
Output format validators for LLM responses.

This module provides a flexible validation framework for ensuring LLM outputs
conform to specific formats like JSON or natural language requirements.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Union, List
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of output validation."""
    is_valid: bool
    error_message: Optional[str] = None
    parsed_output: Optional[Any] = None
    retry_prompt: Optional[str] = None


class OutputValidator(ABC):
    """Base class for output format validators."""
    
    def __init__(self, max_retries: int = 3):
        """
        Initialize validator.
        
        Args:
            max_retries: Maximum number of retry attempts when validation fails
        """
        self.max_retries = max_retries
    
    @abstractmethod
    def validate(self, output: str) -> ValidationResult:
        """
        Validate the output format.
        
        Args:
            output: The LLM output string to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        pass
    
    @abstractmethod
    def get_retry_prompt(self, original_output: str, error_message: str) -> str:
        """
        Generate a retry prompt when validation fails.
        
        Args:
            original_output: The original invalid output
            error_message: Description of the validation error
            
        Returns:
            A prompt string to guide the LLM for retry
        """
        pass


class JsonValidator(OutputValidator):
    """Validator for JSON format output."""
    
    def __init__(self, 
                 schema: Optional[Dict[str, Any]] = None,
                 strict: bool = False,
                 extract_json: bool = True,
                 max_retries: int = 3):
        """
        Initialize JSON validator.
        
        Args:
            schema: Optional JSON schema for validation (requires jsonschema package)
            strict: If True, output must be pure JSON. If False, extract JSON from text
            extract_json: If True, try to extract JSON from text using regex
            max_retries: Maximum number of retry attempts
        """
        super().__init__(max_retries)
        self.schema = schema
        self.strict = strict
        self.extract_json = extract_json
        
        # Check if jsonschema is available for schema validation
        self._jsonschema_available = False
        if schema:
            try:
                import jsonschema
                self._jsonschema = jsonschema
                self._jsonschema_available = True
            except ImportError:
                raise ImportError(
                    "jsonschema package is required for schema validation. "
                    "Install it with: pip install jsonschema"
                )
    
    def validate(self, output: str) -> ValidationResult:
        """Validate JSON format."""
        try:
            # First try to parse as pure JSON
            parsed_json = self._parse_json(output)
            
            # If schema validation is required
            if self.schema and self._jsonschema_available:
                try:
                    self._jsonschema.validate(parsed_json, self.schema)
                except self._jsonschema.ValidationError as e:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"JSON schema validation failed: {str(e)}",
                        retry_prompt=self.get_retry_prompt(output, f"Schema validation error: {str(e)}")
                    )
            
            return ValidationResult(
                is_valid=True,
                parsed_output=parsed_json
            )
            
        except json.JSONDecodeError as e:
            # If strict mode or extraction failed, return error
            if self.strict or not self.extract_json:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid JSON format: {str(e)}",
                    retry_prompt=self.get_retry_prompt(output, f"JSON parsing error: {str(e)}")
                )
            
            # Try to extract JSON from text
            extracted_json = self._extract_json_from_text(output)
            if extracted_json:
                try:
                    parsed_json = json.loads(extracted_json)
                    
                    # Schema validation for extracted JSON
                    if self.schema and self._jsonschema_available:
                        try:
                            self._jsonschema.validate(parsed_json, self.schema)
                        except self._jsonschema.ValidationError as e:
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Extracted JSON schema validation failed: {str(e)}",
                                retry_prompt=self.get_retry_prompt(output, f"Schema validation error: {str(e)}")
                            )
                    
                    return ValidationResult(
                        is_valid=True,
                        parsed_output=parsed_json
                    )
                except json.JSONDecodeError as e:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Extracted JSON is invalid: {str(e)}",
                        retry_prompt=self.get_retry_prompt(output, f"Extracted JSON parsing error: {str(e)}")
                    )
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message="No valid JSON found in output",
                    retry_prompt=self.get_retry_prompt(output, "No JSON found in the response")
                )
    
    def _parse_json(self, text: str) -> Any:
        """Parse JSON from text."""
        return json.loads(text.strip())
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """Extract JSON object or array from text using regex."""
        # Pattern to match JSON objects
        json_patterns = [
            r'\{(?:[^{}]|{(?:[^{}]|{[^{}]*})*})*\}',  # JSON objects
            r'\[(?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*\]'  # JSON arrays
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    # Try to parse to ensure it's valid JSON
                    json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def get_retry_prompt(self, original_output: str, error_message: str) -> str:
        """Generate retry prompt for JSON validation failures."""
        base_prompt = (
            f"Your previous response had a JSON format error: {error_message}\n\n"
            f"Previous response:\n{original_output}\n\n"
            f"Please provide a valid JSON response that follows the required format."
        )
        
        if self.schema:
            base_prompt += f"\n\nRequired JSON schema:\n{json.dumps(self.schema, indent=2)}"
        
        if not self.strict:
            base_prompt += "\n\nYou can include explanatory text, but make sure to include a valid JSON object or array."
        else:
            base_prompt += "\n\nPlease respond with ONLY valid JSON, no additional text."
        
        return base_prompt


class TextValidator(OutputValidator):
    """Validator for natural language format requirements."""
    
    def __init__(self, 
                 requirements: str,
                 validator_func: Optional[Callable[[str], bool]] = None,
                 llm_validation: bool = False,
                 max_retries: int = 3):
        """
        Initialize text validator.
        
        Args:
            requirements: Natural language description of format requirements
            validator_func: Optional custom validation function
            llm_validation: If True, use LLM to validate format compliance
            max_retries: Maximum number of retry attempts
        """
        super().__init__(max_retries)
        self.requirements = requirements
        self.validator_func = validator_func
        self.llm_validation = llm_validation
    
    def validate(self, output: str) -> ValidationResult:
        """Validate text format against natural language requirements."""
        # If custom validator function is provided
        if self.validator_func:
            try:
                is_valid = self.validator_func(output)
                if is_valid:
                    return ValidationResult(is_valid=True, parsed_output=output)
                else:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Output does not meet requirements: {self.requirements}",
                        retry_prompt=self.get_retry_prompt(output, "Custom validation failed")
                    )
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Validation function error: {str(e)}",
                    retry_prompt=self.get_retry_prompt(output, f"Validation error: {str(e)}")
                )
        
        # For now, if no custom validator and LLM validation not enabled, 
        # just return valid (basic text validator)
        # TODO: Implement LLM-based validation in future
        if self.llm_validation:
            # Placeholder for LLM-based validation
            # This would require calling another LLM to validate format
            pass
        
        return ValidationResult(is_valid=True, parsed_output=output)
    
    def get_retry_prompt(self, original_output: str, error_message: str) -> str:
        """Generate retry prompt for text validation failures."""
        return (
            f"Your previous response did not meet the format requirements: {error_message}\n\n"
            f"Requirements: {self.requirements}\n\n"
            f"Previous response:\n{original_output}\n\n"
            f"Please provide a response that meets the specified requirements."
        )


class RegexValidator(OutputValidator):
    """Validator for regex pattern matching."""
    
    def __init__(self, 
                 pattern: Union[str, re.Pattern],
                 requirements_description: str = "",
                 flags: int = 0,
                 max_retries: int = 3):
        """
        Initialize regex validator.
        
        Args:
            pattern: Regex pattern to match against
            requirements_description: Human-readable description of requirements
            flags: Regex flags (e.g., re.IGNORECASE, re.MULTILINE)
            max_retries: Maximum number of retry attempts
        """
        super().__init__(max_retries)
        if isinstance(pattern, str):
            self.pattern = re.compile(pattern, flags)
        else:
            self.pattern = pattern
        self.requirements_description = requirements_description or f"Must match pattern: {pattern}"
    
    def validate(self, output: str) -> ValidationResult:
        """Validate output against regex pattern."""
        if self.pattern.search(output):
            return ValidationResult(is_valid=True, parsed_output=output)
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Output does not match required pattern: {self.pattern.pattern}",
                retry_prompt=self.get_retry_prompt(output, "Pattern matching failed")
            )
    
    def get_retry_prompt(self, original_output: str, error_message: str) -> str:
        """Generate retry prompt for regex validation failures."""
        return (
            f"Your previous response did not match the required format: {error_message}\n\n"
            f"Requirements: {self.requirements_description}\n\n"
            f"Previous response:\n{original_output}\n\n"
            f"Please provide a response that matches the required format."
        )