"""Tests for permissions and role-based access control."""


from app.auth.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_role_permissions,
    get_user_permissions,
    has_permission,
    has_any_permission,
    has_all_permissions,
)


class TestPermissionEnum:
    """Tests for Permission enum."""
    
    def test_permission_string_value(self):
        """Permissions have correct string values."""
        assert str(Permission.WORKFLOW_READ) == "workflow:read"
        assert str(Permission.ADMIN) == "admin"
    
    def test_all_permissions_have_values(self):
        """All permissions have string values."""
        for perm in Permission:
            assert isinstance(perm.value, str)
            assert len(perm.value) > 0


class TestRoleDefinitions:
    """Tests for role permission definitions."""
    
    def test_viewer_role_exists(self):
        """Viewer role is defined."""
        assert "viewer" in ROLE_PERMISSIONS
    
    def test_operator_role_exists(self):
        """Operator role is defined."""
        assert "operator" in ROLE_PERMISSIONS
    
    def test_admin_role_exists(self):
        """Admin role is defined."""
        assert "admin" in ROLE_PERMISSIONS
    
    def test_viewer_has_read_only(self):
        """Viewer can only read."""
        perms = ROLE_PERMISSIONS["viewer"]
        assert Permission.WORKFLOW_READ in perms
        assert Permission.EXECUTION_READ in perms
        assert Permission.WORKFLOW_EXECUTE not in perms
        assert Permission.EXECUTION_WRITE not in perms
    
    def test_operator_can_execute(self):
        """Operator can execute workflows."""
        perms = ROLE_PERMISSIONS["operator"]
        assert Permission.WORKFLOW_EXECUTE in perms
        assert Permission.EXECUTION_WRITE in perms
    
    def test_admin_has_all_permissions(self):
        """Admin has comprehensive permissions."""
        perms = ROLE_PERMISSIONS["admin"]
        assert Permission.ADMIN in perms
        assert Permission.WORKFLOW_READ in perms
        assert Permission.EXECUTION_CANCEL in perms


class TestGetPermissions:
    """Tests for permission lookup functions."""
    
    def test_get_role_permissions_valid(self):
        """Can get permissions for valid role."""
        perms = get_role_permissions("viewer")
        assert Permission.WORKFLOW_READ in perms
    
    def test_get_role_permissions_invalid(self):
        """Unknown role returns empty set."""
        perms = get_role_permissions("unknown_role")
        assert perms == set()
    
    def test_get_user_permissions_single_role(self):
        """User with single role gets correct permissions."""
        perms = get_user_permissions(["viewer"])
        assert Permission.WORKFLOW_READ in perms
        assert Permission.WORKFLOW_EXECUTE not in perms
    
    def test_get_user_permissions_multiple_roles(self):
        """User with multiple roles gets combined permissions."""
        perms = get_user_permissions(["viewer", "operator"])
        assert Permission.WORKFLOW_READ in perms
        assert Permission.WORKFLOW_EXECUTE in perms
    
    def test_get_user_permissions_empty_roles(self):
        """User with no roles gets no permissions."""
        perms = get_user_permissions([])
        assert perms == set()


class TestHasPermission:
    """Tests for permission checking functions."""
    
    def test_has_permission_granted(self):
        """Returns True when permission is granted."""
        assert has_permission(["operator"], Permission.WORKFLOW_EXECUTE) is True
    
    def test_has_permission_denied(self):
        """Returns False when permission is not granted."""
        assert has_permission(["viewer"], Permission.WORKFLOW_EXECUTE) is False
    
    def test_admin_has_all_permissions(self):
        """Admin role grants all permissions."""
        assert has_permission(["admin"], Permission.WORKFLOW_READ) is True
        assert has_permission(["admin"], Permission.EXECUTION_CANCEL) is True
        assert has_permission(["admin"], Permission.USER_MANAGE) is True
    
    def test_has_any_permission_one_matches(self):
        """Returns True if any permission matches."""
        result = has_any_permission(
            ["viewer"],
            [Permission.WORKFLOW_READ, Permission.WORKFLOW_EXECUTE]
        )
        assert result is True
    
    def test_has_any_permission_none_match(self):
        """Returns False if no permissions match."""
        result = has_any_permission(
            ["viewer"],
            [Permission.WORKFLOW_EXECUTE, Permission.EXECUTION_CANCEL]
        )
        assert result is False
    
    def test_has_all_permissions_all_match(self):
        """Returns True if all permissions match."""
        result = has_all_permissions(
            ["operator"],
            [Permission.WORKFLOW_READ, Permission.WORKFLOW_EXECUTE]
        )
        assert result is True
    
    def test_has_all_permissions_partial_match(self):
        """Returns False if not all permissions match."""
        result = has_all_permissions(
            ["viewer"],
            [Permission.WORKFLOW_READ, Permission.WORKFLOW_EXECUTE]
        )
        assert result is False
