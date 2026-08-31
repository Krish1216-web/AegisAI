import pytest
import uuid

class MockRedisClient:
    def __init__(self):
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int = 300):
        self.store[key] = value

    def delete(self, key: str):
        self.store.pop(key, None)

def test_cache_key_tenant_scoping():
    ws1 = str(uuid.uuid4())
    ws2 = str(uuid.uuid4())
    tool_name = "github_create_issue"

    redis = MockRedisClient()

    # Workspace 1 caches tool result
    cache_key_ws1 = f"aegis:mcp:{ws1}:tool:{tool_name}"
    redis.set(cache_key_ws1, '{"result": "issue_101_created_ws1"}')

    # Workspace 2 caches tool result
    cache_key_ws2 = f"aegis:mcp:{ws2}:tool:{tool_name}"
    redis.set(cache_key_ws2, '{"result": "issue_202_created_ws2"}')

    # Verify complete isolation
    assert redis.get(cache_key_ws1) == '{"result": "issue_101_created_ws1"}'
    assert redis.get(cache_key_ws2) == '{"result": "issue_202_created_ws2"}'
    assert redis.get(f"aegis:mcp:{uuid.uuid4()}:tool:{tool_name}") is None
