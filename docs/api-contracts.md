# API contracts

`GET /healthz` returns HTTP 200 with `{"status":"ok"}` when the API process can respond.

## Invoice intake API

Create a merchant-scoped session with `POST /invoice-intake/sessions`. Upload one raw
image to `POST /invoice-intake/sessions/{session_id}/image` with the same bearer token.
Successful uploads return HTTP 201 and `ACCEPTED`. Invalid images return `RETRY_CAPTURE`
with HTTP 422, or 413 for oversized images. Storage or database failures return
`UNAVAILABLE` with HTTP 503. Sessions outside the authenticated merchant return HTTP 404.
