from app.domain.handlers import get_handler

handler = get_handler("architecture_spec")
print(handler)

fake_response = '''```json
{
    "architecture_summary": {
        "title": "The Combine Architecture",
        "architectural_style": "Document-centric factory with registry-driven handlers",
        "key_decisions": [
            "Documents are primary, workers are anonymous",
            "Handlers own rendering logic",
            "Registry in database, not code"
        ]
    },
    "components": [
        {"name": "Document Registry", "purpose": "Source of truth for document types", "layer": "Domain"},
        {"name": "Document Builder", "purpose": "Builds any document type", "layer": "Domain"},
        {"name": "Handlers", "purpose": "Parse, validate, transform, render", "layer": "Domain"}
    ],
    "data_model": [],
    "interfaces": [],
    "workflows": [],
    "quality_attributes": [],
    "risks": []
}
```'''

result = handler.process(fake_response)
print(f"Title: {result['title']}")
print(f"HTML: {len(handler.render(result['data']))} chars")
