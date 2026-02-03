# MixMint API Contracts

This document outlines the core API endpoints, their expected inputs, and standard responses.

## Standard Response Format

All APIs follow a predictable response structure:

- **Success**: `200 OK` or `201 Created`
  ```json
  { "data": { ... } }
  ```
- **Error**: `400+` status code
  ```json
  { "error": "Descriptive error message" }
  ```

---

## 1. Downloads & Access

### POST `/api/download-token`
Generates a one-time, short-lived token for file access.

**Request Body**:
- `content_id`: string (Track ID or Album ID)
- `content_type`: "track" | "zip"

**Errors**:
- `401 Unauthorized`: Login required
- `403 Forbidden`: Purchase or active subscription required
- `404 Not Found`: Content does not exist

### GET `/api/download`
Streams the file content using a valid token.

**Query Params**:
- `token`: string (The token from `/api/download-token`)

**Errors**:
- `400 Bad Request`: Token missing
- `403 Forbidden`: Token used, expired, or IP mismatch
- `404 Not Found`: File missing in storage

---

## 2. DJ Uploads

### POST `/api/dj/upload` (Unified)
Uploads tracks or zippered album packs.

**Form Data**:
- `file`: File object
- `title`: string
- `price`: number
- `description`: string (optional)
- `content_type`: "track" | "zip"

**Errors**:
- `401 Unauthorized`: DJ login required
- `403 Forbidden`: DJ profile not approved
- `400 Bad Request`: Invalid file format or size limit exceeded (500MB for ZIP)

---

## 3. Storage Paths (R2)

MixMint enforces a strict storage hierarchy for security and isolation:

- **Tracks**: `<dj_name>_<dj_id>/tracks/<timestamp>-<filename>`
- **Albums**: `<dj_name>_<dj_id>/albums/<timestamp>-<filename>`
- **Zips**: `<dj_name>_<dj_id>/zips/<timestamp>-<filename>` (Internal backups)

---

## Error Codes & Observability

All backend errors are logged with domain tags for easier debugging:
- `[DOWNLOAD_ERROR]`
- `[UPLOAD_ERROR]`
- `[PAYMENT_ERROR]` (Planned)
- `[EMAIL_ERROR]` (Planned)
