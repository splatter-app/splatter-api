# Versioning

The major API version is part of every application URL: `/api/v1`.

Within v1, responses may gain optional fields and enums may gain documented values. Removing a
field, changing its meaning, or adding a required request field requires a new major version.
Presigned storage URLs are temporary credentials, not versioned API endpoints.
