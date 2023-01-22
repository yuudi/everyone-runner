# self runner

usage example:

POST /api/v1/commands

headers:
```headers
Content-Type: application/json
Authorization: Bearer your-secret-here
```

body:
```json
{
  "user": "test001",
  "command": "run sh\nwhoami"
}
```
