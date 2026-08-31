# Document Storage Security

AegisAI employs strict security restrictions for document handling:

1. **Path Traversal Guards**: Checks for parent directories (`..`), absolute prefixes (`/` or `\\`), and verifies resolved paths are sub-paths of the base storage root folder.
2. **Signature Bytes Verification**: Reads the starting bytes of all binary documents (like PDF `%PDF` or Office ZIP containers `PK\x03\x04`) to prevent extension/MIME spoofing.
3. **Tenant & Owner Boundaries**: Every download, details view, listing, and deletion API call checks workspace membership and document ownership. 
4. **Duplicate Protection**: Checksum detection restricts duplication within the same workspace to optimize space, while hiding existing files from other tenants.
