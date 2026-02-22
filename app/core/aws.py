"""AWS service utilities for The Combine.

Provides reusable access to AWS services (Secrets Manager, S3, etc.)
with consistent error handling and region configuration.
"""

import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_REGION = "us-east-1"


def get_secret(secret_name: str, region: str = DEFAULT_REGION) -> dict:
    """Retrieve and parse a JSON secret from AWS Secrets Manager.

    Args:
        secret_name: The secret ID (e.g. "the-combine/db-dev").
        region: AWS region. Defaults to us-east-1.

    Returns:
        Parsed JSON secret as a dict.

    Raises:
        RuntimeError: If boto3 is not installed or AWS call fails.
    """
    try:
        import boto3
    except ImportError:
        raise RuntimeError(
            "boto3 is required for AWS Secrets Manager access. "
            "Install it: pip install boto3"
        )

    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception as e:
        raise RuntimeError(
            f"Failed to retrieve secret '{secret_name}' from Secrets Manager: {e}\n"
            f"Check that:\n"
            f"  1. AWS CLI is configured (aws sts get-caller-identity)\n"
            f"  2. You have secretsmanager:GetSecretValue permission\n"
            f"  3. Secret '{secret_name}' exists in region {region}"
        ) from e
