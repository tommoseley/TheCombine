from app.domain.handlers import get_handler

handler = get_handler("project_discovery")

fake_response = '''```json
{
    "project_name": "The Combine",
    "preliminary_summary": {
        "problem_understanding": "Document production is manual and slow",
        "proposed_system_shape": "Document-centric factory with registry and handlers",
        "architectural_intent": "Make workers anonymous, documents primary"
    },
    "unknowns": [
        {"question": "How to handle streaming?", "why_it_matters": "UX", "impact_if_unresolved": "Bad UX"}
    ],
    "stakeholder_questions": [
        {"question": "What's the MVP scope?", "directed_to": "product", "blocking": true}
    ]
}
```'''

result = handler.process(fake_response)
print(f"Title: {result['title']}")
print(f"HTML length: {len(handler.render(result['data']))} chars")
