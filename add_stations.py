import json

STATION_MAPPINGS = {
    "intake_gate": {"id": "intake", "label": "INTAKE", "order": 1},
    "pgc": {"id": "pgc", "label": "PGC", "order": 1},
    "pgc_gate": {"id": "pgc", "label": "PGC", "order": 1},
    "generation": {"id": "draft", "label": "DRAFT", "order": 2},
    "qa": {"id": "qa", "label": "QA", "order": 3},
    "qa_gate": {"id": "qa", "label": "QA", "order": 3},
    "remediation": {"id": "qa", "label": "QA", "order": 3},
    "end_complete": {"id": "done", "label": "DONE", "order": 4},
    "end_failed": {"id": "done", "label": "DONE", "order": 4},
    "end_stabilized": {"id": "done", "label": "DONE", "order": 4},
    "end_blocked": {"id": "done", "label": "DONE", "order": 4},
    "end_abandoned": {"id": "done", "label": "DONE", "order": 4},
}

files = [
    "combine-config/workflows/concierge_intake/releases/1.4.0/definition.json",
    "combine-config/workflows/project_discovery/releases/2.0.0/definition.json",
    "combine-config/workflows/technical_architecture/releases/2.0.0/definition.json",
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for node in data.get('nodes', []):
        node_id = node.get('node_id')
        if node_id in STATION_MAPPINGS:
            node['station'] = STATION_MAPPINGS[node_id]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Updated: {filepath}")
