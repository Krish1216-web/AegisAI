import pytest
import os
import uuid
import tempfile
import shutil

from app.services.document_storage import DocumentStorage
from app.core.document_exceptions import DocumentStorageError

@pytest.fixture
def temp_storage():
    # Setup temporary directory for test storage
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_store_and_retrieve_file(temp_storage):
    storage = DocumentStorage(storage_root=temp_storage)
    
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    content = b"hello test file content"
    
    # Store
    rel_path = storage.store_file(workspace_id, document_id, content)
    assert "workspaces" in rel_path
    assert str(workspace_id) in rel_path
    assert str(document_id) in rel_path
    assert rel_path.endswith("original_file")
    
    # Retrieve
    retrieved = storage.get_file(rel_path)
    assert retrieved == content
    assert storage.file_exists(rel_path)

def test_delete_file(temp_storage):
    storage = DocumentStorage(storage_root=temp_storage)
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    content = b"some content to delete"
    
    rel_path = storage.store_file(workspace_id, document_id, content)
    assert storage.file_exists(rel_path)
    
    storage.delete_file(rel_path)
    assert not storage.file_exists(rel_path)

def test_calculate_checksum(temp_storage):
    storage = DocumentStorage(storage_root=temp_storage)
    content1 = b"unique content 1"
    content2 = b"unique content 1"
    content3 = b"different content"
    
    hash1 = storage.calculate_checksum(content1)
    hash2 = storage.calculate_checksum(content2)
    hash3 = storage.calculate_checksum(content3)
    
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64  # SHA-256 length hex

def test_path_traversal_rejection(temp_storage):
    storage = DocumentStorage(storage_root=temp_storage)
    
    # Test malicious traversal paths
    malicious_paths = [
        "../traversal_file.txt",
        "..\\traversal_file.txt",
        "workspaces/../../../etc/passwd",
        "/absolute/path/leak",
        "C:\\Windows\\System32"
    ]
    
    for path in malicious_paths:
        with pytest.raises(DocumentStorageError):
            storage.get_file(path)
            
        with pytest.raises(DocumentStorageError):
            storage.delete_file(path)
