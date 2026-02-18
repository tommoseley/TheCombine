"""
Tier-1 tests for set_reconciler.py.

Pure in-memory, no DB, no LLM.
Tests ID-only reconciliation for backlog item sets.

WS-BCP-005.
"""


from app.domain.services.set_reconciler import (
    reconcile,
)


# ---------------------------------------------------------------------------
# Fixtures: minimal backlog item builders
# ---------------------------------------------------------------------------

def item(id, level="FEATURE", parent_id="E001", priority=50, summary=""):
    return {
        "schema_version": "1.0.0",
        "id": id,
        "level": level,
        "title": f"Item {id}",
        "summary": summary or f"Summary for {id}",
        "priority_score": priority,
        "depends_on": [],
        "parent_id": parent_id,
    }


# ===========================================================================
# All-adds (first run, no existing items)
# ===========================================================================

class TestAllAdds:

    def test_empty_existing_all_candidates_added(self):
        existing = []
        candidates = [item("F001"), item("F002"), item("F003")]
        result = reconcile(existing, candidates)
        assert len(result.adds) == 3
        assert len(result.keeps) == 0
        assert len(result.drops) == 0
        assert not result.has_drops

    def test_adds_sorted_by_id(self):
        existing = []
        candidates = [item("F003"), item("F001"), item("F002")]
        result = reconcile(existing, candidates)
        add_ids = [i["id"] for i in result.adds]
        assert add_ids == ["F001", "F002", "F003"]


# ===========================================================================
# All-keeps (identical re-run)
# ===========================================================================

class TestAllKeeps:

    def test_same_ids_all_kept(self):
        existing = [item("F001"), item("F002")]
        candidates = [item("F001"), item("F002")]
        result = reconcile(existing, candidates)
        assert len(result.keeps) == 2
        assert len(result.adds) == 0
        assert len(result.drops) == 0

    def test_keeps_return_candidate_version(self):
        """When ID matches, the candidate version is returned (details may differ)."""
        existing = [item("F001", summary="Old summary")]
        candidates = [item("F001", summary="New summary")]
        result = reconcile(existing, candidates)
        assert len(result.keeps) == 1
        assert result.keeps[0]["summary"] == "New summary"


# ===========================================================================
# Mixed add/keep/drop
# ===========================================================================

class TestMixed:

    def test_mixed_reconciliation(self):
        existing = [item("F001"), item("F002"), item("F003")]
        candidates = [item("F002"), item("F003"), item("F004")]
        result = reconcile(existing, candidates)
        assert [i["id"] for i in result.keeps] == ["F002", "F003"]
        assert [i["id"] for i in result.adds] == ["F004"]
        assert [i["id"] for i in result.drops] == ["F001"]
        assert result.has_drops

    def test_complete_replacement(self):
        """All existing dropped, all candidates added."""
        existing = [item("F001"), item("F002")]
        candidates = [item("F003"), item("F004")]
        result = reconcile(existing, candidates)
        assert len(result.keeps) == 0
        assert len(result.adds) == 2
        assert len(result.drops) == 2

    def test_summary_counts(self):
        existing = [item("F001"), item("F002"), item("F003")]
        candidates = [item("F002"), item("F004")]
        result = reconcile(existing, candidates)
        assert result.summary == {"keeps": 1, "adds": 1, "drops": 2}


# ===========================================================================
# Order insensitivity
# ===========================================================================

class TestOrderInsensitivity:

    def test_existing_order_irrelevant(self):
        existing_a = [item("F001"), item("F002"), item("F003")]
        existing_b = [item("F003"), item("F001"), item("F002")]
        candidates = [item("F002"), item("F004")]

        result_a = reconcile(existing_a, candidates)
        result_b = reconcile(existing_b, candidates)

        assert [i["id"] for i in result_a.keeps] == [i["id"] for i in result_b.keeps]
        assert [i["id"] for i in result_a.adds] == [i["id"] for i in result_b.adds]
        assert [i["id"] for i in result_a.drops] == [i["id"] for i in result_b.drops]

    def test_candidate_order_irrelevant(self):
        existing = [item("F001"), item("F002")]
        candidates_a = [item("F002"), item("F003")]
        candidates_b = [item("F003"), item("F002")]

        result_a = reconcile(existing, candidates_a)
        result_b = reconcile(existing, candidates_b)

        assert [i["id"] for i in result_a.keeps] == [i["id"] for i in result_b.keeps]
        assert [i["id"] for i in result_a.adds] == [i["id"] for i in result_b.adds]


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:

    def test_empty_existing_empty_candidates(self):
        result = reconcile([], [])
        assert result.keeps == []
        assert result.adds == []
        assert result.drops == []
        assert not result.has_drops

    def test_empty_candidates_all_dropped(self):
        existing = [item("F001"), item("F002")]
        result = reconcile(existing, [])
        assert len(result.drops) == 2
        assert len(result.keeps) == 0
        assert len(result.adds) == 0
        assert result.has_drops

    def test_single_item_kept(self):
        existing = [item("F001")]
        candidates = [item("F001")]
        result = reconcile(existing, candidates)
        assert len(result.keeps) == 1
        assert len(result.adds) == 0
        assert len(result.drops) == 0

    def test_drops_return_existing_version(self):
        """Dropped items are the existing versions (for display in modal)."""
        existing = [item("F001", summary="Original")]
        candidates = []
        result = reconcile(existing, candidates)
        assert result.drops[0]["summary"] == "Original"


# ===========================================================================
# Cross-level usage (stories under features)
# ===========================================================================

class TestStoryReconciliation:

    def test_story_reconciliation(self):
        """SetReconciler works for any level, not just features."""
        existing = [
            item("S001", level="STORY", parent_id="F001"),
            item("S002", level="STORY", parent_id="F001"),
        ]
        candidates = [
            item("S002", level="STORY", parent_id="F001"),
            item("S003", level="STORY", parent_id="F001"),
        ]
        result = reconcile(existing, candidates)
        assert [i["id"] for i in result.keeps] == ["S002"]
        assert [i["id"] for i in result.adds] == ["S003"]
        assert [i["id"] for i in result.drops] == ["S001"]


# ===========================================================================
# Determinism
# ===========================================================================

class TestDeterminism:

    def test_same_input_same_output(self):
        existing = [item("F003"), item("F001")]
        candidates = [item("F002"), item("F001")]
        r1 = reconcile(existing, candidates)
        r2 = reconcile(existing, candidates)
        assert [i["id"] for i in r1.keeps] == [i["id"] for i in r2.keeps]
        assert [i["id"] for i in r1.adds] == [i["id"] for i in r2.adds]
        assert [i["id"] for i in r1.drops] == [i["id"] for i in r2.drops]
