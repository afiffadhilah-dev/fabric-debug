# Candidate API Endpoints

Base URL: `/candidates`
Auth: `X-API-Key` header (required on all endpoints)

---

## POST `/candidates/` — Upsert Candidate

Create a new candidate or update an existing one. Matching is done by `email` + `organization_id`.

**Request**

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "organization_id": 1
}
```

| Field             | Type   | Required | Description                                                                 |
|-------------------|--------|----------|-----------------------------------------------------------------------------|
| `name`            | string | yes      | Candidate display name                                                      |
| `email`           | string | no       | Candidate email. Used for upsert matching (email + org)                     |
| `organization_id` | int   | no       | Organization ID. Must match the authenticated org or be omitted (defaults to authenticated org) |

**Response — 201 Created** (new candidate)

```json
{
  "candidate": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "organization_id": 1
  }
}
```

**Response — 200 OK** (existing candidate updated)

Same shape as above, with updated fields.

**Errors**

| Status | Detail                          |
|--------|---------------------------------|
| 403    | `Organization mismatch` — supplied `organization_id` doesn't match authenticated org |
| 500    | `Failed to upsert candidate: ...` |

---

## GET `/candidates/` — List Candidates

Paginated list of candidates for the authenticated organization.

**Query Parameters**

| Param      | Type | Default | Constraints    | Description          |
|------------|------|---------|----------------|----------------------|
| `page`     | int  | 1       | >= 1           | Page number          |
| `page_size`| int  | 20      | 1–100          | Results per page     |

**Request**

```
GET /candidates/?page=1&page_size=10
```

**Response — 200 OK**

```json
{
  "candidates": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "organization_id": 1
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "name": "John Smith",
      "email": null,
      "organization_id": 1
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 10
}
```

---

## GET `/candidates/{candidate_id}` — Get Candidate Detail

**Request**

```
GET /candidates/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response — 200 OK**

```json
{
  "candidate": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "organization_id": 1
  }
}
```

**Errors**

| Status | Detail                                    |
|--------|-------------------------------------------|
| 404    | `Candidate not found`                     |
| 403    | `Unauthorized access to this candidate`   |

---

## GET `/candidates/{candidate_id}/sessions` — List Candidate Sessions

Returns all interview sessions for a candidate.

**Request**

```
GET /candidates/a1b2c3d4-e5f6-7890-abcd-ef1234567890/sessions
```

**Response — 200 OK**

```json
{
  "sessions": [
    {
      "id": "sess-001",
      "candidate_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "created_at": "2026-02-10T06:54:30",
      "completed_at": "2026-02-10T07:30:00"
    },
    {
      "id": "sess-002",
      "candidate_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "created_at": "2026-02-11T10:00:00",
      "completed_at": null
    }
  ]
}
```

**Errors**

| Status | Detail                                    |
|--------|-------------------------------------------|
| 404    | `Candidate not found`                     |
| 403    | `Unauthorized access to this candidate`   |
