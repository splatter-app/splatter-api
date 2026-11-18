# Authentication

Send credentials through the standard bearer header:

```http
Authorization: Bearer <token>
```

The current v1 routes support the Splatter website's Clerk session. User-issued personal API
tokens will use the same header after the token-management slice is released.

Never send a Splatter bearer token to a presigned part URL. The URL itself is the temporary upload
credential.
