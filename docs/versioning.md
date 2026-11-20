# Versioning

The major API version is part of every application URL: `/api/v1`.

Within v1, responses may gain optional fields and enums may gain documented values. Removing a
field, changing its meaning, or adding a required request field requires a new major version.
Presigned storage URLs are temporary credentials, not versioned API endpoints.

Clients must ignore response fields they do not recognize and handle unknown enum values without
rejecting the entire response. Request objects remain strict: clients must not send undocumented
fields.
