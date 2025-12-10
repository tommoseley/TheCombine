{
  "epic_id": "PIPELINE-175D",
  "title": "Metrics Dashboard",
  "version": "1.1",
  "author": "Architect Mentor",
  "date": "2025-12-06",
  "revision": "QA fixes applied - ready for implementation",
  
  "type_glossary": {
    "description": "Internal service layer types vs external API schemas",
    "internal_types": {
      "MetricsSummary": {
        "purpose": "Internal dataclass returned by TokenMetricsService.get_summary()",
        "fields": {
          "total_pipelines": "int",
          "total_cost_usd": "float",
          "total_input_tokens": "int",
          "total_output_tokens": "int",
          "success_count": "int",
          "failure_count": "int",
          "last_usage_timestamp": "datetime | None"
        },
        "usage": "Service layer and HTML templates"
      },
      "PipelineMetrics": {
        "purpose": "Internal dataclass for per-pipeline breakdown",
        "fields": {
          "pipeline_id": "str",
          "status": "str",
          "current_phase": "str",
          "epic_description": "str | None",
          "total_cost_usd": "float",
          "total_input_tokens": "int",
          "total_output_tokens": "int",
          "phase_breakdown": "list[PhaseMetrics]"
        },
        "usage": "Service layer, templates, and converted to PipelineMetricsResponse for JSON API"
      },
      "PipelineSummary": {
        "purpose": "Lightweight pipeline info for lists",
        "fields": {
          "pipeline_id": "str",
          "epic_description": "str | None",
          "status": "str",
          "total_cost_usd": "float",
          "total_tokens": "int",
          "created_at": "datetime"
        },
        "usage": "Service layer for recent pipeline lists"
      },
      "DailyCost": {
        "purpose": "Daily aggregated cost for charts",
        "fields": {
          "date": "str (YYYY-MM-DD)",
          "total_cost_usd": "float"
        },
        "usage": "Service layer and chart templates"
      },
      "UsageRecord": {
        "purpose": "Database model from pipeline_prompt_usage table",
        "source": "Existing SQLAlchemy model",
        "usage": "Repository layer only"
      }
    },
    "pydantic_schemas": {
      "MetricsSummaryResponse": {
        "purpose": "JSON API response for GET /metrics/summary",
        "excludes": "last_usage_timestamp (used only in HTML templates)",
        "note": "HTML route receives full MetricsSummary object with timestamp for indicator calculation"
      },
      "PipelineMetricsResponse": {
        "purpose": "JSON API response for GET /metrics/pipelines/{id}",
        "source": "Mapped from internal PipelineMetrics"
      },
      "PhaseMetrics": {
        "purpose": "Shared schema for both internal and external use",
        "used_in": "Both PipelineMetrics and PipelineMetricsResponse"
      }
    }
  },
  
  "components": [
    {
      "name": "TokenMetricsService",
      "file_path": "app/orchestrator_api/services/token_metrics_service.py",
      "purpose": "Centralized service layer for all token usage and cost queries. Abstracts aggregation logic from routers and provides consistent error handling.",
      "responsibilities": [
        "Query pipeline_prompt_usage for system-wide aggregates",
        "Query pipeline_prompt_usage for per-pipeline breakdowns",
        "Join with pipelines table for status/phase info",
        "Handle missing data gracefully (return zeros/nulls)",
        "Apply performance-conscious SQL aggregation",
        "Format results for both JSON API and template consumption",
        "Catch all repository exceptions and convert to safe zero/empty results with logging",
        "Calculate last_usage_minutes from last_usage_timestamp for template indicator"
      ],
      "dependencies": [
        "app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository.PipelinePromptUsageRepository",
        "app.orchestrator_api.persistence.repositories.pipeline_repository.PipelineRepository",
        "app.orchestrator_api.persistence.database.get_db_session",
        "sqlalchemy.sql.functions (SUM, COUNT, MAX)",
        "datetime",
        "logging"
      ],
      "public_interface": [
        {
          "method": "get_summary",
          "signature": "get_summary() -> MetricsSummary",
          "returns": {
            "type": "MetricsSummary (internal dataclass)",
            "fields": {
              "total_pipelines": "int",
              "total_cost_usd": "float",
              "total_input_tokens": "int",
              "total_output_tokens": "int",
              "success_count": "int (status='completed')",
              "failure_count": "int (status IN ('failed', 'error'))",
              "last_usage_timestamp": "datetime | None"
            }
          },
          "description": "Returns system-wide aggregated metrics. Success_count = pipelines with status='completed'. Failure_count = pipelines with status IN ('failed', 'error'). Other statuses excluded from counts.",
          "error_handling": "Catches repository exceptions, logs warning, returns zeros/None for all fields"
        },
        {
          "method": "get_pipeline_metrics",
          "signature": "get_pipeline_metrics(pipeline_id: str) -> PipelineMetrics | None",
          "returns": {
            "type": "PipelineMetrics (internal dataclass) | None",
            "fields": {
              "pipeline_id": "str",
              "status": "str",
              "current_phase": "str",
              "epic_description": "str | None",
              "total_cost_usd": "float",
              "total_input_tokens": "int",
              "total_output_tokens": "int",
              "phase_breakdown": "list[PhaseMetrics]"
            }
          },
          "description": "Returns detailed metrics for a single pipeline, including per-phase breakdown. Returns None if pipeline not found.",
          "error_handling": "Catches repository exceptions, logs warning, returns None"
        },
        {
          "method": "get_recent_pipelines",
          "signature": "get_recent_pipelines(limit: int = 20) -> list[PipelineSummary]",
          "returns": {
            "type": "list[PipelineSummary] (internal dataclass)",
            "fields": {
              "pipeline_id": "str",
              "epic_description": "str | None",
              "status": "str",
              "total_cost_usd": "float",
              "total_tokens": "int",
              "created_at": "datetime"
            }
          },
          "description": "Returns most recent pipelines ordered by creation date descending",
          "error_handling": "Catches repository exceptions, logs warning, returns empty list"
        },
        {
          "method": "get_daily_costs",
          "signature": "get_daily_costs(days: int = 7) -> list[DailyCost]",
          "returns": {
            "type": "list[DailyCost] (internal dataclass)",
            "fields": {
              "date": "str (YYYY-MM-DD in database UTC timezone)",
              "total_cost_usd": "float"
            }
          },
          "description": "Returns daily aggregated costs for the last N days (database UTC), fills missing dates with 0.0. See ADR-014 for timezone considerations.",
          "error_handling": "Catches repository exceptions, logs warning, returns empty list"
        }
      ],
      "error_handling": [
        "Service layer wraps all repository calls in try/except",
        "Database/repository exceptions are caught, logged with details, and converted to safe return values",
        "Never propagates exceptions to router layer",
        "Returns zeros, empty lists, or None depending on method contract",
        "Logs all errors at WARNING level with context"
      ],
      "test_count": 12,
      "test_types": [
        "Unit: get_summary with mock repo (empty, populated)",
        "Unit: get_summary with repository exception",
        "Unit: get_pipeline_metrics (found, not found, no usage records)",
        "Unit: get_pipeline_metrics with repository exception",
        "Unit: get_recent_pipelines (empty, with data)",
        "Unit: get_daily_costs (7 days, sparse data, all zeros)",
        "Integration: actual DB queries with seeded data"
      ]
    },
    
    {
      "name": "MetricsRouter",
      "file_path": "app/orchestrator_api/routers/metrics.py",
      "purpose": "FastAPI router exposing metrics REST endpoints. Thin layer that delegates to TokenMetricsService. Intentionally unauthenticated - assumes trusted network access.",
      "responsibilities": [
        "Define GET /metrics/summary endpoint",
        "Define GET /metrics/pipelines/{pipeline_id} endpoint",
        "Define GET /metrics HTML dashboard endpoint",
        "Define GET /metrics/pipelines/{pipeline_id} HTML detail endpoint",
        "Validate path parameters",
        "Convert service layer dataclasses to JSON response schemas",
        "Render Jinja2 templates for HTML routes",
        "Handle 404 for invalid pipeline_id",
        "Pass full MetricsSummary (with last_usage_timestamp) to HTML templates for indicator calculation",
        "Pass only MetricsSummaryResponse fields to JSON endpoints (excludes last_usage_timestamp)"
      ],
      "dependencies": [
        "fastapi.APIRouter",
        "fastapi.HTTPException",
        "fastapi.Request",
        "fastapi.responses.HTMLResponse",
        "fastapi.templating.Jinja2Templates",
        "app.orchestrator_api.services.token_metrics_service.TokenMetricsService",
        "app.orchestrator_api.schemas.metrics (response models)"
      ],
      "public_interface": [
        {
          "method": "GET /metrics/summary",
          "response_model": "MetricsSummaryResponse",
          "status_code": 200,
          "description": "Returns system-wide aggregated metrics as JSON (excludes last_usage_timestamp)"
        },
        {
          "method": "GET /metrics/pipelines/{pipeline_id}",
          "response_model": "PipelineMetricsResponse",
          "status_code": "200 | 404",
          "description": "Returns per-pipeline metrics as JSON. 404 if not found."
        },
        {
          "method": "GET /metrics",
          "response_type": "HTMLResponse",
          "status_code": 200,
          "description": "Renders metrics overview dashboard (Jinja2 template). Receives full MetricsSummary with last_usage_timestamp for indicator."
        },
        {
          "method": "GET /metrics/pipelines/{pipeline_id}",
          "response_type": "HTMLResponse",
          "status_code": "200 | 404",
          "description": "Renders per-pipeline detail page (Jinja2 template). 404 if not found."
        }
      ],
      "authentication": {
        "policy": "None - endpoints are intentionally unauthenticated",
        "rationale": "Operator tool accessible only from trusted network",
        "note": "Router is registered without auth dependencies. If global auth is added later, explicitly exclude /metrics routes."
      },
      "error_handling": [
        "Service returns None: raise HTTPException(404)",
        "Service returns empty data: return valid response with zeros",
        "Template rendering errors propagate to FastAPI default 500 handler (logged automatically)",
        "Service layer guarantees no exceptions, so router only handles None returns"
      ],
      "test_count": 8,
      "test_types": [
        "Unit: JSON endpoints with mocked service",
        "Unit: HTML routes render templates correctly",
        "Unit: 404 handling for missing pipeline",
        "Integration: Full request/response cycle with test client"
      ]
    },
    
    {
      "name": "MetricsSchemas",
      "file_path": "app/orchestrator_api/schemas/metrics.py",
      "purpose": "Pydantic models for metrics API JSON responses. Note: HTML templates receive internal dataclasses directly.",
      "responsibilities": [
        "Define MetricsSummaryResponse schema (excludes last_usage_timestamp)",
        "Define PipelineMetricsResponse schema",
        "Define PhaseMetrics schema (shared across internal and external)",
        "Ensure JSON serialization compatibility",
        "Provide example values for OpenAPI docs"
      ],
      "dependencies": [
        "pydantic.BaseModel",
        "datetime",
        "typing"
      ],
      "public_interface": [
        {
          "schema": "MetricsSummaryResponse",
          "purpose": "JSON API response for GET /metrics/summary",
          "fields": {
            "total_pipelines": "int",
            "total_cost_usd": "float",
            "total_input_tokens": "int",
            "total_output_tokens": "int",
            "success_count": "int",
            "failure_count": "int"
          },
          "note": "Does NOT include last_usage_timestamp - that field is only used in HTML templates for the live indicator"
        },
        {
          "schema": "PipelineMetricsResponse",
          "purpose": "JSON API response for GET /metrics/pipelines/{id}",
          "fields": {
            "pipeline_id": "str",
            "status": "str",
            "current_phase": "str",
            "epic_description": "str | None",
            "total_cost_usd": "float",
            "total_input_tokens": "int",
            "total_output_tokens": "int",
            "phase_breakdown": "list[PhaseMetrics]"
          }
        },
        {
          "schema": "PhaseMetrics",
          "purpose": "Shared schema used in both internal PipelineMetrics and external PipelineMetricsResponse",
          "fields": {
            "phase_name": "str",
            "role_name": "str",
            "input_tokens": "int",
            "output_tokens": "int",
            "cost_usd": "float",
            "execution_time_ms": "int | None",
            "timestamp": "str"
          }
        }
      ],
      "error_handling": [
        "Pydantic validation handles type errors automatically",
        "Null handling via Optional types"
      ],
      "test_count": 7,
      "test_types": [
        "Unit: Schema validation with valid data",
        "Unit: Schema validation with missing optional fields",
        "Unit: JSON serialization round-trip"
      ]
    },
    
    {
      "name": "MetricsTemplates",
      "file_path": "app/orchestrator_api/templates/metrics/",
      "purpose": "Jinja2 HTML templates for operator dashboard UI.",
      "responsibilities": [
        "Render metrics overview page",
        "Render per-pipeline detail page",
        "Display live spend validation indicator",
        "Render cost trend chart with graceful fallback",
        "Provide consistent layout and styling"
      ],
      "dependencies": [
        "Jinja2",
        "Tailwind CSS (CDN)",
        "Chart.js (CDN, optional)",
        "templates/base.html (if exists)"
      ],
      "files": [
        {
          "file": "overview.html",
          "purpose": "Main metrics dashboard",
          "context_required": {
            "summary": "MetricsSummary (internal type with last_usage_timestamp)",
            "recent_pipelines": "list[PipelineSummary]",
            "daily_costs": "list[DailyCost]",
            "last_usage_minutes": "int | None (computed from summary.last_usage_timestamp)"
          }
        },
        {
          "file": "detail.html",
          "purpose": "Per-pipeline breakdown page",
          "context_required": {
            "pipeline": "PipelineMetrics (internal type)"
          }
        },
        {
          "file": "_indicator.html",
          "purpose": "Reusable live spend indicator component",
          "context_required": {
            "last_usage_minutes": "int | None"
          }
        },
        {
          "file": "_chart.html",
          "purpose": "Cost trend chart with table fallback",
          "context_required": {
            "daily_costs": "list[DailyCost]"
          }
        }
      ],
      "error_handling": [
        "Missing data: display '(no data available)' or '-'",
        "Chart.js load failure: detected via missing global Chart, show table",
        "Template syntax errors propagate to FastAPI (logged, 500 response)",
        "No manual try/except needed in templates - integration tests verify correctness"
      ],
      "test_count": 5,
      "test_types": [
        "Integration: Render overview with full data",
        "Integration: Render overview with empty data",
        "Integration: Render detail with full breakdown",
        "Integration: Render detail with missing epic",
        "Unit: Indicator logic for different time ranges"
      ]
    },
    
    {
      "name": "PipelineRepository (Extension)",
      "file_path": "app/orchestrator_api/persistence/repositories/pipeline_repository.py",
      "purpose": "Extend existing PipelineRepository with metrics-specific query methods if needed.",
      "responsibilities": [
        "Provide get_pipeline_with_epic(pipeline_id) for joining status + epic description",
        "Extract epic description from artifacts JSON if available"
      ],
      "modifications": [
        {
          "method": "get_pipeline_with_epic",
          "signature": "get_pipeline_with_epic(pipeline_id: str) -> dict | None",
          "returns": {
            "pipeline_id": "str",
            "status": "str",
            "current_phase": "str",
            "epic_description": "str | None",
            "created_at": "datetime"
          },
          "description": "Returns pipeline with epic_description extracted from artifacts JSON if available. Returns None if pipeline not found."
        }
      ],
      "dependencies": [
        "Existing PipelineRepository base",
        "SQLAlchemy models",
        "json module for artifacts parsing"
      ],
      "error_handling": [
        "Invalid JSON in artifacts: return None for epic_description",
        "Missing pipeline: return None",
        "Database errors: raise (let service layer handle)"
      ],
      "test_count": 3,
      "test_types": [
        "Unit: get_pipeline_with_epic (found with epic, found without epic, not found)"
      ]
    },
    
    {
      "name": "PipelinePromptUsageRepository (Extension)",
      "file_path": "app/orchestrator_api/persistence/repositories/pipeline_prompt_usage_repository.py",
      "purpose": "Extend with aggregation query methods for metrics service.",
      "responsibilities": [
        "Provide get_system_aggregates() for summary endpoint",
        "Provide get_pipeline_usage(pipeline_id) for per-pipeline breakdown",
        "Provide get_daily_aggregates(days) for chart data"
      ],
      "modifications": [
        {
          "method": "get_system_aggregates",
          "signature": "get_system_aggregates() -> dict",
          "returns": {
            "total_cost": "float",
            "total_input_tokens": "int",
            "total_output_tokens": "int",
            "count": "int",
            "last_timestamp": "datetime | None"
          },
          "implementation": "Single SQL query using SUM, COUNT, MAX aggregations on pipeline_prompt_usage table",
          "sql_example": "SELECT SUM(cost_usd), SUM(input_tokens), SUM(output_tokens), COUNT(*), MAX(created_at) FROM pipeline_prompt_usage"
        },
        {
          "method": "get_pipeline_usage",
          "signature": "get_pipeline_usage(pipeline_id: str) -> list[UsageRecord]",
          "returns": "List of usage records for the pipeline, ordered by created_at",
          "implementation": "Filter by pipeline_id, order by timestamp",
          "sql_example": "SELECT * FROM pipeline_prompt_usage WHERE pipeline_id = ? ORDER BY created_at"
        },
        {
          "method": "get_daily_aggregates",
          "signature": "get_daily_aggregates(days: int) -> list[dict]",
          "returns": "List of {date: str (YYYY-MM-DD), total_cost: float} for last N days",
          "implementation": "SQL GROUP BY DATE(created_at). Note: Uses database UTC timezone - see ADR-014 for timezone considerations.",
          "sql_example": "SELECT DATE(created_at) as date, SUM(cost_usd) as cost FROM pipeline_prompt_usage WHERE created_at >= DATE('now', '-7 days') GROUP BY DATE(created_at)"
        }
      ],
      "dependencies": [
        "Existing repository base",
        "SQLAlchemy aggregation functions (SUM, COUNT, MAX)",
        "datetime utilities"
      ],
      "error_handling": [
        "Empty results: return zeros/empty lists (valid data, not an error)",
        "Database errors: raise exception with context (service layer will catch and handle)"
      ],
      "test_count": 6,
      "test_types": [
        "Unit: Each aggregation method with mock data",
        "Integration: Actual queries with seeded usage records"
      ]
    }
  ],
  
  "adrs": [
    {
      "id": "ADR-011",
      "title": "Metrics Router as Separate Module",
      "decision": "Create dedicated metrics_router.py instead of adding endpoints to existing routers",
      "rationale": [
        "Metrics endpoints serve a different user persona (operator vs pipeline user)",
        "Keeps metrics logic isolated and removable if needed",
        "Allows independent evolution of metrics features",
        "Prevents bloating existing routers with UI concerns",
        "Simplifies testing by isolating metrics behavior"
      ],
      "consequences": {
        "positive": [
          "Clear separation of concerns",
          "Easy to disable/remove metrics if needed",
          "Independent test suite",
          "No risk of breaking existing API endpoints"
        ],
        "negative": [
          "Additional file in routers directory",
          "Need to register new router in main.py"
        ]
      },
      "alternatives_considered": [
        "Add to existing admin router - rejected due to auth concerns",
        "Add to pipeline router - rejected due to different purpose"
      ]
    },
    
    {
      "id": "ADR-012",
      "title": "TokenMetricsService Abstraction Layer",
      "decision": "Create service layer between routers and repositories for all metrics queries",
      "rationale": [
        "Prevents duplicate aggregation logic across JSON and HTML endpoints",
        "Centralizes error handling for missing/incomplete data",
        "Provides consistent data format for both API and templates",
        "Enables unit testing without database dependencies",
        "Encapsulates join logic between pipelines and usage tables",
        "Easier to optimize queries in single location"
      ],
      "consequences": {
        "positive": [
          "Single source of truth for metrics calculations",
          "Testable without full stack",
          "Easy to add caching later if needed",
          "Consistent error handling across all endpoints",
          "Service catches all repository exceptions and converts to safe return values"
        ],
        "negative": [
          "Additional layer of indirection",
          "One more file to maintain"
        ]
      },
      "error_handling_contract": {
        "repositories": "Raise exceptions on database errors (with context)",
        "service_layer": "Catch all repository exceptions, log warnings, return zeros/empty/None",
        "routers": "Receive safe data from service, only handle None → 404 conversion"
      },
      "alternatives_considered": [
        "Direct repository calls from router - rejected due to duplication",
        "Repository methods return formatted data - rejected due to mixing concerns"
      ]
    },
    
    {
      "id": "ADR-013",
      "title": "SQL Aggregation Over Python Iteration",
      "decision": "Use SQL SUM/COUNT/GROUP BY for all aggregations instead of fetching all records and computing in Python",
      "rationale": [
        "Database engines are optimized for aggregation operations",
        "Reduces data transfer between database and application",
        "Scales better as usage records grow",
        "SQLite supports GROUP BY and aggregate functions efficiently",
        "Enables <2 second response time even with 1000 pipelines",
        "Reduces memory footprint in application layer"
      ],
      "consequences": {
        "positive": [
          "Fast queries even with large datasets",
          "Low memory usage",
          "Leverages database strengths",
          "Simple migration to PostgreSQL if needed"
        ],
        "negative": [
          "Slightly more complex SQL queries",
          "Requires understanding of aggregation functions"
        ]
      },
      "alternatives_considered": [
        "Fetch all, aggregate in Python - rejected due to performance",
        "Pandas DataFrame aggregation - rejected due to unnecessary dependency"
      ]
    },
    
    {
      "id": "ADR-014",
      "title": "SQLite Performance Strategy and Timezone Handling",
      "decision": "Rely on existing indexes and small dataset size rather than adding new indexes for metrics queries. Use database UTC timezone for daily cost grouping.",
      "rationale": [
        "Current usage: <1000 pipelines expected in near term",
        "SQLite full table scans are fast for tables under 100K rows",
        "Pipeline_prompt_usage already has pipeline_id foreign key",
        "Adding indexes prematurely violates YAGNI",
        "Can add indexes later if performance degrades",
        "Metrics dashboard is operator tool, not user-facing",
        "Database UTC timezone is acceptable for MVP - operator tool doesn't require local timezone calendar days"
      ],
      "consequences": {
        "positive": [
          "No schema changes required",
          "Simpler implementation",
          "Faster writes (no index maintenance)",
          "Easier to remove feature if unneeded"
        ],
        "negative": [
          "May need optimization later if dataset grows",
          "Query times may increase with scale",
          "Daily cost bars use database time (likely UTC), not operator's local timezone"
        ],
        "mitigation": [
          "Monitor query times in health check",
          "Add indexes if response time exceeds 2 seconds",
          "Document timezone behavior: daily grouping uses database UTC; local-timezone calendar days can be added later if needed"
        ]
      },
      "timezone_note": "Daily cost aggregation uses DATE(created_at) which operates in database timezone (typically UTC). This is acceptable for an operator tool. Future enhancement could add timezone conversion for local calendar days.",
      "alternatives_considered": [
        "Add created_at index - deferred until proven necessary",
        "Materialized view - rejected as over-engineering for MVP",
        "Client-side timezone conversion - deferred to future if needed"
      ]
    },
    
    {
      "id": "ADR-015",
      "title": "Server-Rendered UI with Jinja2",
      "decision": "Use Jinja2 templates for all HTML rendering instead of React/Vue SPA or HTMX-heavy approach",
      "rationale": [
        "Matches existing FastAPI + Jinja2 pattern in codebase",
        "No build tooling required (no npm, webpack, etc.)",
        "No client-side state management complexity",
        "Fast time-to-interactive (no large JS bundles)",
        "Operator dashboard doesn't need real-time updates",
        "Full page reload acceptable for metrics viewing",
        "Works with CDN-based Tailwind CSS"
      ],
      "consequences": {
        "positive": [
          "Zero build pipeline",
          "Simple deployment",
          "Fast development iteration",
          "Easy to debug",
          "Low maintenance burden"
        ],
        "negative": [
          "Full page reload on navigation",
          "No real-time updates without polling",
          "Limited interactivity"
        ],
        "accepted_tradeoffs": [
          "30-second auto-refresh acceptable for operator tool",
          "Static snapshots meet confidence-building goal"
        ]
      },
      "alternatives_considered": [
        "React SPA - rejected due to build complexity",
        "HTMX partial updates - deferred to future if needed",
        "Alpine.js for interactivity - kept as option for future"
      ]
    },
    
    {
      "id": "ADR-016",
      "title": "Chart.js with Graceful Degradation",
      "decision": "Use Chart.js from CDN for cost trend visualization with automatic fallback to HTML table if CDN fails",
      "rationale": [
        "Chart.js is lightweight and widely supported",
        "CDN delivery means no npm/build requirement",
        "Graceful degradation ensures data always visible",
        "Table fallback provides same information in accessible format",
        "Operator can function fully even if chart fails",
        "Detection via `typeof Chart === 'undefined'` is reliable"
      ],
      "consequences": {
        "positive": [
          "Enhanced UX when chart loads",
          "No hard dependency on external CDN",
          "Accessibility maintained via table fallback",
          "Progressive enhancement pattern"
        ],
        "negative": [
          "External CDN dependency for visualization",
          "Need to maintain both chart and table code paths"
        ],
        "mitigation": [
          "Table is primary interface, chart is enhancement",
          "Test both code paths in integration tests"
        ]
      },
      "alternatives_considered": [
        "Pure CSS bar chart - rejected due to complexity",
        "SVG generation server-side - rejected as over-engineering",
        "No visualization - rejected as missing UX opportunity"
      ]
    }
  ],
  
  "test_strategy": {
    "unit_tests": {
      "total_count": 36,
      "components": [
        {
          "component": "TokenMetricsService",
          "count": 12,
          "focus": [
            "Aggregation logic with mocked repositories",
            "Null/empty data handling",
            "Data transformation correctness",
            "Exception catching and conversion to safe values",
            "Success/failure count calculation"
          ]
        },
        {
          "component": "MetricsRouter",
          "count": 8,
          "focus": [
            "Endpoint routing with mocked service",
            "JSON response serialization",
            "404 handling for invalid pipeline_id",
            "Template context passing",
            "Conversion of internal types to response schemas"
          ]
        },
        {
          "component": "MetricsSchemas",
          "count": 7,
          "focus": [
            "Pydantic validation",
            "Optional field handling",
            "JSON serialization"
          ]
        },
        {
          "component": "Repository Extensions",
          "count": 9,
          "focus": [
            "SQL aggregation correctness",
            "Empty result handling",
            "Date range calculations",
            "Exception raising on database errors"
          ]
        }
      ]
    },
    
    "integration_tests": {
      "total_count": 12,
      "components": [
        {
          "test": "GET /metrics/summary with seeded data",
          "validates": "Full aggregation pipeline from DB to JSON"
        },
        {
          "test": "GET /metrics/pipelines/{id} with complete usage records",
          "validates": "Per-pipeline breakdown accuracy"
        },
        {
          "test": "GET /metrics/pipelines/{id} with missing pipeline",
          "validates": "404 response handling"
        },
        {
          "test": "GET /metrics HTML renders with data",
          "validates": "Template rendering and context passing"
        },
        {
          "test": "GET /metrics HTML renders with empty data",
          "validates": "Graceful handling of zero metrics"
        },
        {
          "test": "GET /metrics/pipelines/{id} HTML with full breakdown",
          "validates": "Detail page rendering"
        },
        {
          "test": "Live indicator shows green for recent usage",
          "validates": "Last usage timestamp logic"
        },
        {
          "test": "Live indicator shows red for stale data",
          "validates": "Indicator state transitions"
        },
        {
          "test": "Daily costs aggregate correctly over 7 days",
          "validates": "Date grouping and cost summation"
        },
        {
          "test": "Chart fallback renders table when Chart.js unavailable",
          "validates": "Graceful degradation mechanism"
        },
        {
          "test": "Epic description displays or shows fallback",
          "validates": "Missing epic handling in UI"
        },
        {
          "test": "Performance: /metrics/summary responds <2s with 1000 pipelines",
          "validates": "Soft performance target (warning/log, not hard fail)",
          "note": "This is a benchmark test that logs warnings if threshold exceeded, not a blocking assertion"
        }
      ]
    },
    
    "test_data_requirements": [
      "Seed 50 pipelines with varying statuses: 30 'completed', 10 'failed', 5 'error', 5 'in_progress'",
      "Seed 200+ usage records across pipelines",
      "Include pipelines with no usage records",
      "Include pipelines with missing epic artifacts",
      "Include usage records from last 7 days (distributed across dates)",
      "Include at least one pipeline with all phases executed"
    ],
    
    "performance_targets": {
      "GET /metrics/summary": "<2 seconds for 1000 pipelines (soft target, warning if exceeded)",
      "GET /metrics/pipelines/{id}": "<2 seconds for 50 phases (soft target)",
      "GET /metrics HTML": "<2 seconds page render (soft target)",
      "note": "These are soft targets that trigger warnings/logs, not hard test failures. Allows for CI environment variability."
    }
  },
  
  "acceptance_criteria_mapping": [
    {
      "story_id": "PIPELINE-175D-1",
      "title": "Metrics aggregation endpoint",
      "components_new": [
        "TokenMetricsService.get_summary() (partial)",
        "MetricsSchemas.MetricsSummaryResponse"
      ],
      "components_modified": [
        "PipelinePromptUsageRepository.get_system_aggregates()"
      ],
      "data_sources": [
        "pipeline_prompt_usage table (SUM cost_usd, SUM tokens, COUNT, MAX created_at)",
        "pipelines table (COUNT by status for success/failure)"
      ],
      "success_failure_definition": {
        "success_count": "COUNT of pipelines where status = 'completed'",
        "failure_count": "COUNT of pipelines where status IN ('failed', 'error')",
        "excluded_statuses": "in_progress, cancelled, reset, or any other status not explicitly counted"
      },
      "template_context": "N/A (JSON endpoint)",
      "queries": [
        "SELECT SUM(cost_usd) as total_cost, SUM(input_tokens) as total_input, SUM(output_tokens) as total_output, COUNT(*) as count, MAX(created_at) as last_timestamp FROM pipeline_prompt_usage",
        "SELECT COUNT(*) FROM pipelines WHERE status = 'completed'",
        "SELECT COUNT(*) FROM pipelines WHERE status IN ('failed', 'error')"
      ]
    },
    
    {
      "story_id": "PIPELINE-175D-2",
      "title": "Per-pipeline metrics endpoint",
      "components_new": [
        "TokenMetricsService.get_pipeline_metrics()",
        "MetricsSchemas.PipelineMetricsResponse",
        "MetricsSchemas.PhaseMetrics"
      ],
      "components_modified": [
        "PipelinePromptUsageRepository.get_pipeline_usage()",
        "PipelineRepository.get_pipeline_with_epic()"
      ],
      "data_sources": [
        "pipeline_prompt_usage filtered by pipeline_id",
        "pipelines table for status and phase",
        "artifacts JSON for epic description"
      ],
      "template_context": "N/A (JSON endpoint)",
      "queries": [
        "SELECT * FROM pipeline_prompt_usage WHERE pipeline_id = ? ORDER BY created_at",
        "SELECT id, status, current_phase, artifacts FROM pipelines WHERE id = ?"
      ]
    },
    
    {
      "story_id": "PIPELINE-175D-3",
      "title": "Metrics service layer",
      "components_new": [
        "TokenMetricsService (complete implementation with error handling)"
      ],
      "components_modified": [],
      "data_sources": [
        "Delegates to repository extensions"
      ],
      "template_context": "N/A (service layer)",
      "queries": "N/A (delegated to repositories)",
      "error_handling_implementation": {
        "pattern": "Service wraps all repository calls in try/except",
        "on_exception": "Log warning with context, return safe default (zeros/empty/None)",
        "guarantee": "Never propagates exceptions to router layer"
      }
    },
    
    {
      "story_id": "PIPELINE-175D-4",
      "title": "Metrics overview HTML page",
      "components_new": [
        "MetricsRouter.GET /metrics",
        "templates/metrics/overview.html",
        "TokenMetricsService.get_recent_pipelines()"
      ],
      "components_modified": [],
      "data_sources": [
        "MetricsSummary (internal type with last_usage_timestamp) from service",
        "Recent pipelines list from service",
        "Daily costs for chart"
      ],
      "template_context": {
        "summary": "MetricsSummary object (includes last_usage_timestamp)",
        "recent_pipelines": "list[PipelineSummary] (limit 20)",
        "daily_costs": "list[DailyCost] (7 days)",
        "last_usage_minutes": "int | None (calculated from summary.last_usage_timestamp)"
      },
      "queries": [
        "Aggregation query for summary",
        "SELECT * FROM pipelines ORDER BY created_at DESC LIMIT 20",
        "Daily aggregation for chart"
      ]
    },
    
    {
      "story_id": "PIPELINE-175D-5",
      "title": "Per-pipeline detail page",
      "components_new": [
        "MetricsRouter.GET /metrics/pipelines/{pipeline_id} (HTML)",
        "templates/metrics/detail.html"
      ],
      "components_modified": [],
      "data_sources": [
        "PipelineMetrics (internal type) from service"
      ],
      "template_context": {
        "pipeline": "PipelineMetrics object with full phase breakdown"
      },
      "queries": [
        "Pipeline-specific queries from story 175D-2"
      ]
    },
    
    {
      "story_id": "PIPELINE-175D-6",
      "title": "Live spend validation indicator",
      "components_new": [
        "templates/metrics/_indicator.html",
        "Indicator logic in overview template"
      ],
      "components_modified": [
        "TokenMetricsService.get_summary() (already returns last_usage_timestamp in MetricsSummary)"
      ],
      "data_sources": [
        "MAX(created_at) from pipeline_prompt_usage (via get_summary)"
      ],
      "template_context": {
        "last_usage_minutes": "int | None (calculated from summary.last_usage_timestamp)"
      },
      "queries": [
        "SELECT MAX(created_at) FROM pipeline_prompt_usage (part of get_summary query)"
      ],
      "indicator_logic": {
        "green": "< 10 minutes ago",
        "yellow": "10-60 minutes ago",
        "red": "> 60 minutes ago or None",
        "grey": "Query failed (summary.last_usage_timestamp is None due to exception)"
      }
    },
    
    {
      "story_id": "PIPELINE-175D-7",
      "title": "Simple cost trend visualization",
      "components_new": [
        "templates/metrics/_chart.html",
        "TokenMetricsService.get_daily_costs()"
      ],
      "components_modified": [
        "PipelinePromptUsageRepository.get_daily_aggregates()"
      ],
      "data_sources": [
        "pipeline_prompt_usage grouped by DATE(created_at)"
      ],
      "template_context": {
        "daily_costs": "list[DailyCost] with date (YYYY-MM-DD in database UTC) and total_cost_usd"
      },
      "queries": [
        "SELECT DATE(created_at) as date, SUM(cost_usd) as cost FROM pipeline_prompt_usage WHERE created_at >= DATE('now', '-7 days') GROUP BY DATE(created_at)"
      ],
      "timezone_note": "Daily grouping uses database UTC timezone. See ADR-014 for details. Local timezone conversion deferred to future if needed.",
      "fallback_mechanism": {
        "detection": "typeof Chart === 'undefined' in client-side JS",
        "action": "Hide #chart-container, show #chart-fallback-table"
      }
    },
    
    {
      "story_id": "PIPELINE-175D-8",
      "title": "Metrics integration tests",
      "components_new": [
        "tests/integration/test_metrics_endpoints.py",
        "tests/integration/test_metrics_templates.py"
      ],
      "components_modified": [],
      "data_sources": [
        "Test database with seeded pipelines and usage records"
      ],
      "template_context": "N/A (tests verify context is correct)",
      "test_scenarios": [
        "All endpoints with full data",
        "All endpoints with empty data",
        "Missing pipeline 404 handling",
        "Missing epic description fallback",
        "In-flight pipeline with incomplete usage",
        "Chart fallback rendering",
        "Service layer exception handling",
        "Success/failure count calculation"
      ]
    }
  ],
  
  "deployment_notes": {
    "router_registration": "Add MetricsRouter to app/orchestrator_api/main.py: app.include_router(metrics_router, tags=['metrics'])",
    "authentication_note": "MetricsRouter is intentionally registered WITHOUT auth dependencies. If global auth is added later, explicitly exclude /metrics routes or add to public routes list.",
    "template_directory": "Create app/orchestrator_api/templates/metrics/ directory",
    "static_dependencies": [
      "Tailwind CSS CDN: https://cdn.tailwindcss.com",
      "Chart.js CDN: https://cdn.jsdelivr.net/npm/chart.js"
    ],
    "database_changes": "None - uses existing schema from 175C",
    "configuration_changes": "None required",
    "backward_compatibility": "100% - only adds new endpoints, no modifications to existing routes"
  },
  
  "risks_and_mitigations": [
    {
      "risk": "Large datasets (>1000 pipelines) may cause slow queries",
      "likelihood": "Low (operator tool, not production analytics)",
      "impact": "Medium (poor UX for operator)",
      "mitigation": "Monitor query times; add indexes if needed; document in ADR-014"
    },
    {
      "risk": "Chart.js CDN unavailable",
      "likelihood": "Low",
      "impact": "Low (graceful fallback to table)",
      "mitigation": "Fallback mechanism built-in; table provides same data"
    },
    {
      "risk": "Missing epic descriptions cause UI issues",
      "likelihood": "Medium (pipelines may fail before PM phase)",
      "impact": "Low (handled with fallback text)",
      "mitigation": "Explicit null handling in templates and service layer"
    },
    {
      "risk": "Service layer exception handling misunderstood",
      "likelihood": "Low (explicitly documented)",
      "impact": "Medium (could cause 500 errors if not implemented correctly)",
      "mitigation": "Clear error handling contract in ADR-012; comprehensive unit tests verify exception catching"
    },
    {
      "risk": "Timezone confusion in daily cost display",
      "likelihood": "Medium (operator may expect local timezone)",
      "impact": "Low (minor UX issue)",
      "mitigation": "Document in ADR-014; acceptable for MVP; can add local timezone later if needed"
    }
  ],
  
  "future_enhancements": {
    "deferred_to_later": [
      "Date range filtering (custom start/end dates)",
      "CSV export of metrics",
      "Real-time updates via WebSocket",
      "Cost alerting/notifications",
      "Multi-tenant filtering",
      "Advanced charting (line charts, pie charts)",
      "Caching layer for aggregations",
      "Pagination for large pipeline lists",
      "Local timezone conversion for daily costs"
    ],
    "potential_175e_features": [
      "Cost breakdown by role (PM vs Dev vs QA)",
      "Token efficiency metrics (tokens per story point)",
      "Comparison between pipeline runs"
    ]
  }
}