# Phase 4: File Upload Security Audit Report

## Scope
Audited `POST /documents/upload` endpoint for file upload vulnerabilities.

## Findings

### CRITICAL — No file size limit
- `await file.read()` called with no `max_size` parameter
- Attacker can upload arbitrarily large files → memory exhaustion
- **FIXED**: Added `max_upload_size = 10 MB` to `Settings` and post-read size check returning 413

### HIGH — No filename sanitization
- Filenames with `../../etc/passwd`, null bytes (`\x00`), or special chars not cleaned
- **FIXED**: Added `_sanitize_filename()` that strips path separators, null bytes, `..`, and trims

### HIGH — Content-Type not validated
- MIME spoofing possible (`.exe` renamed to `.pdf` passes extension check)
- **Mitigation**: Extension whitelist in `SUPPORTED_EXTENSIONS` — first line of defense
- **Recommendation**: Add MIME magic byte verification

### MEDIUM — No request body size middleware
- FastAPI accepts arbitrarily large request bodies beyond file content
- **Fix**: Size check applied after read; recommend adding `StreamingResponse` + chunked reading for production

### MEDIUM — No file count throttle
- No per-user rate limit on upload count
- **Recommendation**: Add Redis-based upload counter per user

## Fixes Applied
1. Added `max_upload_size = 10 * 1024 * 1024` to `Settings`
2. Added `_sanitize_filename()` — strips `\x00-\x1f`, `/`, `\`, `..`, leading/trailing dots and spaces
3. Added `413 Request Entity Too Large` response when file exceeds limit
4. Safe filename passed to `ingest_document` instead of raw user input
