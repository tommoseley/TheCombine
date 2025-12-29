"""
Rate limiting middleware and utilities.

ADR-008: Multi-Provider OAuth Authentication
Provides client IP detection and rate limiting enforcement.

CRITICAL: get_client_ip() respects TRUST_PROXY setting.
Only trust X-Forwarded-For when behind known reverse proxy.
"""
from fastapi import Request
import os
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Get real client IP address, handling proxies correctly.
    
    SECURITY CRITICAL:
    - Only trusts X-Forwarded-For if TRUST_PROXY=true
    - Otherwise attackers can spoof IPs to bypass rate limits
    - Behind Nginx/K8s: TRUST_PROXY must be true
    - Direct internet: TRUST_PROXY must be false
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Client IP address
        
    Examples:
        >>> # Behind Nginx with TRUST_PROXY=true
        >>> os.environ['TRUST_PROXY'] = 'true'
        >>> request.headers = {'X-Forwarded-For': '1.2.3.4, 10.0.0.1'}
        >>> get_client_ip(request)
        '1.2.3.4'
        
        >>> # Direct exposure with TRUST_PROXY=false
        >>> os.environ['TRUST_PROXY'] = 'false'
        >>> request.headers = {'X-Forwarded-For': '1.2.3.4'}  # Attacker-controlled
        >>> get_client_ip(request)
        '5.6.7.8'  # Real socket IP, not spoofed header
    """
    trust_proxy = os.getenv('TRUST_PROXY', 'false').lower() == 'true'
    
    if trust_proxy:
        # Parse X-Forwarded-For (leftmost IP is original client)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
            logger.debug(f"Using X-Forwarded-For: {client_ip}")
            return client_ip
        
        # Fallback to X-Real-IP
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            logger.debug(f"Using X-Real-IP: {real_ip}")
            return real_ip
    
    # Direct connection or untrusted proxy
    client_ip = request.client.host
    logger.debug(f"Using request.client.host: {client_ip}")
    return client_ip


# ============================================================================
# RateLimiter class will be implemented in Stage 8
# ============================================================================
# For Stage 1, we only need get_client_ip() defined.
# The full RateLimiter implementation with Redis sliding window
# will be added in Stage 8 (Phase 4 of implementation plan).