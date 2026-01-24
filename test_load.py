import sys
sys.path.insert(0, '/home/tommoseley/dev/TheCombine')
from app.domain.workflow.plan_loader import PlanLoader
from pathlib import Path

loader = PlanLoader()

for wf in ['concierge_intake.v1.json', 'project_discovery.v1.json']:
    try:
        plan = loader.load(Path(f'seed/workflows/{wf}'))
        print(f"OK: {wf} -> workflow_id={plan.workflow_id}, document_type={plan.document_type}")
    except Exception as e:
        print(f"FAIL: {wf} -> {e}")