"""Authentication module for The Combine."""

from .models import (
    User,
    Session,
    UserSession,
    AuthProvider,
    AuthEventType,
    AuthContext,
    PersonalAccessToken,
    OAuthTokens,
    OAuthUserInfo,
)
from .repositories import (
    UserRepository,
    SessionRepository,
    InMemoryUserRepository,
    InMemorySessionRepository,
    UserNotFoundError,
    UserAlreadyExistsError,
    SessionNotFoundError,
)
from .services import (
    SessionService,
    UserService,
    generate_user_id,
    generate_session_id,
    generate_session_token,
    hash_token,
)
from .pat_service import (
    PATService,
    InMemoryPATRepository,
    generate_pat_token,
    hash_pat,
    get_token_display,
    get_key_id,
)
from .permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_role_permissions,
    get_user_permissions,
    has_permission,
    has_any_permission,
    has_all_permissions,
)
from .middleware import (
    AuthMiddleware,
    require_auth,
    require_permission,
    require_any_permission,
)

__all__ = [
    # Models
    "User",
    "Session",
    "UserSession",
    "AuthProvider",
    "AuthEventType",
    "AuthContext",
    "PersonalAccessToken",
    "OAuthTokens",
    "OAuthUserInfo",
    # Repositories
    "UserRepository",
    "SessionRepository",
    "InMemoryUserRepository",
    "InMemorySessionRepository",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "SessionNotFoundError",
    # Session Services
    "SessionService",
    "UserService",
    "generate_user_id",
    "generate_session_id",
    "generate_session_token",
    "hash_token",
    # PAT Services
    "PATService",
    "InMemoryPATRepository",
    "generate_pat_token",
    "hash_pat",
    "get_token_display",
    "get_key_id",
    # Permissions
    "Permission",
    "ROLE_PERMISSIONS",
    "get_role_permissions",
    "get_user_permissions",
    "has_permission",
    "has_any_permission",
    "has_all_permissions",
    # Middleware
    "AuthMiddleware",
    "require_auth",
    "require_permission",
    "require_any_permission",
]
