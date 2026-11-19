# Authentication

Send credentials through the standard bearer header:

```http
Authorization: Bearer <token>
```

The v1 owner and upload routes accept either the Splatter website's Clerk session or a personal API
token created on the website's Settings page. Send the complete personal token as the bearer value.
It is shown only once when created; store it like a password.

Personal tokens grant the same owner-level API access as the account that created them. They do not
grant access to token-management endpoints. Revoked and expired tokens fail immediately with
`401 AUTHENTICATION_REQUIRED`.

Never send a Splatter bearer token to a presigned part URL. The URL itself is the temporary upload
credential.
