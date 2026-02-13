import sys
sys.path.insert(0, '/home/tommoseley/dev/TheCombine')
try:
    from app.domain.workflow.plan_registry import get_plan_registry
    registry = get_plan_registry()
    plans = registry.list_plans()
    print(f"Loaded {len(plans)} plans:")
    for p in plans:
        print(f"  - {p.workflow_id} -> {p.document_type}")
except Exception as e:
    import traceback
    traceback.print_exc()