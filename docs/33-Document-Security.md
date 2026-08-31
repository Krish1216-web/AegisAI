# Document Processing Security

Document processing treats all uploaded documents as untrusted data inputs.

## 1. Safety Measures
- **Temporary Files Isolation**: Content is written to local temporary files inside thread-safe context scopes and aggressively cleaned up at process finalization (both on success and failure).
- **Macro and Code Execution Guards**: Parsers strictly read static text contents and ignore macro scripts, preventing arbitrary code executions.
- **Path Traversal Guards**: The file downloader enforces path resolving bounds to verify sub-paths reside within `workspaces/<id>/documents/` storage branches.
- **Resource Constraints**: Limits on spreadsheet cell/row boundaries restrict CPU block and memory exhaustion scenarios.
- **Sanitized Errors**: DB error messages block full stack traces, database keys, or local folder paths from being stored on the document record or exposed through APIs.

## 2. Prompt Injection Scanner
A reusable regex and heuristic scanner evaluates all normalized text contents before storage.
- **Scanner function**: `scan_document_text(text)`
- **Behavior**: Scans for common pattern commands trying to override system directives (e.g. *"ignore all previous instructions"*).
- **Outcome**: Returns `{ "contains_suspicious_instructions": bool, "matches": [...] }` which is stored inside the document's extensible metadata payload. Document data itself is **never** deleted, ensuring complete fidelity.
