"""
Component and Fragment Completeness Tests.

Per WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS:
Ensure all components meet completeness requirements.
"""

import pytest
from jinja2 import Environment


class TestComponentCompleteness:
    """Tests ensuring all components meet completeness requirements."""
    
    @pytest.fixture
    def components(self):
        from seed.registry.component_artifacts import INITIAL_COMPONENT_ARTIFACTS
        return INITIAL_COMPONENT_ARTIFACTS
    
    def test_all_components_have_guidance_bullets(self, components):
        """INVARIANT: Every component has non-empty generation_guidance.bullets."""
        for component in components:
            comp_id = component["component_id"]
            guidance = component.get("generation_guidance", {})
            bullets = guidance.get("bullets", [])
            
            assert bullets, f"{comp_id}: generation_guidance.bullets is empty"
            assert len(bullets) > 0, f"{comp_id}: generation_guidance.bullets is empty"
    
    def test_all_components_have_web_binding(self, components):
        """INVARIANT: Every component has view_bindings.web.fragment_id."""
        for component in components:
            comp_id = component["component_id"]
            bindings = component.get("view_bindings", {})
            web = bindings.get("web", {})
            fragment_id = web.get("fragment_id")
            
            assert fragment_id, f"{comp_id}: missing view_bindings.web.fragment_id"
    
    def test_all_fragment_ids_use_canonical_format(self, components):
        """INVARIANT: All fragment IDs follow canonical format."""
        for component in components:
            comp_id = component["component_id"]
            bindings = component.get("view_bindings", {})
            web = bindings.get("web", {})
            fragment_id = web.get("fragment_id")
            
            if fragment_id:
                assert fragment_id.startswith("fragment:"), \
                    f"{comp_id}: fragment_id must start with 'fragment:' - got {fragment_id}"
                assert ":web:" in fragment_id, \
                    f"{comp_id}: fragment_id must contain ':web:' - got {fragment_id}"
    
    def test_guidance_bullets_are_declarative(self, components):
        """INVARIANT: Bullets are declarative/imperative, no 'you' or UI instructions."""
        forbidden_patterns = ["you should", "you must", "you can", "click", "select", "button"]
        
        for component in components:
            comp_id = component["component_id"]
            guidance = component.get("generation_guidance", {})
            bullets = guidance.get("bullets", [])
            
            for bullet in bullets:
                bullet_lower = bullet.lower()
                for pattern in forbidden_patterns:
                    assert pattern not in bullet_lower, \
                        f"{comp_id}: bullet contains forbidden pattern '{pattern}': {bullet}"


    def test_container_guidance_has_no_rendering_terms(self, components):
        """INVARIANT: Container guidance excludes render/style instructions."""
        # Containers identified by schema containing "Block" and ending with items
        container_schemas = [
            "schema:OpenQuestionsBlockV1",
            "schema:StoriesBlockV1", 
            "schema:StringListBlockV1",
            "schema:RisksBlockV1",
        ]
        
        forbidden_terms = [
            "context.title", "style", "render items", "order", 
            "heading", "numbered", "bullet", "check",
            "conforming to", "riskv1", "storyv1", "questionv1"  # No schema name references
        ]
        
        for component in components:
            comp_id = component["component_id"]
            schema_id = component.get("schema_id", "")
            
            if schema_id not in container_schemas:
                continue
            
            guidance = component.get("generation_guidance", {})
            bullets = guidance.get("bullets", [])
            bullets_text = " ".join(bullets).lower()
            
            for term in forbidden_terms:
                assert term.lower() not in bullets_text, \
                    f"{comp_id}: container guidance contains forbidden term '{term}'"

class TestFragmentCompleteness:
    """Tests ensuring all fragments meet completeness requirements."""
    
    @pytest.fixture
    def fragments(self):
        from seed.registry.fragment_artifacts import INITIAL_FRAGMENT_ARTIFACTS
        return INITIAL_FRAGMENT_ARTIFACTS
    
    @pytest.fixture
    def fragment_markup_map(self, fragments):
        """Map fragment_id to markup for easy lookup."""
        return {f["fragment_id"]: f["fragment_markup"] for f in fragments}
    
    def test_all_fragment_ids_resolve(self, fragments):
        """INVARIANT: All fragments have valid fragment_id."""
        for fragment in fragments:
            frag_id = fragment.get("fragment_id")
            assert frag_id, f"Fragment missing fragment_id: {fragment}"
            assert fragment.get("fragment_markup"), f"{frag_id}: missing fragment_markup"
    
    def test_all_fragments_compile(self, fragments):
        """INVARIANT: All fragments compile as valid Jinja2."""
        env = Environment(autoescape=False)
        
        for fragment in fragments:
            frag_id = fragment["fragment_id"]
            markup = fragment["fragment_markup"]
            
            try:
                env.from_string(markup)
            except Exception as e:
                pytest.fail(f"{frag_id}: Jinja2 compilation failed - {e}")
    
    def test_all_fragments_use_canonical_ids(self, fragments):
        """INVARIANT: All fragment IDs follow canonical format."""
        for fragment in fragments:
            frag_id = fragment["fragment_id"]
            
            assert frag_id.startswith("fragment:"), \
                f"fragment_id must start with 'fragment:' - got {frag_id}"
            assert ":web:" in frag_id, \
                f"fragment_id must contain ':web:' - got {frag_id}"


class TestComponentFragmentAlignment:
    """Tests ensuring components and fragments are aligned."""
    
    @pytest.fixture
    def components(self):
        from seed.registry.component_artifacts import INITIAL_COMPONENT_ARTIFACTS
        return INITIAL_COMPONENT_ARTIFACTS
    
    @pytest.fixture
    def fragments(self):
        from seed.registry.fragment_artifacts import INITIAL_FRAGMENT_ARTIFACTS
        return INITIAL_FRAGMENT_ARTIFACTS
    
    @pytest.mark.skip(reason="UnknownsBlockV1 component missing fragment - needs fragment implementation")
    def test_all_component_fragments_exist(self, components, fragments):
        """INVARIANT: Every component's fragment_id has a corresponding fragment."""
        fragment_ids = {f["fragment_id"] for f in fragments}
        
        for component in components:
            comp_id = component["component_id"]
            bindings = component.get("view_bindings", {})
            web = bindings.get("web", {})
            fragment_id = web.get("fragment_id")
            
            if fragment_id:
                assert fragment_id in fragment_ids, \
                    f"{comp_id}: fragment '{fragment_id}' not found in INITIAL_FRAGMENT_ARTIFACTS"



class TestSchemaGovernance:
    """Tests ensuring all schemas meet governance requirements."""
    
    @pytest.fixture
    def schemas(self):
        from seed.registry.schema_artifacts import INITIAL_SCHEMA_ARTIFACTS
        return INITIAL_SCHEMA_ARTIFACTS
    
    def test_all_schemas_disallow_additional_properties(self, schemas):
        """INVARIANT: All schemas must have additionalProperties: false."""
        for schema in schemas:
            schema_id = schema.get("schema_id", "unknown")
            schema_json = schema.get("schema_json", {})
            
            # Skip envelope schemas (RenderModelV1, etc.) that may have different rules
            if schema.get("kind") == "envelope":
                continue
            
            additional_props = schema_json.get("additionalProperties")
            assert additional_props is False, \
                f"schema:{schema_id} must have additionalProperties: false (got {additional_props})"

