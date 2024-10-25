import os
from openai import OpenAI
import pytest

@pytest.fixture
def client():
    return OpenAI()

def test_chat_completion_hello_world(client):
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, World!'"}
        ]
    )
    print(completion)
    
    assert completion.choices[0].message.content.strip().lower() == "hello, world!"


def test_list_assistants(client):
    assistants = client.beta.assistants.list()
    print(assistants)
    assert isinstance(assistants.data, list)
    assert len(assistants.data) > 0
    
    # Check if each assistant has the expected attributes
    for assistant in assistants.data:
        assert hasattr(assistant, 'id')
        assert hasattr(assistant, 'name')
        assert hasattr(assistant, 'created_at')
        assert hasattr(assistant, 'model')

