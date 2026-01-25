import sys
sys.path.insert(0, '/home/tommoseley/dev/TheCombine')

from uuid import UUID
from app.domain.prompt.assembler import PromptAssembler

FIXTURES = "tests/fixtures/adr041"

assembler = PromptAssembler(template_root=f"{FIXTURES}/templates")

result = assembler.assemble(
    task_ref="clarification_generator_v1",
    includes={
        "PGC_CONTEXT": f"{FIXTURES}/includes/pgc_context_project_discovery_v1.txt",
        "OUTPUT_SCHEMA": f"{FIXTURES}/includes/clarification_schema_v2.json",
    },
    correlation_id=UUID("00000000-0000-0000-0000-000000000001"),
)

expected_content = open(f"{FIXTURES}/expected/assembled_clarification_generator_project_discovery_v1.txt").read()

print(f"Result length: {len(result.content)}")
print(f"Expected length: {len(expected_content)}")
print(f"Equal: {result.content == expected_content}")

if result.content != expected_content:
    # Find first difference
    for i, (r, e) in enumerate(zip(result.content, expected_content)):
        if r != e:
            print(f"First diff at position {i}: result={repr(r)}, expected={repr(e)}")
            print(f"Context: result[{i-5}:{i+10}]={repr(result.content[i-5:i+10])}")
            print(f"Context: expected[{i-5}:{i+10}]={repr(expected_content[i-5:i+10])}")
            break
    else:
        if len(result.content) != len(expected_content):
            print(f"Lengths differ: result={len(result.content)}, expected={len(expected_content)}")