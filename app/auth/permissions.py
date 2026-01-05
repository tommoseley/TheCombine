"""Permission and role-based access control."""

from enum import Enum
from typing import List, Set


class Permission(str, Enum):
    """System permissions."""
    # Workflow permissions
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_EXECUTE = "workflow:execute"
    
    # Execution permissions
    EXECUTION_READ = "execution:read"
    EXECUTION_WRITE = "execution:write"
    EXECUTION_CANCEL = "execution:cancel"
    
    # Admin permissions
    ADMIN = "admin"
    USER_MANAGE = "user:manage"
    
    def __str__(self) -> str:
        return self.value


# Role definitions with their granted permissions
ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    "viewer": {
        Permission.WORKFLOW_READ,
        Permission.EXECUTION_READ,
    },
    "operator": {
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.EXECUTION_READ,
        Permission.EXECUTION_WRITE,
    },
    "admin": {
        Permission.ADMIN,
        Permission.USER_MANAGE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_EXECUTE,
        Permission.EXECUTION_READ,
        Permission.EXECUTION_WRITE,
        Permission.EXECUTION_CANCEL,
    },
}


def get_role_permissions(role: str) -> Set[Permission]:
    """Get permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())


def get_user_permissions(roles: List[str]) -> Set[Permission]:
    """Get all permissions for a user based on their roles."""
    permissions: Set[Permission] = set()
    for role in roles:
        permissions.update(get_role_permissions(role))
    return permissions


def has_permission(roles: List[str], permission: Permission) -> bool:
    """Check if roles grant a specific permission."""
    # Admin has all permissions
    if "admin" in roles:
        return True
    
    user_permissions = get_user_permissions(roles)
    return permission in user_permissions


def has_any_permission(roles: List[str], permissions: List[Permission]) -> bool:
    """Check if roles grant any of the specified permissions."""
    return any(has_permission(roles, p) for p in permissions)


def has_all_permissions(roles: List[str], permissions: List[Permission]) -> bool:
    """Check if roles grant all of the specified permissions."""
    return all(has_permission(roles, p) for p in permissions)
