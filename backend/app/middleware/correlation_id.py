"""
Correlation ID Middleware for request tracing.
Task 17: Monitoring & Logs (Wave 2)
Injects a unique UUID for each request, propagated through all logs and responses.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject correlation IDs into requests.

    - Checks for X-Correlation-ID header (for distributed tracing)
    - If not present, generates a UUID4
    - Stores in request.state.correlation_id
    - Returns correlation ID in X-Correlation-ID response header
    """

    async def dispatch(self, request: Request, call_next):
        # Check if correlation ID is already provided
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            # Generate new UUID if not provided
            correlation_id = str(uuid.uuid4())

        # Store in request state for use in handlers
        request.state.correlation_id = correlation_id

        # Process the request
        response = await call_next(request)

        # Add correlation ID to response headers for client/logging
        response.headers["X-Correlation-ID"] = correlation_id

        return response
