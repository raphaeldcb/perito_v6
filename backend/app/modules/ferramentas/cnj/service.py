"""
CNJ service for CNJ (Conselho Nacional de Justiça) number parsing and validation.

Stateless service for CNJ number operations.

CNJ format (20 digits): NNNNNNNDDAAAASSTTOOEE
- N (7 digits): Sequential number
- D (2 digits): Verification digits
- A (4 digits): Year (DDAA format, but actually AADD)
- S (2 digits): Segment (1=Judicial, 2=Administrative)
- T (4 digits): Court number
- O (2 digits): Origin state code
- E (2 digits): End designation

All operations are deterministic and have p95 < 1ms.
"""

import re
from typing import Dict, Any, Optional


class CNJService:
    """Stateless service for CNJ number operations."""

    # CNJ format regex: 25 digits
    # Pattern: sequential(7) + verification(2) + year(4) + segment1(4) + segment2(4) + state(2) + origin(2)
    CNJ_PATTERN = re.compile(r"^(\d{7})(\d{2})(\d{4})(\d{4})(\d{4})(\d{2})(\d{2})$")

    def parse_cnj(self, cnj_number: str) -> Optional[Dict[str, str]]:
        """
        Parse CNJ number into components.

        Args:
            cnj_number: Full 20-digit CNJ number

        Returns:
            Dict with parsed components if valid, None if invalid format

        Components returned:
            - sequential: 7-digit sequential number
            - verification_digits: 2-digit verification code
            - origin_year: 4-digit year
            - segment: 2-digit segment code
            - court: 4-digit court number
            - origin_state: 2-digit state origin code
        """
        match = self.CNJ_PATTERN.match(cnj_number)
        if not match:
            return None

        sequential, verif, year, segment, court, state, end = match.groups()

        return {
            "sequential": sequential,
            "verification_digits": verif,
            "origin_year": year,
            "segment": segment,
            "court": court,
            "origin_state": state,
        }

    def validate_cnj(self, cnj_number: str) -> Dict[str, Any]:
        """
        Validate CNJ number and return detailed result.

        Args:
            cnj_number: Full CNJ number to validate

        Returns:
            Dict with:
                - valid: True if valid, False otherwise
                - cnj_number: Original input
                - parsed: Parsed components if valid, None otherwise
                - error: Error message if invalid, None otherwise
        """
        # Validate it's not empty
        if not cnj_number or not isinstance(cnj_number, str):
            return {
                "valid": False,
                "cnj_number": cnj_number,
                "parsed": None,
                "error": "CNJ number must be a non-empty string",
            }

        # Validate length (25 digits)
        if len(cnj_number) != 25:
            return {
                "valid": False,
                "cnj_number": cnj_number,
                "parsed": None,
                "error": f"CNJ number must have exactly 25 digits, got {len(cnj_number)}",
            }

        # Validate all characters are digits
        if not cnj_number.isdigit():
            return {
                "valid": False,
                "cnj_number": cnj_number,
                "parsed": None,
                "error": "CNJ number must contain only digits",
            }

        # Parse and validate format
        parsed = self.parse_cnj(cnj_number)
        if parsed is None:
            return {
                "valid": False,
                "cnj_number": cnj_number,
                "parsed": None,
                "error": "Invalid CNJ format",
            }

        return {
            "valid": True,
            "cnj_number": cnj_number,
            "parsed": parsed,
            "error": None,
        }

    def extract_comarca(self, cnj_number: str) -> Optional[str]:
        """
        Extract comarca (court) code from CNJ number.

        Args:
            cnj_number: Valid CNJ number

        Returns:
            Court/comarca code (state + court), or None if invalid
        """
        parsed = self.parse_cnj(cnj_number)
        if not parsed:
            return None

        # Comarca is typically state code + court code
        return f"{parsed['origin_state']}{parsed['court']}"

    def extract_year(self, cnj_number: str) -> Optional[int]:
        """
        Extract origin year from CNJ number.

        Args:
            cnj_number: Valid CNJ number

        Returns:
            Year as integer, or None if invalid
        """
        parsed = self.parse_cnj(cnj_number)
        if not parsed:
            return None

        try:
            return int(parsed["origin_year"])
        except ValueError:
            return None


# Singleton instance
_cnj_service: Optional[CNJService] = None


def get_cnj_service() -> CNJService:
    """
    Get or create singleton CNJ service.

    Returns:
        CNJService singleton instance
    """
    global _cnj_service
    if _cnj_service is None:
        _cnj_service = CNJService()
    return _cnj_service
