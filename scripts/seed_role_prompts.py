"""
Seed script for baseline role prompts.

Loads prompt content from JSON files in app/orchestrator_api/prompts/defaults/
Creates 11 role prompts: 
- Workers: pm, architect, ba, dev, qa, commit (stub)
- Mentors: pm_mentor, architect_mentor, ba_mentor, developer_mentor, qa_mentor

Run: python scripts/seed_role_prompts.py
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.combine.persistence.repositories.role_prompt_repository import RolePromptRepository


def load_prompt_from_file(role_name: str) -> dict:
    """Load prompt definition from JSON file."""
    prompt_file = Path(__file__).parent.parent / "app" / "orchestrator_api" / "prompts" / "defaults" / f"{role_name}_v1.json"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def seed_role_prompts():
    """Seed baseline role prompts from JSON files."""
    repo = RolePromptRepository()
    created_count = 0
    skipped_count = 0
    
    # All roles: workers + mentors
    roles = [
        # Worker roles (execute phases)
        "pm",
        "architect", 
        "ba",
        "dev",
        "qa",
        "commit",
        # Mentor roles (consolidate worker proposals)
        "pm_mentor",
        "architect_mentor",
        "ba_mentor",
        "developer_mentor",
        "qa_mentor"
    ]
    
    print(f"Seeding {len(roles)} role prompts...\n")
    
    for role_name in roles:
        try:
            # Check if prompt already exists
            existing = repo.get_active_prompt(role_name)
            if existing:
                print(f"⊘ Skipped {role_name}: already exists (version {existing.version})")
                skipped_count += 1
                continue
            
            # Load prompt data from file
            prompt_data = load_prompt_from_file(role_name)
            
            # Get working_schema and ensure it's dict or None
            working_schema = prompt_data.get("working_schema")
            
            # Debug: show what we're about to save
            print(f"  Loading {role_name}:")
            print(f"    working_schema type: {type(working_schema)}")
            if working_schema is not None:
                print(f"    working_schema keys: {list(working_schema.keys()) if isinstance(working_schema, dict) else 'NOT A DICT'}")
            
            # Ensure working_schema is dict or None (not string)
            if working_schema is not None and not isinstance(working_schema, dict):
                print(f"  ⚠ WARNING: working_schema is {type(working_schema)}, converting to None")
                working_schema = None
            
            # Create prompt
            prompt = repo.create(
                role_name=prompt_data["role_name"],
                version=prompt_data["version"],
                bootstrapper=prompt_data["bootstrapper"],
                instructions=prompt_data["instructions"],
                working_schema=working_schema,
                created_by="system",
                notes=prompt_data.get("notes", f"Initial {role_name} prompt"),
                set_active=True
            )
            print(f"✓ Created {role_name} prompt (version {prompt.version})\n")
            created_count += 1
            
        except FileNotFoundError as e:
            print(f"✗ Failed to load {role_name} prompt: {e}\n")
        except Exception as e:
            print(f"✗ Failed to create {role_name} prompt: {e}\n")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ Summary: {created_count} created, {skipped_count} skipped")
    print(f"✓ Total roles seeded: {created_count + skipped_count}/{len(roles)}")
    return created_count > 0 or skipped_count > 0


if __name__ == "__main__":
    success = seed_role_prompts()
    sys.exit(0 if success else 1)