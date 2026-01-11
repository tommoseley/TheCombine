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
    {% for item in block.data["items"] %}
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
  
  {% if not block.data["items"] or block.data["items"] | length == 0 %}
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
    {% for item in block.data["items"] %}
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
  
  {% if not block.data["items"] or block.data["items"] | length == 0 %}
  <p class="text-gray-400 italic">No stories in this epic.</p>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034-DISCOVERY: Generic List and Summary Fragments
# =============================================================================

STRING_LIST_BLOCK_V1_FRAGMENT = """
<div class="string-list-block" data-block-type="StringListBlockV1">
  {# Title handled by section header - don't duplicate #}
  {% set style = block.context.style | default(block.data.style) | default('bullet') %}
  
  {% if style == 'numbered' %}
  <ol class="list-decimal list-inside space-y-2 text-gray-700">
    {% for item in block.data["items"] %}
    <li>{{ item.value if item is mapping else item }}</li>
    {% endfor %}
  </ol>
  {% elif style == 'check' %}
  <ul class="space-y-2">
    {% for item in block.data["items"] %}
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
    {% for item in block.data["items"] %}
    <li>{{ item.value if item is mapping else item }}</li>
    {% endfor %}
  </ul>
  {% endif %}
  
  {% if not block.data["items"] or block.data["items"] | length == 0 %}
  <p class="text-gray-400 italic">No items.</p>
  {% endif %}
</div>
"""


SUMMARY_BLOCK_V1_FRAGMENT = """
<div class="summary-block bg-blue-50 rounded-lg p-4 space-y-3" data-block-type="SummaryBlockV1">
  {# ProjectDiscovery fields #}
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
  
  {# EpicBacklog epic_set_summary fields #}
  {% if block.data.overall_intent %}
  <div>
    <span class="text-sm font-medium text-blue-800">Overall Intent:</span>
    <p class="text-blue-900">{{ block.data.overall_intent }}</p>
  </div>
  {% endif %}
  
  {% if block.data.mvp_definition %}
  <div>
    <span class="text-sm font-medium text-blue-800">MVP Definition:</span>
    <p class="text-blue-900">{{ block.data.mvp_definition }}</p>
  </div>
  {% endif %}
  
  {# Architecture Summary fields #}
  {% if block.data.title %}
  <div>
    <h3 class="text-lg font-semibold text-blue-900">{{ block.data.title }}</h3>
  </div>
  {% endif %}
  
  {% if block.data.architectural_style %}
  <div>
    <span class="text-sm font-medium text-blue-800">Architectural Style:</span>
    <p class="text-blue-900">{{ block.data.architectural_style }}</p>
  </div>
  {% endif %}
  
  {% if block.data.refined_description %}
  <div>
    <span class="text-sm font-medium text-blue-800">Description:</span>
    <p class="text-blue-900">{{ block.data.refined_description }}</p>
  </div>
  {% endif %}
</div>
"""


RISKS_BLOCK_V1_FRAGMENT = """
<div class="risks-block" data-block-type="RisksBlockV1">
  {# Title handled by section header - don't duplicate #}
  <div class="space-y-3">
    {% for item in block.data["items"] %}
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
          {% if item.likelihood %}
          <span class="px-2 py-0.5 text-xs font-medium rounded {{ badge_class }}">
            {{ likelihood | title }}
          </span>
          {% endif %}
        </div>
        {% if item.impact %}
        <p class="text-sm text-gray-600">{{ item.impact }}</p>
        {% endif %}
        {% if item.affected_epics and item.affected_epics | length > 0 %}
        <p class="text-xs text-gray-500 mt-2">
          Affects: {{ item.affected_epics | join(', ') }}
        </p>
        {% endif %}
      </div>
    {% endfor %}
  </div>
  
  {% if not block.data["items"] or block.data["items"] | length == 0 %}
  <p class="text-gray-400 italic">No risks identified.</p>
  {% endif %}
</div>
"""


PARAGRAPH_BLOCK_V1_FRAGMENT = """
<div class="paragraph-block" data-block-type="ParagraphBlockV1">
  {% if block.context and block.context.title %}
  <h3 class="text-lg font-semibold text-gray-900 mb-2">{{ block.context.title }}</h3>
  {% endif %}
  
  {% set text = block.data.content or block.data.value or block.data %}
  {% if text is string %}
  <p class="text-gray-700 leading-relaxed">{{ text }}</p>
  {% elif text is mapping and text.value %}
  <p class="text-gray-700 leading-relaxed">{{ text.value }}</p>
  {% else %}
  <p class="text-gray-400 italic">No content.</p>
  {% endif %}
</div>
"""


INDICATOR_BLOCK_V1_FRAGMENT = """
<div class="indicator-block inline-flex items-center gap-2" data-block-type="IndicatorBlockV1">
  {% if block.context and block.context.title %}
  <span class="text-sm text-gray-600">{{ block.context.title }}:</span>
  {% endif %}
  
  {% set value = block.data.value | default('unknown') %}
  {% if value == 'high' %}
  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
    {{ value | title }}
  </span>
  {% elif value == 'medium' %}
  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
    {{ value | title }}
  </span>
  {% elif value == 'low' %}
  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
    {{ value | title }}
  </span>
  {% else %}
  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
    {{ value | title }}
  </span>
  {% endif %}
</div>
"""


EPIC_SUMMARY_BLOCK_V1_FRAGMENT = """
<div class="epic-summary-block border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors" data-block-type="EpicSummaryBlockV1" data-epic-id="{{ block.data.epic_id | default(block.context.epic_id) }}">
  <div class="flex items-start justify-between gap-4">
    <div class="flex-1 min-w-0">
      <!-- Title -->
      <h3 class="text-lg font-semibold text-gray-900 truncate">
        {{ block.data.name | default(block.data.title) | default('Untitled Epic') }}
      </h3>
      
      <!-- Intent (truncated) -->
      {% if block.data.intent or block.data.vision %}
      <p class="text-sm text-gray-600 mt-1 line-clamp-2">
        {{ block.data.intent | default(block.data.vision) }}
      </p>
      {% endif %}
    </div>
    
    <div class="flex items-center gap-3 flex-shrink-0">
      <!-- Phase Badge -->
      {% if block.data.mvp_phase %}
      <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium 
        {% if block.data.mvp_phase == 'mvp' %}bg-blue-100 text-blue-800{% else %}bg-gray-100 text-gray-600{% endif %}">
        {{ block.data.mvp_phase | upper }}
      </span>
      {% endif %}
      
      <!-- Risk Level Indicator -->
      {% set risk = block.data.risk_level | default('low') %}
      <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium
        {% if risk == 'high' %}bg-red-100 text-red-800
        {% elif risk == 'medium' %}bg-amber-100 text-amber-800
        {% else %}bg-green-100 text-green-800{% endif %}">
        {{ risk | title }} Risk
      </span>
    </div>
  </div>
  
  <!-- Detail Link -->
  {% if block.data.detail_ref %}
  <div class="mt-3 pt-3 border-t border-gray-100">
    <a href="#" class="text-sm text-blue-600 hover:text-blue-800 font-medium"
       data-detail-ref="{{ block.data.detail_ref | tojson }}">
      View Details →
    </a>
  </div>
  {% endif %}
</div>
"""


DEPENDENCIES_BLOCK_V1_FRAGMENT = """
<div class="dependencies-block" data-block-type="DependenciesBlockV1">
  {# Title handled by section header - don't duplicate #}
  <div class="space-y-2">
    {% for item in block.data["items"] %}
    <div class="flex items-start gap-3 p-3 border border-gray-200 rounded-lg {% if item.blocking %}bg-amber-50 border-amber-200{% else %}bg-gray-50{% endif %}">
      <!-- Blocking indicator -->
      {% if item.blocking %}
      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 flex-shrink-0">
        Blocking
      </span>
      {% else %}
      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 flex-shrink-0">
        Optional
      </span>
      {% endif %}
      
      <div class="flex-1 min-w-0">
        <!-- Target -->
        <p class="font-medium text-gray-900">
          {% if item.depends_on_type %}{{ item.depends_on_type }}:{% endif %}{{ item.depends_on_id }}
        </p>
        
        <!-- Reason -->
        <p class="text-sm text-gray-600 mt-1">{{ item.reason }}</p>
        
        <!-- Notes -->
        {% if item.notes %}
        <p class="text-xs text-gray-500 mt-1 italic">{{ item.notes }}</p>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
  
  {% if not block.data["items"] or block.data["items"] | length == 0 %}
  <p class="text-gray-400 italic">No dependencies.</p>
  {% endif %}
</div>
"""


STORY_SUMMARY_BLOCK_V1_FRAGMENT = """
<div class="story-summary-card p-3 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors">
  <div class="flex items-start justify-between gap-2">
    <div class="flex-1 min-w-0">
      <!-- Title -->
      <p class="font-medium text-gray-900">{{ block.data.title }}</p>
      
      <!-- Intent -->
      <p class="text-sm text-gray-600 mt-1 line-clamp-2">{{ block.data.intent }}</p>
      
      <!-- Badges row -->
      <div class="flex items-center gap-2 mt-2">
        <!-- Phase badge -->
        {% if block.data.mvp_phase %}
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
          {% if block.data.mvp_phase == 'mvp' %}bg-blue-100 text-blue-800{% else %}bg-gray-100 text-gray-600{% endif %}">
          {{ block.data.phase | upper }}
        </span>
        {% endif %}
        
        <!-- Risk badge -->
        {% if block.data.risk_level %}
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
          {% if block.data.risk_level == 'high' %}bg-red-100 text-red-800
          {% elif block.data.risk_level == 'medium' %}bg-amber-100 text-amber-800
          {% else %}bg-green-100 text-green-800{% endif %}">
          {{ block.data.risk_level }} risk
        </span>
        {% endif %}
      </div>
    </div>
    
    <!-- Detail link -->
    {% if block.data.detail_ref %}
    <a href="#" class="text-blue-600 hover:text-blue-800 text-xs flex-shrink-0" 
       data-detail-ref="{{ block.data.detail_ref | tojson }}">
      View →
    </a>
    {% endif %}
  </div>
</div>
"""


STORIES_BLOCK_V1_FRAGMENT = """
<div class="stories-block" data-block-type="StoriesBlockV1">
  {% if block.context and block.context.epic_title %}
  <h3 class="text-lg font-semibold text-gray-900 mb-3">{{ block.context.epic_title }}</h3>
  {% endif %}
  
  <div class="space-y-2">
    {% for item in block.data["items"] %}
    <div class="story-summary-card p-3 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p class="font-medium text-gray-900">{{ item.title }}</p>
          <p class="text-sm text-gray-600 mt-1 line-clamp-2">{{ item.intent }}</p>
          <div class="flex items-center gap-2 mt-2">
            {% if item.phase %}
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
              {% if item.phase == 'mvp' %}bg-blue-100 text-blue-800{% else %}bg-gray-100 text-gray-600{% endif %}">
              {{ item.phase | upper }}
            </span>
            {% endif %}
            {% if item.risk_level %}
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
              {% if item.risk_level == 'high' %}bg-red-100 text-red-800
              {% elif item.risk_level == 'medium' %}bg-amber-100 text-amber-800
              {% else %}bg-green-100 text-green-800{% endif %}">
              {{ item.risk_level }} risk
            </span>
            {% endif %}
          </div>
        </div>
        {% if item.detail_ref %}
        <a href="#" class="text-blue-600 hover:text-blue-800 text-xs flex-shrink-0"
           data-detail-ref="{{ item.detail_ref | tojson }}">
          View →
        </a>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
  
  {% if not block.data["items"] or block.data["items"] | length == 0 %}
  <p class="text-gray-400 italic text-sm">No stories.</p>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034: Architecture Component Block Fragment
# =============================================================================

ARCH_COMPONENT_BLOCK_V1_FRAGMENT = """
<div class="arch-component-card border border-gray-200 rounded-lg p-4 mb-4 bg-white" data-block-type="ArchComponentBlockV1">
  <div class="flex items-start justify-between gap-4 mb-3">
    <div>
      <h4 class="text-lg font-semibold text-gray-900">{{ block.data.name }}</h4>
      <span class="text-sm text-gray-500">{{ block.data.id }}</span>
    </div>
    <div class="flex items-center gap-2">
      {% if block.data.layer %}
      <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
        {{ block.data.layer }}
      </span>
      {% endif %}
      {% if block.data.mvp_phase %}
      <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium 
        {% if block.data.mvp_phase == 'mvp' %}bg-blue-100 text-blue-800{% else %}bg-gray-100 text-gray-600{% endif %}">
        {{ block.data.mvp_phase | upper }}
      </span>
      {% endif %}
    </div>
  </div>
  
  {% if block.data.purpose %}
  <p class="text-gray-600 mb-3">{{ block.data.purpose }}</p>
  {% endif %}
  
  {% if block.data.responsibilities and block.data.responsibilities | length > 0 %}
  <div class="mb-3">
    <span class="text-sm font-medium text-gray-700">Responsibilities:</span>
    <ul class="list-disc list-inside text-sm text-gray-600 mt-1">
      {% for r in block.data.responsibilities %}
      <li>{{ r }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}
  
  {% if block.data.technology_choices and block.data.technology_choices | length > 0 %}
  <div class="mb-3">
    <span class="text-sm font-medium text-gray-700">Technology:</span>
    <div class="flex flex-wrap gap-1 mt-1">
      {% for tech in block.data.technology_choices %}
      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700">{{ tech }}</span>
      {% endfor %}
    </div>
  </div>
  {% endif %}
  
  {% if block.data.depends_on_components and block.data.depends_on_components | length > 0 %}
  <div class="text-sm text-gray-500">
    <span class="font-medium">Depends on:</span> {{ block.data.depends_on_components | join(', ') }}
  </div>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034: Quality Attribute Block Fragment
# =============================================================================

QUALITY_ATTRIBUTE_BLOCK_V1_FRAGMENT = """
<div class="quality-attr-card border border-gray-200 rounded-lg p-4 mb-4 bg-white" data-block-type="QualityAttributeBlockV1">
  <h4 class="text-lg font-semibold text-gray-900 mb-2">{{ block.data.name }}</h4>
  
  {% if block.data.target %}
  <div class="mb-2">
    <span class="text-sm font-medium text-gray-700">Target:</span>
    <p class="text-gray-600">{{ block.data.target }}</p>
  </div>
  {% endif %}
  
  {% if block.data.rationale %}
  <div class="mb-2">
    <span class="text-sm font-medium text-gray-700">Rationale:</span>
    <p class="text-sm text-gray-600">{{ block.data.rationale }}</p>
  </div>
  {% endif %}
  
  {% if block.data.acceptance_criteria and block.data.acceptance_criteria | length > 0 %}
  <div>
    <span class="text-sm font-medium text-gray-700">Acceptance Criteria:</span>
    <ul class="list-disc list-inside text-sm text-gray-600 mt-1">
      {% for c in block.data.acceptance_criteria %}
      <li>{{ c }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034: Interface Block Fragment
# =============================================================================

INTERFACE_BLOCK_V1_FRAGMENT = """
<div class="interface-card border border-gray-200 rounded-lg p-4 mb-4 bg-white" data-block-type="InterfaceBlockV1">
  <div class="flex items-start justify-between gap-4 mb-3">
    <div>
      <h4 class="text-lg font-semibold text-gray-900">{{ block.data.name }}</h4>
      <span class="text-sm text-gray-500">{{ block.data.id }}</span>
    </div>
    <div class="flex items-center gap-2">
      {% if block.data.type %}
      <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
        {{ block.data.type }}
      </span>
      {% endif %}
      {% if block.data.protocol %}
      <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
        {{ block.data.protocol }}
      </span>
      {% endif %}
    </div>
  </div>
  
  {% if block.data.description %}
  <p class="text-gray-600 mb-3">{{ block.data.description }}</p>
  {% endif %}
  
  {% if block.data.endpoints and block.data.endpoints | length > 0 %}
  <div class="mt-3">
    <span class="text-sm font-medium text-gray-700">Endpoints:</span>
    <div class="mt-2 space-y-2">
      {% for ep in block.data.endpoints %}
      <div class="bg-gray-50 rounded p-2 text-sm">
        <div class="flex items-center gap-2">
          <span class="font-mono px-1.5 py-0.5 rounded text-xs font-bold
            {% if ep.method == 'GET' %}bg-green-100 text-green-700
            {% elif ep.method == 'POST' %}bg-blue-100 text-blue-700
            {% elif ep.method == 'PUT' %}bg-amber-100 text-amber-700
            {% elif ep.method == 'DELETE' %}bg-red-100 text-red-700
            {% else %}bg-gray-100 text-gray-700{% endif %}">
            {{ ep.method }}
          </span>
          <span class="font-mono text-gray-800">{{ ep.path }}</span>
        </div>
        {% if ep.description %}
        <p class="text-gray-600 mt-1">{{ ep.description }}</p>
        {% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034: Workflow Block Fragment
# =============================================================================

WORKFLOW_BLOCK_V1_FRAGMENT = """
<div class="workflow-card border border-gray-200 rounded-lg p-4 mb-4 bg-white" data-block-type="WorkflowBlockV1">
  <h4 class="text-lg font-semibold text-gray-900 mb-2">{{ block.data.name }}</h4>
  
  {% if block.data.description %}
  <p class="text-gray-600 mb-3">{{ block.data.description }}</p>
  {% endif %}
  
  {% if block.data.trigger %}
  <div class="mb-3 text-sm">
    <span class="font-medium text-gray-700">Trigger:</span>
    <span class="text-gray-600">{{ block.data.trigger }}</span>
  </div>
  {% endif %}
  
  {% if block.data.steps and block.data.steps | length > 0 %}
  <div class="mt-3">
    <span class="text-sm font-medium text-gray-700">Steps:</span>
    <div class="mt-2 space-y-2">
      {% for step in block.data.steps %}
      <div class="flex gap-3 text-sm">
        <span class="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-medium">
          {{ step.order }}
        </span>
        <div class="flex-1">
          <div class="flex items-center gap-2">
            <span class="font-medium text-gray-800">{{ step.actor }}</span>
            <span class="text-gray-400">→</span>
            <span class="text-gray-600">{{ step.action }}</span>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}
</div>
"""


# =============================================================================
# ADR-034: Data Model Block Fragment
# =============================================================================

DATA_MODEL_BLOCK_V1_FRAGMENT = """
<div class="data-model-card border border-gray-200 rounded-lg p-4 mb-4 bg-white" data-block-type="DataModelBlockV1">
  <h4 class="text-lg font-semibold text-gray-900 mb-2">{{ block.data.name }}</h4>
  
  {% if block.data.description %}
  <p class="text-gray-600 mb-3">{{ block.data.description }}</p>
  {% endif %}
  
  {% if block.data.primary_keys and block.data.primary_keys | length > 0 %}
  <div class="mb-3 text-sm">
    <span class="font-medium text-gray-700">Primary Key:</span>
    <span class="font-mono text-gray-600">{{ block.data.primary_keys | join(', ') }}</span>
  </div>
  {% endif %}
  
  {% if block.data.fields and block.data.fields | length > 0 %}
  <div class="mt-3">
    <span class="text-sm font-medium text-gray-700">Fields:</span>
    <div class="mt-2 overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-3 py-2 text-left font-medium text-gray-700">Name</th>
            <th class="px-3 py-2 text-left font-medium text-gray-700">Type</th>
            <th class="px-3 py-2 text-left font-medium text-gray-700">Required</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {% for field in block.data.fields %}
          <tr>
            <td class="px-3 py-2 font-mono text-gray-800">{{ field.name }}</td>
            <td class="px-3 py-2 text-gray-600">{{ field.type }}</td>
            <td class="px-3 py-2">
              {% if field.required %}
              <span class="text-green-600">✓</span>
              {% else %}
              <span class="text-gray-400">-</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  {% endif %}
</div>
"""

# =============================================================================
# WS-STORY-BACKLOG-VIEW: Epic Stories Card Fragment
# =============================================================================

EPIC_STORIES_CARD_BLOCK_V1_FRAGMENT = """
<div class="epic-stories-card border border-gray-200 rounded-lg bg-white shadow-sm mb-6" 
     data-block-type="EpicStoriesCardBlockV1" data-epic-id="{{ block.data.epic_id }}">
  {# Epic Header #}
  <div class="p-4 border-b border-gray-100">
    <div class="flex items-start justify-between gap-4">
      <div class="flex-1 min-w-0">
        <h3 class="text-lg font-semibold text-gray-900">
          {{ block.data.epic_name | default(block.data.name) | default(block.data.epic_id) }}
        </h3>
        {% if block.data.intent %}
        <p class="text-sm text-gray-600 mt-1">{{ block.data.intent }}</p>
        {% endif %}
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        {% set phase = block.data.phase | default(block.data.mvp_phase) %}
        {% if phase %}
        <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium 
          {% if phase == 'mvp' %}bg-blue-100 text-blue-800{% else %}bg-gray-100 text-gray-600{% endif %}">
          {{ phase | upper }}
        </span>
        {% endif %}
        {% if block.data.risk_level %}
        <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium
          {% if block.data.risk_level == 'high' %}bg-red-100 text-red-800
          {% elif block.data.risk_level == 'medium' %}bg-amber-100 text-amber-800
          {% else %}bg-green-100 text-green-800{% endif %}">
          {{ block.data.risk_level | title }} Risk
        </span>
        {% endif %}
        {% if block.data.detail_ref %}
        <a href="#" class="text-blue-600 hover:text-blue-800 text-sm font-medium"
           data-detail-ref="{{ block.data.detail_ref | tojson }}">
          View Epic &rarr;
        </a>
        {% endif %}
      </div>
    </div>
  </div>
  
  {# Stories Section OR Generate Button #}
  {% if block.data.stories and block.data.stories | length > 0 %}
  <div class="stories-section">
    <div class="px-4 py-2 bg-gray-50 border-b border-gray-100">
      <span class="text-sm font-medium text-gray-700">Stories ({{ block.data.stories | length }})</span>
    </div>
    <ul class="divide-y divide-gray-100">
      {% for story in block.data.stories %}
      <li class="px-4 py-3 hover:bg-gray-50 transition-colors">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono text-gray-500">{{ story.story_id | default(story.id) }}</span>
              <span class="text-sm font-medium text-gray-900">{{ story.title }}</span>
            </div>
            {% set story_desc = story.intent | default(story.description) %}
            {% if story_desc %}
            <p class="text-sm text-gray-600 mt-1 line-clamp-2">{{ story_desc }}</p>
            {% endif %}
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            {% set story_phase = story.phase | default(story.mvp_phase) %}
            {% if story_phase %}
            <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium 
              {% if story_phase == 'mvp' %}bg-blue-100 text-blue-800{% else %}bg-gray-100 text-gray-600{% endif %}">
              {{ story_phase | upper }}
            </span>
            {% endif %}
            {% if story.detail_ref %}
            <a href="#" class="text-blue-600 hover:text-blue-800 text-xs"
               data-detail-ref="{{ story.detail_ref | tojson }}">
              View &rarr;
            </a>
            {% endif %}
          </div>
        </div>
      </li>
      {% endfor %}
    </ul>
  </div>
  {% else %}
  {# No stories - show generate button #}
  <div class="p-4 bg-gray-50 no-stories-section">
      <p class="text-sm text-gray-500 mb-3 no-stories-text">No stories generated yet</p>
    <button type="button"
            class="generate-epic-btn inline-flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            data-epic-id="{{ block.data.epic_id }}"
            onclick="generateEpicStories(this)">
      <i data-lucide="sparkles" class="w-4 h-4"></i>
      <span class="btn-text">Generate Stories</span>
    </button>
    <div class="generate-status mt-2 text-sm"></div>
  </div>
  {% endif %}
</div>
"""

INITIAL_FRAGMENT_ARTIFACTS: List[Dict[str, Any]] = [
    {
        "fragment_id": "fragment:OpenQuestionV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "OpenQuestionV1",
        "status": "accepted",
        "fragment_markup": OPEN_QUESTION_V1_FRAGMENT,
    },
    {
        "fragment_id": "fragment:RiskV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "RiskV1",
        "status": "accepted",
        "fragment_markup": RISK_V1_FRAGMENT,
    },
    # ADR-034-EXP: Container fragment
    {
        "fragment_id": "fragment:OpenQuestionsBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "OpenQuestionsBlockV1",
        "status": "accepted",
        "fragment_markup": OPEN_QUESTIONS_BLOCK_V1_FRAGMENT,
    },
    # ADR-034-EXP3: Story fragments
    {
        "fragment_id": "fragment:StoryV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "StoryV1",
        "status": "accepted",
        "fragment_markup": STORY_V1_FRAGMENT,
    },
    {
        "fragment_id": "fragment:StoriesBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "StoriesBlockV1",
        "status": "accepted",
        "fragment_markup": STORIES_BLOCK_V1_FRAGMENT,
    },
    # ADR-034-DISCOVERY: Generic list and summary fragments
    {
        "fragment_id": "fragment:StringListBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "StringListBlockV1",
        "status": "accepted",
        "fragment_markup": STRING_LIST_BLOCK_V1_FRAGMENT,
    },
    {
        "fragment_id": "fragment:SummaryBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "SummaryBlockV1",
        "status": "accepted",
        "fragment_markup": SUMMARY_BLOCK_V1_FRAGMENT,
    },
    {
        "fragment_id": "fragment:RisksBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "RisksBlockV1",
        "status": "accepted",
        "fragment_markup": RISKS_BLOCK_V1_FRAGMENT,
    },
    # ADR-034-EPIC-DETAIL: Paragraph block
    {
        "fragment_id": "fragment:ParagraphBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "ParagraphBlockV1",
        "status": "accepted",
        "fragment_markup": PARAGRAPH_BLOCK_V1_FRAGMENT,
    },
    # ADR-034-EPIC-SUMMARY: Indicator block
    {
        "fragment_id": "fragment:IndicatorBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "IndicatorBlockV1",
        "status": "accepted",
        "fragment_markup": INDICATOR_BLOCK_V1_FRAGMENT,
    },
    # ADR-034-EPIC-BACKLOG: Epic summary card
    {
        "fragment_id": "fragment:EpicSummaryBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "EpicSummaryBlockV1",
        "status": "accepted",
        "fragment_markup": EPIC_SUMMARY_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Dependencies block
    {
        "fragment_id": "fragment:DependenciesBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "DependenciesBlockV1",
        "status": "accepted",
        "fragment_markup": DEPENDENCIES_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Story summary item
    {
        "fragment_id": "fragment:StorySummaryBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "StorySummaryBlockV1",
        "status": "accepted",
        "fragment_markup": STORY_SUMMARY_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Stories container
    {
        "fragment_id": "fragment:StoriesBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "StoriesBlockV1",
        "status": "accepted",
        "fragment_markup": STORIES_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Architecture Component Block
    {
        "fragment_id": "fragment:ArchComponentBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "ArchComponentBlockV1",
        "status": "accepted",
        "fragment_markup": ARCH_COMPONENT_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Quality Attribute Block
    {
        "fragment_id": "fragment:QualityAttributeBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "QualityAttributeBlockV1",
        "status": "accepted",
        "fragment_markup": QUALITY_ATTRIBUTE_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Interface Block
    {
        "fragment_id": "fragment:InterfaceBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "InterfaceBlockV1",
        "status": "accepted",
        "fragment_markup": INTERFACE_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Workflow Block
    {
        "fragment_id": "fragment:WorkflowBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "WorkflowBlockV1",
        "status": "accepted",
        "fragment_markup": WORKFLOW_BLOCK_V1_FRAGMENT,
    },
    # ADR-034: Data Model Block
    {
        "fragment_id": "fragment:DataModelBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "DataModelBlockV1",
        "status": "accepted",
        "fragment_markup": DATA_MODEL_BLOCK_V1_FRAGMENT,
    },
    # WS-STORY-BACKLOG-VIEW: Epic Stories Card
    {
        "fragment_id": "fragment:EpicStoriesCardBlockV1:web:1.0.0",
        "version": "1.0",
        "schema_type_id": "EpicStoriesCardBlockV1",
        "status": "accepted",
        "fragment_markup": EPIC_STORIES_CARD_BLOCK_V1_FRAGMENT,
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







































