"""
Seed script for baseline phase configuration.

Creates 6-phase pipeline: pm_phase → arch_phase → ba_phase → dev_phase → qa_phase → commit_phase → null

Run: python scripts/seed_phase_configuration.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.orchestrator_api.persistence.repositories.phase_configuration_repository import PhaseConfigurationRepository


def seed_phase_configuration():
    """Seed baseline phase configuration."""
    repo = PhaseConfigurationRepository()
    created_count = 0
    skipped_count = 0
    
    # Define 6-phase pipeline
    phases = [
        {"phase_name": "pm_phase", "role_name": "pm", "artifact_type": "epic", "next_phase": "arch_phase"},
        {"phase_name": "arch_phase", "role_name": "architect", "artifact_type": "arch_notes", "next_phase": "ba_phase"},
        {"phase_name": "ba_phase", "role_name": "ba", "artifact_type": "ba_spec", "next_phase": "dev_phase"},
        {"phase_name": "dev_phase", "role_name": "dev", "artifact_type": "proposed_change_set", "next_phase": "qa_phase"},
        {"phase_name": "qa_phase", "role_name": "qa", "artifact_type": "qa_result", "next_phase": "commit_phase"},
        {"phase_name": "commit_phase", "role_name": "commit", "artifact_type": "commit_result", "next_phase": None},  # Terminal
    ]
    
    for phase_data in phases:
        try:
            # Check if phase already exists
            existing = repo.get_by_phase(phase_data["phase_name"])
            if existing:
                print(f"○ Skipped {phase_data['phase_name']}: already exists")
                skipped_count += 1
                continue
            
            # Create phase
            config = repo.create(
                phase_name=phase_data["phase_name"],
                role_name=phase_data["role_name"],
                artifact_type=phase_data["artifact_type"],
                next_phase=phase_data["next_phase"]
            )
            
            next_display = phase_data["next_phase"] if phase_data["next_phase"] else "(terminal)"
            print(f"✓ Created {phase_data['phase_name']} → {phase_data['role_name']} → {phase_data['artifact_type']} → {next_display}")
            created_count += 1
            
        except Exception as e:
            print(f"✗ Failed to create {phase_data['phase_name']}: {e}")
    
    # Validate configuration graph
    print("\nValidating configuration graph...")
    validation = repo.validate_configuration_graph()
    
    if validation.is_valid:
        print("✓ Configuration graph valid")
    else:
        print("✗ Configuration graph has errors:")
        for error in validation.errors:
            print(f"  - {error}")
        raise ValueError("Configuration validation failed")
    
    print(f"\n✓ Summary: {created_count} created, {skipped_count} skipped, graph validated")
    return created_count > 0 or skipped_count > 0


if __name__ == "__main__":
    success = seed_phase_configuration()
    sys.exit(0 if success else 1)