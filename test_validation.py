import sys
import os

# Set working directory
os.chdir(r'C:\Dev\The Combine')
sys.path.insert(0, '.')

output = []
try:
    from app.domain.workflow import WorkflowValidator, ValidationResult
    import json

    # Load workflow with absolute path
    workflow_path = r'C:\Dev\The Combine\seed\workflows\software_product_development.v1.json'
    output.append(f'Loading workflow from: {workflow_path}')
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    output.append(f'Workflow loaded: {workflow.get("name", "unknown")}')

    # Create validator
    validator = WorkflowValidator()

    # Test validation
    output.append('Testing workflow validation...')
    result = validator.validate(workflow)

    if result.valid:
        output.append('SUCCESS: Workflow is valid')
    else:
        output.append(f'ERRORS ({len(result.errors)}):')
        for e in result.errors:
            output.append(f'  {e}')
except Exception as ex:
    output.append(f'ERROR: {ex}')
    import traceback
    output.append(traceback.format_exc())

with open(r'C:\Dev\The Combine\test_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
