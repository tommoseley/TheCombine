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


# =============================================================================
# ADR-034-EXP3: Story Fragments
# =============================================================================

STORY_V1_FRAGMENT = """
<div class="story-item border-l-4 border-blue-400 pl-4 py-3 bg-white rounded shadow-sm">
  <div class="story-header flex items-center gap-2 mb-2">
    <span class="story-id font-mono text-sm text-gray-500">{{ block.data.id }}</span>
    <span class="story-status px-2 py-0.5 text-xs rounded 
      {% if block.data.status == 'done' %}bg-green-100 text-green-700
      {% elif block.data.status == 'blocked' %}bg-red-100 text-red-700
      {% elif block.data.status == 'in_progress' %}bg-yellow-100 text-yellow-700
      {% elif block.data.status == 'ready' %}bg-blue-100 text-blue-700
      {% else %}bg-gray-100 text-gray-600{% endif %}">
      {{ block.data.status }}
    </span>
  </div>
  <h4 class="story-title font-medium text-gray-900">{{ block.data.title }}</h4>
  <p class="story-description text-sm text-gray-600 mt-1">{{ block.data.description }}</p>
  {% if block.data.acceptance_criteria %}
  <div class="acceptance-criteria mt-2">
    <span class="text-xs font-medium text-gray-500">Acceptance Criteria:</span>
    <ul class="list-disc list-inside text-sm text-gray-600 mt-1">
      {% for criterion in block.data.acceptance_criteria %}
      <li>{{ criterion }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}
  {% if block.data.notes %}
  <p class="story-notes text-xs text-gray-500 mt-2 italic">{{ block.data.notes }}</p>
  {% endif %}
</div>
"""


STORIES_BLOCK_V1_FRAGMENT = """
<div class="stories-block" data-block-type="StoriesBlockV1">
  {% if block.context %}
  <div class="block-context text-sm text-gray-500 mb-3">
    {% if block.context.epic_title %}Epic: {{ block.context.epic_title }}{% endif %}
  </div>
  {% endif %}
  
  <div class="stories-list space-y-4">
    {% for item in block.data.items %}
      <div class="story-item border-l-4 border-blue-400 pl-4 py-3 bg-white rounded shadow-sm">
        <div class="story-header flex items-center gap-2 mb-2">
          <span class="story-id font-mono text-sm text-gray-500">{{ item.id }}</span>
          <span class="story-status px-2 py-0.5 text-xs rounded 
            {% if item.status == 'done' %}bg-green-100 text-green-700
            {% elif item.status == 'blocked' %}bg-red-100 text-red-700
            {% elif item.status == 'in_progress' %}bg-yellow-100 text-yellow-700
            {% elif item.status == 'ready' %}bg-blue-100 text-blue-700
            {% else %}bg-gray-100 text-gray-600{% endif %}">
            {{ item.status }}
          </span>
        </div>
        <h4 class="story-title font-medium text-gray-900">{{ item.title }}</h4>
        <p class="story-description text-sm text-gray-600 mt-1">{{ item.description }}</p>
        {% if item.acceptance_criteria %}
        <div class="acceptance-criteria mt-2">
          <span class="text-xs font-medium text-gray-500">Acceptance Criteria:</span>
          <ul class="list-disc list-inside text-sm text-gray-600 mt-1">
            {% for criterion in item.acceptance_criteria %}
            <li>{{ criterion }}</li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
      </div>
    {% endfor %}
  </div>
  
  {% if not block.data.items or block.data.items | length == 0 %}
  <p class="text-gray-400 italic">No stories in this epic.</p>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034-DISCOVERY: Generic List and Summary Fragments
# =============================================================================

STRING_LIST_BLOCK_V1_FRAGMENT = """
<div class="string-list-block" data-block-type="StringListBlockV1">
  {% if block.context and block.context.title %}
  <h3 class="text-lg font-semibold text-gray-900 mb-3">{{ block.context.title }}</h3>
  {% endif %}
  
  {% set style = block.data.style | default('bullet') %}
  
  {% if style == 'numbered' %}
  <ol class="list-decimal list-inside space-y-2 text-gray-700">
    {% for item in block.data.items %}
    <li>{{ item.value if item is mapping else item }}</li>
    {% endfor %}
  </ol>
  {% elif style == 'check' %}
  <ul class="space-y-2">
    {% for item in block.data.items %}
    <li class="flex items-start">
      <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
      </svg>
      <span class="text-gray-700">{{ item.value if item is mapping else item }}</span>
    </li>
    {% endfor %}
  </ul>
  {% else %}
  <ul class="list-disc list-inside space-y-2 text-gray-700">
    {% for item in block.data.items %}
    <li>{{ item.value if item is mapping else item }}</li>
    {% endfor %}
  </ul>
  {% endif %}
  
  {% if not block.data.items or block.data.items | length == 0 %}
  <p class="text-gray-400 italic">No items.</p>
  {% endif %}
</div>
"""


SUMMARY_BLOCK_V1_FRAGMENT = """
<div class="summary-block bg-blue-50 rounded-lg p-4 space-y-3" data-block-type="SummaryBlockV1">
  {% if block.data.problem_understanding %}
  <div>
    <span class="text-sm font-medium text-blue-800">Problem Understanding:</span>
    <p class="text-blue-900">{{ block.data.problem_understanding }}</p>
  </div>
  {% endif %}
  
  {% if block.data.architectural_intent %}
  <div>
    <span class="text-sm font-medium text-blue-800">Architectural Intent:</span>
    <p class="text-blue-900">{{ block.data.architectural_intent }}</p>
  </div>
  {% endif %}
  
  {% if block.data.scope_pressure_points %}
  <div>
    <span class="text-sm font-medium text-blue-800">Scope Pressure Points:</span>
    <p class="text-blue-900">{{ block.data.scope_pressure_points }}</p>
  </div>
  {% endif %}
</div>
"""


RISKS_BLOCK_V1_FRAGMENT = """
<div class="risks-block" data-block-type="RisksBlockV1">
  {% if block.context and block.context.title %}
  <h3 class="text-lg font-semibold text-gray-900 mb-3">{{ block.context.title }}</h3>
  {% endif %}
  
  <div class="space-y-3">
    {% for item in block.data.items %}
      {% set likelihood = item.likelihood | default('medium') %}
      {% if likelihood == 'high' %}
        {% set border_class = 'border-red-400 bg-red-50' %}
        {% set badge_class = 'bg-red-100 text-red-700' %}
      {% elif likelihood == 'medium' %}
        {% set border_class = 'border-amber-400 bg-amber-50' %}
        {% set badge_class = 'bg-amber-100 text-amber-700' %}
      {% else %}
        {% set border_class = 'border-gray-300 bg-gray-50' %}
        {% set badge_class = 'bg-gray-100 text-gray-700' %}
      {% endif %}
      
      <div class="border-l-4 {{ border_class }} p-4 rounded-r-lg">
        <div class="flex items-center justify-between mb-1">
          <p class="font-medium text-gray-900">{{ item.description }}</p>
          <span class="px-2 py-0.5 text-xs font-medium rounded {{ badge_class }}">
            {{ likelihood | title }}
          </span>
        </div>
        {% if item.impact %}
        <p class="text-sm text-gray-600">{{ item.impact }}</p>
        {% endif %}
      </div>
    {% endfor %}
  </div>
  
  {% if not block.data.items or block.data.items | length == 0 %}
  <p class="text-gray-400 italic">No risks identified.</p>
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
    # ADR-034-EXP3: Story fragments
    {
        "fragment_id": "StoryV1Fragment",
        "version": "1.0",
        "schema_type_id": "StoryV1",
        "status": "accepted",
        "fragment_markup": STORY_V1_FRAGMENT,
    },
    {
        "fragment_id": "StoriesBlockV1Fragment",
        "version": "1.0",
        "schema_type_id": "StoriesBlockV1",
        "status": "accepted",
        "fragment_markup": STORIES_BLOCK_V1_FRAGMENT,
    },
    # ADR-034-DISCOVERY: Generic list and summary fragments
    {
        "fragment_id": "StringListBlockV1Fragment",
        "version": "1.0",
        "schema_type_id": "StringListBlockV1",
        "status": "accepted",
        "fragment_markup": STRING_LIST_BLOCK_V1_FRAGMENT,
    },
    {
        "fragment_id": "SummaryBlockV1Fragment",
        "version": "1.0",
        "schema_type_id": "SummaryBlockV1",
        "status": "accepted",
        "fragment_markup": SUMMARY_BLOCK_V1_FRAGMENT,
    },
    {
        "fragment_id": "RisksBlockV1Fragment",
        "version": "1.0",
        "schema_type_id": "RisksBlockV1",
        "status": "accepted",
        "fragment_markup": RISKS_BLOCK_V1_FRAGMENT,
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






