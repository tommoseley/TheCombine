"""
Seed data for fragment_artifacts table.

Per ADR-032: Canonical fragments are seeded as governed artifacts.

Usage:
    python -m app.domain.registry.seed_fragment_artifacts
    
Or call seed_fragment_artifacts(db) from your migration/startup.
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.services.fragment_registry_service import FragmentRegistryService

logger = logging.getLogger(__name__)


# =============================================================================
# CANONICAL FRAGMENTS - Governed rendering artifacts per ADR-032
# =============================================================================

OPEN_QUESTION_V1_FRAGMENT = '''<div class="open-question {% if item.blocking %}open-question--blocking{% endif %}" data-question-id="{{ item.id }}">
  <div class="open-question__header">
    <span class="open-question__text">{{ item.text }}</span>
    {% if item.blocking %}
    <span class="open-question__badge open-question__badge--blocking">Blocking</span>
    {% endif %}
    {% if item.priority %}
    <span class="open-question__badge open-question__badge--{{ item.priority }}">{{ item.priority | capitalize }}</span>
    {% endif %}
  </div>
  {% if item.why_it_matters %}
  <div class="open-question__why">
    <strong>Why it matters:</strong> {{ item.why_it_matters }}
  </div>
  {% endif %}
  {% if item.options and item.options | length > 0 %}
  <div class="open-question__options">
    <strong>Options:</strong>
    <ul class="open-question__options-list">
      {% for option in item.options %}
      <li class="open-question__option">
        <strong>{{ option.label }}</strong>
        {% if option.description %}: {{ option.description }}{% endif %}
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}
  {% if item.notes %}
  <div class="open-question__notes">
    <em>{{ item.notes }}</em>
  </div>
  {% endif %}
</div>'''

RISK_V1_FRAGMENT = '''<div class="risk {% if item.severity == 'critical' %}risk--critical{% elif item.severity == 'high' %}risk--high{% endif %}" data-risk-id="{{ item.id }}">
  <div class="risk__header">
    <span class="risk__description">{{ item.description }}</span>
    {% if item.severity %}
    <span class="risk__badge risk__badge--{{ item.severity }}">{{ item.severity | capitalize }}</span>
    {% endif %}
    {% if item.likelihood %}
    <span class="risk__badge risk__badge--likelihood">{{ item.likelihood | capitalize }} likelihood</span>
    {% endif %}
  </div>
  <div class="risk__impact">
    <strong>Impact:</strong> {{ item.impact }}
  </div>
  {% if item.mitigation %}
  <div class="risk__mitigation">
    <strong>Mitigation:</strong> {{ item.mitigation }}
  </div>
  {% endif %}
  {% if item.affected_items and item.affected_items | length > 0 %}
  <div class="risk__affected">
    <strong>Affects:</strong> {{ item.affected_items | join(', ') }}
  </div>
  {% endif %}
</div>'''


# ADR-034-EXP: Container fragment for Open Questions block
OPEN_QUESTIONS_BLOCK_V1_FRAGMENT = """
<div class="open-questions-block" data-block-type="OpenQuestionsBlockV1">
  {% if block.context %}
  <div class="block-context text-sm text-gray-500 mb-2">
    {% if block.context.epic_title %}Epic: {{ block.context.epic_title }}{% endif %}
  </div>
  {% endif %}
  
  <div class="questions-list space-y-4">
    {% for item in block.data.items %}
      <div class="open-question-item border-l-4 border-amber-400 pl-4 py-2">
        <div class="question-header flex items-start gap-2">
          <span class="question-id font-mono text-sm text-gray-500">{{ item.id }}</span>
          {% if item.blocking %}
          <span class="blocking-badge bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded">Blocking</span>
          {% endif %}
        </div>
        <p class="question-text font-medium mt-1">{{ item.text }}</p>
        {% if item.why_it_matters %}
        <p class="why-it-matters text-sm text-gray-600 mt-1">{{ item.why_it_matters }}</p>
        {% endif %}
      </div>
    {% endfor %}
  </div>
  
  {% if not block.data.items or block.data.items | length == 0 %}
  <p class="text-gray-400 italic">No open questions.</p>
  {% endif %}
</div>
"""


INITIAL_FRAGMENT_ARTIFACTS: List[Dict[str, Any]] = [
    {
        "fragment_id": "OpenQuestionV1Fragment",
        "version": "1.0",
        "schema_type_id": "OpenQuestionV1",
        "status": "accepted",
        "fragment_markup": OPEN_QUESTION_V1_FRAGMENT,
    },
    {
        "fragment_id": "RiskV1Fragment",
        "version": "1.0",
        "schema_type_id": "RiskV1",
        "status": "accepted",
        "fragment_markup": RISK_V1_FRAGMENT,
    },
    # ADR-034-EXP: Container fragment
    {
        "fragment_id": "OpenQuestionsBlockV1Fragment",
        "version": "1.0",
        "schema_type_id": "OpenQuestionsBlockV1",
        "status": "accepted",
        "fragment_markup": OPEN_QUESTIONS_BLOCK_V1_FRAGMENT,
    },
]


async def seed_fragment_artifacts(db: AsyncSession) -> int:
    """
    Seed the fragment_artifacts table with canonical fragments.
    
    Creates fragments and activates bindings.
    Skips any artifacts that already exist (by fragment_id + version).
    
    Args:
        db: Database session
        
    Returns:
        Number of artifacts created
    """
    registry = FragmentRegistryService(db)
    created_count = 0
    
    for artifact_data in INITIAL_FRAGMENT_ARTIFACTS:
        fragment_id = artifact_data["fragment_id"]
        version = artifact_data["version"]
        schema_type_id = artifact_data["schema_type_id"]
        
        # Check if already exists
        existing = await registry.get_fragment(fragment_id, version)
        
        if existing:
            logger.info(f"Fragment '{fragment_id}' v{version} already exists, skipping")
            continue
        
        # Create the fragment
        await registry.create_fragment(
            fragment_id=fragment_id,
            version=version,
            schema_type_id=schema_type_id,
            status=artifact_data["status"],
            fragment_markup=artifact_data["fragment_markup"],
            created_by="seed",
        )
        
        # Activate binding
        await registry.activate_binding(
            schema_type_id=schema_type_id,
            fragment_id=fragment_id,
            fragment_version=version,
        )
        
        created_count += 1
        logger.info(f"Created fragment: {fragment_id} v{version} -> {schema_type_id}")
    
    logger.info(f"Seeded {created_count} fragment artifacts")
    return created_count


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from app.core.database import async_session_factory
    
    async def main():
        async with async_session_factory() as db:
            count = await seed_fragment_artifacts(db)
            print(f"Seeded {count} fragment artifacts")
    
    asyncio.run(main())

