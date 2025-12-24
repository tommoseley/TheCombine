"""
Rate limiting policies.

ADR-008: Multi-Provider OAuth Authentication
Defines rate limit policies for all auth endpoints.

Two-tier rate limiting:
1. Nginx edge limits (mandatory for MVP)
2. Redis app-level limits (optional for MVP+)
"""
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class RateLimitPolicy:
    """
    Rate limit policy configuration.
    
    Attributes:
        requests: Maximum number of requests allowed
        window: Time window for the limit
        key_type: How to identify the requester
            - 'ip': Rate limit by IP address
            - 'user': Rate limit by user_id (authenticated)
            - 'ip+user': Rate limit by combination (IP + user)
            - 'token': Rate limit by token_id (PAT)
    """
    requests: int
    window: timedelta
    key_type: str  # 'ip', 'user', 'ip+user', 'token'
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.requests} requests per {self.window.total_seconds()}s"


# Rate limit policies for all auth endpoints
RATE_LIMITS = {
    # ========================================================================
    # UNAUTHENTICATED / HIGH-ABUSE ENDPOINTS
    # ========================================================================
    
    'auth_login_redirect': RateLimitPolicy(
        requests=30,
        window=timedelta(minutes=1),
        key_type='ip'
    ),
    
    'auth_callback': RateLimitPolicy(
        requests=30,
        window=timedelta(minutes=1),
        key_type='ip'
    ),
    
    'auth_link_callback': RateLimitPolicy(
        requests=30,
        window=timedelta(minutes=1),
        key_type='ip'
    ),
    
    # ========================================================================
    # SECURITY-SENSITIVE ENDPOINTS
    # ========================================================================
    
    'auth_link_initiate': RateLimitPolicy(
        requests=10,
        window=timedelta(minutes=1),
        key_type='ip+user'  # Both IP and user must match
    ),
    
    'pat_auth_failure': RateLimitPolicy(
        requests=20,
        window=timedelta(minutes=1),
        key_type='ip'  # Prevents brute force by IP
    ),
    
    'pat_auth_failure_per_token': RateLimitPolicy(
        requests=5,
        window=timedelta(minutes=1),
        key_type='token'  # Prevents enumeration of specific token
    ),
    
    # ========================================================================
    # AUTHENTICATED BUT RISKY ENDPOINTS
    # ========================================================================
    
    'pat_creation': RateLimitPolicy(
        requests=5,
        window=timedelta(hours=1),
        key_type='user'  # Per user, not per IP
    ),
    
    'pat_revocation': RateLimitPolicy(
        requests=20,
        window=timedelta(hours=1),
        key_type='user'
    ),
    
    # ========================================================================
    # GLOBAL BURST PROTECTION
    # ========================================================================
    
    'global_unauth': RateLimitPolicy(
        requests=300,
        window=timedelta(minutes=1),
        key_type='ip'  # Catch-all for any endpoint
    )
}


def get_policy(policy_name: str) -> RateLimitPolicy:
    """
    Get rate limit policy by name.
    
    Args:
        policy_name: Name of the policy
        
    Returns:
        RateLimitPolicy instance
        
    Raises:
        KeyError: If policy not found
    """
    return RATE_LIMITS[policy_name]