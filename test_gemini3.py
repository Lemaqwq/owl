"""Test Gemini 3 structured output to debug parsing issues.

Replicates exactly how workforce parses responses using:
- response_format.model_validate_json(message.content)
"""

from dotenv import load_dotenv
load_dotenv(override=True)

import json
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


# Response formats used by workforce
class TaskAssignment(BaseModel):
    """Task assignment response format (used by coordinator)."""
    assignee_id: str = Field(description="The ID of the worker to assign the task to")


class SubtaskResult(BaseModel):
    """Subtask result format."""
    content: str = Field(description="The response content")
    result: Optional[str] = Field(default=None, description="The result of the task")


def try_parse_response(content: str, response_format: type[BaseModel]) -> tuple[bool, any]:
    """
    Try to parse response exactly as workforce does.
    Uses: response_format.model_validate_json(message.content)
    """
    try:
        parsed = response_format.model_validate_json(content)
        return True, parsed
    except ValidationError as e:
        return False, e


def test_gemini3_workforce_parsing():
    """Test Gemini 3 output parsing exactly as workforce does."""

    print("=" * 80)
    print("Testing Gemini 3 structured output parsing (workforce style)")
    print("=" * 80)

    # Create the model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_3_FLASH_PREVIEW,
        model_config_dict={"temperature": 0},
    )

    print(f"Model: {ModelType.GEMINI_3_FLASH_PREVIEW.value}")
    print()

    # Test 1: TaskAssignment (the one that failed in the log)
    print("[TEST 1] TaskAssignment - simulating coordinator task assignment")
    print("-" * 80)

    messages = [
        {"role": "system", "content": "You are a task coordinator that assigns tasks to workers."},
        {"role": "user", "content": """Based on the task description, assign it to the most appropriate worker.

Available workers:
- Worker ID: 5528871616 - Web search specialist
- Worker ID: 5528871617 - Document processor

Task: Search the web for information about AI regulation.

Respond with the worker ID to assign this task to."""}
    ]

    print("Calling model.run() with response_format=TaskAssignment...")
    response = model.run(messages=messages, response_format=TaskAssignment)

    content = response.choices[0].message.content
    print(f"\n>>> RAW CONTENT FROM GEMINI 3:")
    print(f"'''{content}'''")
    print(f"\n>>> CONTENT REPR:")
    print(f"{repr(content)}")
    print(f"\n>>> CONTENT TYPE: {type(content)}")

    # Try parsing exactly as workforce does
    print(f"\n>>> Attempting: TaskAssignment.model_validate_json(content)")
    success, result = try_parse_response(content, TaskAssignment)
    if success:
        print(f"SUCCESS: Parsed as {result}")
    else:
        print(f"FAILED: {result}")

    # Try manual JSON parsing to understand the issue
    print(f"\n>>> Manual json.loads() attempt:")
    try:
        parsed = json.loads(content)
        print(f"SUCCESS: {parsed}")
    except json.JSONDecodeError as e:
        print(f"FAILED: {e}")
        # Check for markdown code blocks
        if "```" in content:
            print("\n>>> DETECTED: Response contains markdown code blocks!")
            # Try to extract JSON from code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if json_match:
                extracted = json_match.group(1).strip()
                print(f">>> EXTRACTED JSON: {repr(extracted)}")
                try:
                    parsed = json.loads(extracted)
                    print(f">>> EXTRACTED PARSES TO: {parsed}")
                except json.JSONDecodeError as e2:
                    print(f">>> EXTRACTED STILL FAILS: {e2}")

    print()
    print("=" * 80)

    # Test 2: Without response_format (raw JSON mode)
    print("\n[TEST 2] Raw output without response_format")
    print("-" * 80)

    messages = [
        {"role": "user", "content": "Return a JSON object with 'assignee_id' set to '5528871616'. Return ONLY valid JSON, no markdown."}
    ]

    print("Calling model.run() WITHOUT response_format...")
    response = model.run(messages=messages)

    content = response.choices[0].message.content
    print(f"\n>>> RAW CONTENT:")
    print(f"'''{content}'''")
    print(f"\n>>> CONTENT REPR: {repr(content)}")

    print()
    print("=" * 80)

    # Test 3: With JSON mode in config
    print("\n[TEST 3] With response_format={'type': 'json_object'} in config")
    print("-" * 80)

    model_json = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_3_FLASH_PREVIEW,
        model_config_dict={"temperature": 0, "response_format": {"type": "json_object"}},
    )

    messages = [
        {"role": "user", "content": "Return a JSON object with 'assignee_id' set to '5528871616'."}
    ]

    print("Calling model.run() with json_object response_format in config...")
    response = model_json.run(messages=messages)

    content = response.choices[0].message.content
    print(f"\n>>> RAW CONTENT:")
    print(f"'''{content}'''")
    print(f"\n>>> CONTENT REPR: {repr(content)}")

    # Try parsing
    print(f"\n>>> Attempting: TaskAssignment.model_validate_json(content)")
    success, result = try_parse_response(content, TaskAssignment)
    if success:
        print(f"SUCCESS: Parsed as {result}")
    else:
        print(f"FAILED: {result}")

    print()
    print("=" * 80)
    print("\nDIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_gemini3_workforce_parsing()
