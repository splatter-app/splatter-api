# Authentication

Send credentials through the standard bearer header:

```http
Authorization: Bearer <token>
```

External clients use a personal API token created on the Splatter website's Settings page. Send the
complete personal token as the bearer value. It is shown only once when created; store it like a
password. The website also uses the same routes with its Clerk session, but Clerk authentication is
not part of the external client contract.

Personal tokens grant the same owner-level API access as the account that created them. They do not
grant access to token-management endpoints. Revoked and expired tokens fail immediately with
`401 AUTHENTICATION_REQUIRED`.

Never send a Splatter bearer token to a presigned part URL. The URL itself is the temporary upload
credential.
