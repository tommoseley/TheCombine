# WP-DCW-001: Work Package and Work Statement Document Creation Workflows

## Status: Accepted

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline WP/WS Integration
- ADR-053 -- Planning Before Architecture in Software Product Development

---

## Intent

Complete the WP/WS ontology migration by building the DCWs that produce Work Package and Work Statement documents, rewriting the software_product_development POW to use them, and eliminating all remaining Epic/Feature references from the runtime system. Also clean up stale seed system references, migrating anything still needed to combine-config.

This is the last structural work before the pipeline can produce WP/WS artifacts through the runtime system.

---

## Scope In

- DCW definition for Work Package production (from IPF output)
- DCW definition for Work Statement decomposition (from WP)
- Prompts and schemas for WP and WS production
- Rewrite software_product_development POW to WP/WS ontology
- Remove all remaining Epic/Feature references from runtime code
- Audit and migrate stale seed system references to combine-config

## Scope Out

- Logbook activation (needs runtime WS acceptance, which this enables but does not implement)
- TA emitting ADR candidates
- WP/WS state machine UI (state transitions are already built, UI affordances are future)
- Circuit breaker, provider switching, metrics

---

## Definition of Done

1. WP DCW exists and can produce Work Package documents from IPF output
2. WS DCW exists and can decompose a WP into Work Statement documents
3. software_product_development POW uses WP/WS ontology throughout (scopes, doc types, entity types, iteration)
4. No runtime code references Epic/Feature as document types or entity types
5. All active seed references point to combine-config, not legacy seed paths
6. Tier 0 green
7. Pipeline can execute Discovery -> IPP -> IPF -> TA -> WP production -> WS decomposition

---

## Tech Debt (Acknowledged)

| Item | Current Approach | Preferred Approach | When |
|------|------------------|--------------------|------|
| WS acceptance triggering logbook | Manual acceptance | Runtime acceptance via pipeline | When WP/WS DCWs are proven in production |
| TA conflict detection on WPs | None (ADR-053 Phase 1) | Soft enforcement with staleness markers | After beta |

---

## Execution Order

1. WS-DCW-001 -- Work Package DCW (definition, prompts, schema)
2. WS-DCW-002 -- Work Statement DCW (definition, prompts, schema)
3. WS-DCW-003 -- Rewrite software_product_development POW
4. WS-DCW-004 -- Remove remaining Epic/Feature references from runtime
5. WS-DCW-005 -- Audit and migrate seed system to combine-config

WS-001 and WS-002 are independent of each other but both must precede WS-003.
WS-004 depends on WS-003 (POW must be rewritten before removing references it depended on).
WS-005 is independent and can execute in parallel with any other WS.

---

_End of WP-DCW-001_
