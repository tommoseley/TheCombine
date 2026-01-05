"""Tests for template rendering.

Ensures all templates can be rendered without TemplateNotFound errors.
This catches issues like missing public/ prefixes in extends/includes.
"""

import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class TestTemplateIntegrity:
    """Validate all templates can load their dependencies."""
    
    @pytest.fixture
    def jinja_env(self):
        """Create Jinja2 environment matching app configuration."""
        template_dir = Path("app/web/templates")
        return Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
    
    def test_public_templates_extend_correctly(self, jinja_env):
        """All public templates must use public/ prefix in extends."""
        template_dir = Path("app/web/templates/public")
        errors = []
        
        for template_file in template_dir.rglob("*.html"):
            rel_path = template_file.relative_to(Path("app/web/templates"))
            # Convert Windows backslashes to forward slashes for Jinja2
            template_name = str(rel_path).replace("\\", "/")
            try:
                # This will fail if extends/includes can't be resolved
                template = jinja_env.get_template(template_name)
                # Try to get the source to trigger any load errors
                jinja_env.loader.get_source(jinja_env, template_name)
            except TemplateNotFound as e:
                errors.append(f"{template_name}: Missing template '{e.name}'")
        
        if errors:
            pytest.fail("Template resolution errors:\n" + "\n".join(errors))
    
    def test_admin_templates_extend_correctly(self, jinja_env):
        """All admin templates must resolve their extends/includes."""
        template_dir = Path("app/web/templates/admin")
        errors = []
        
        for template_file in template_dir.rglob("*.html"):
            rel_path = template_file.relative_to(Path("app/web/templates"))
            # Convert Windows backslashes to forward slashes for Jinja2
            template_name = str(rel_path).replace("\\", "/")
            try:
                template = jinja_env.get_template(template_name)
                jinja_env.loader.get_source(jinja_env, template_name)
            except TemplateNotFound as e:
                errors.append(f"{template_name}: Missing template '{e.name}'")
        
        if errors:
            pytest.fail("Template resolution errors:\n" + "\n".join(errors))
    
    def test_no_orphan_extends_in_public(self):
        """Scan for extends/includes in public/ that might fail at runtime."""
        template_dir = Path("app/web/templates/public")
        errors = []
        
        import re
        for template_file in template_dir.rglob("*.html"):
            content = template_file.read_text(encoding="utf-8")
            rel_path = str(template_file.relative_to(Path("app/web/templates"))).replace("\\", "/")
            
            # Check extends without public/ prefix
            extends_matches = re.findall(r'{%\s*extends\s+"([^"]+)"', content)
            for ext_path in extends_matches:
                if not ext_path.startswith("public/"):
                    errors.append(
                        f"{rel_path}: extends '{ext_path}' should be 'public/{ext_path}'"
                    )
            
            # Check includes without public/ prefix
            include_matches = re.findall(r'{%\s*include\s+"([^"]+)"', content)
            for inc_path in include_matches:
                if not inc_path.startswith("public/"):
                    errors.append(
                        f"{rel_path}: include '{inc_path}' should be 'public/{inc_path}'"
                    )
        
        if errors:
            pytest.fail("Template path errors:\n" + "\n".join(errors))