"""
Rate limiting utilities for API calls.
Implements retry logic with exponential backoff.
"""

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
import requests


# Notion rate limiting decorator (3 requests per second)
@sleep_and_retry
@limits(calls=3, period=1)
def notion_rate_limited_call(func, *args, **kwargs):
    """Enforce Notion rate limits."""
    return func(*args, **kwargs)


# Retry decorator for network errors
@retry(
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, requests.HTTPError)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
def robust_api_call(url, params=None, headers=None, method='GET', json=None, timeout=30):
    """Make API call with automatic retry on network errors."""
    if method.upper() == 'GET':
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
    elif method.upper() == 'POST':
        response = requests.post(url, params=params, headers=headers, json=json, timeout=timeout)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    response.raise_for_status()
    return response.json()
