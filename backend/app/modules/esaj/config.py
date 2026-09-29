"""
ESAJ module configuration with sandbox/production toggle.

Controls API endpoints, timeouts, and behavior based on environment variables.
"""

import os
from dataclasses import dataclass


@dataclass
class EsajConfig:
    """
    ESAJ configuration management.

    Supports sandbox and production modes with environment-based configuration.
    """

    sandbox_mode: bool
    api_url: str
    timeout_seconds: int

    def __init__(self):
        """Initialize ESAJ configuration from environment variables."""
        # Determine sandbox mode
        sandbox_env = os.getenv("ESAJ_SANDBOX", "false").lower()
        self.sandbox_mode = sandbox_env in ("true", "1", "yes")

        # Set API URL based on sandbox mode
        if self.sandbox_mode:
            self.api_url = os.getenv(
                "ESAJ_SANDBOX_URL",
                "https://sandbox.esaj.tjsp.jus.br/webservices",
            )
        else:
            self.api_url = os.getenv(
                "ESAJ_API_URL",
                "https://webservices.tjsp.jus.br/",
            )

        # Set timeout
        try:
            self.timeout_seconds = int(os.getenv("ESAJ_TIMEOUT", "10"))
        except ValueError:
            self.timeout_seconds = 10

    def get_url(self, endpoint: str) -> str:
        """
        Get full API URL for an endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Full URL for the endpoint
        """
        return f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
