curl -X POST "http://localhost:8000/workforce/commit" \
  -H "Content-Type: application/json" \
  -H "x-workforce-key: super-secret" \
  -d '{
    "message": "test workforce commit",
    "changes": [
      {
        "path": "README_WORKFORCE.md",
        "content": "# Hello from the Workforce\n"
      }
    ]
  }'