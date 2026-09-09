"""
Unified E2E Test Suite Runner using FastAPI TestClient.
Executes all existing test modules (Auth, Documents, Extraction, Chunking, Embeddings, Chroma, RAG, Gemini RAG, Conversations, Assistant)
in-process without requiring external network connections.
"""
import os
import sys
import unittest.mock
from urllib.parse import urlparse

from fastapi.testclient import TestClient
from app.main import app

# Create in-process test client
client = TestClient(app)

class TestClientResponseAdapter:
    """Adapts FastAPI TestClient Response to behave like a requests.Response."""
    def __init__(self, starlette_response):
        self._resp = starlette_response
        self.status_code = starlette_response.status_code
        self.text = starlette_response.text
        self.content = starlette_response.content
        self.headers = starlette_response.headers

    def json(self):
        return self._resp.json()

def mock_request(method, url, **kwargs):
    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path += f"?{parsed.query}"
    
    # Extract params, headers, json, data, files
    headers = kwargs.get("headers", {})
    json_payload = kwargs.get("json")
    data = kwargs.get("data")
    files = kwargs.get("files")
    params = kwargs.get("params")

    response = client.request(
        method=method,
        url=path,
        headers=headers,
        json=json_payload,
        data=data,
        files=files,
        params=params,
    )
    return TestClientResponseAdapter(response)

def mock_get(url, **kwargs):
    return mock_request("GET", url, **kwargs)

def mock_post(url, **kwargs):
    return mock_request("POST", url, **kwargs)

def mock_put(url, **kwargs):
    return mock_request("PUT", url, **kwargs)

def mock_delete(url, **kwargs):
    return mock_request("DELETE", url, **kwargs)

# Also mock urllib.request for test_auth.py
class MockUrlLibResponse:
    def __init__(self, response):
        self._resp = response
        self.code = response.status_code

    def read(self):
        return self._resp.content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

import urllib.error

def mock_urlopen(url_or_req, data=None, timeout=None):
    if hasattr(url_or_req, "full_url"):
        url = url_or_req.full_url
        method = url_or_req.get_method()
        headers = dict(url_or_req.headers)
        body = url_or_req.data
        parsed = urlparse(url)
        path = parsed.path
        
        # If body exists and json content type
        json_data = None
        data_payload = None
        if body:
            ct = headers.get("Content-type", headers.get("Content-Type", ""))
            if "application/json" in ct:
                import json
                json_data = json.loads(body.decode("utf-8"))
            else:
                data_payload = body

        resp = client.request(method=method, url=path, headers=headers, json=json_data, data=data_payload)
    else:
        url = str(url_or_req)
        parsed = urlparse(url)
        path = parsed.path
        resp = client.get(path)

    if resp.status_code >= 400:
        raise urllib.error.HTTPError(
            url=url,
            code=resp.status_code,
            msg=resp.text,
            hdrs=resp.headers,
            fp=None
        )
    return MockUrlLibResponse(resp)

def run_suite():
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from app.database.connection import engine
    from app.database.base import Base
    from app.models.user import User
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.conversation import Conversation
    from app.models.conversation_message import ConversationMessage

    # Re-create database tables cleanly
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Clear ChromaDB vector storage directory for clean vector DB initialization
    import shutil
    from app.config import settings
    chroma_dir = os.path.abspath(settings.CHROMA_PERSIST_DIRECTORY)
    if os.path.exists(chroma_dir):
        try:
            shutil.rmtree(chroma_dir, ignore_errors=True)
        except Exception:
            pass

    import requests
    requests.get = mock_get
    requests.post = mock_post
    requests.put = mock_put
    requests.delete = mock_delete
    requests.request = mock_request

    import urllib.request
    urllib.request.urlopen = mock_urlopen

    test_files = [
        "test_auth.py",
        "test_db.py",
        "test_documents.py",
        "test_extraction.py",
        "test_chunking.py",
        "test_embeddings.py",
        "test_chroma.py",
        "test_rag.py",
        "test_gemini_rag.py",
        "test_conversations.py",
        "test_assistant.py",
    ]

    print("=" * 70)
    print("  RUNNING COMPLETE E2E BACKEND TEST SUITE (IN-PROCESS TESTCLIENT)")
    print("=" * 70)

    passed_tests = []
    failed_tests = []

    for tf in test_files:
        print(f"\n>>> Running {tf} ...")
        try:
            with open(tf, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Execute in a custom globals namespace
            g_ns = {
                "__name__": "__main__",
                "__file__": tf,
                "requests": requests,
                "urllib": urllib,
            }
            exec(code, g_ns)
            passed_tests.append(tf)
            print(f"✅ {tf} PASSED!")
        except Exception as e:
            failed_tests.append((tf, str(e)))
            print(f"❌ {tf} FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("  FINAL SUITE RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Passed: {len(passed_tests)} / {len(test_files)}")
    print(f"  Failed: {len(failed_tests)} / {len(test_files)}")
    
    if failed_tests:
        print("\nFailures:")
        for tf, err in failed_tests:
            print(f"  - {tf}: {err}")
    else:
        print("\n🎉 ALL BACKEND TEST MODULES PASSED 100%!")

if __name__ == "__main__":
    run_suite()
