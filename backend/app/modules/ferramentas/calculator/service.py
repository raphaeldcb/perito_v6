"""
Calculator service for financial operations.

Stateless service providing:
- deslocamento calculation (travel expenses: distance × rate + toll)
- juros calculation (interest: principal × taxa × dias/30)

All calculations are deterministic and have p95 < 1ms.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional


class CalculatorService:
    """Stateless calculator service for financial operations."""

    def calculate_deslocamento(
        self,
        distance_km: float,
        toll_cost: float = 0.0,
        rate_per_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate deslocamento (travel expense).

        Formula:
            travel_cost = distance_km × rate_per_km
            total_cost = travel_cost + toll_cost

        Args:
            distance_km: Distance traveled in kilometers (must be > 0)
            toll_cost: Toll cost in R$ (default: 0)
            rate_per_km: Rate per kilometer in R$ (default: 2.50)

        Returns:
            Dict with:
                - distance_km: Original distance
                - toll_cost: Original toll cost
                - rate_per_km: Rate used
                - travel_cost: Calculated travel cost
                - total_cost: Total (travel + toll)

        Raises:
            ValueError: If distance_km <= 0
        """
        if rate_per_km is None:
            rate_per_km = 2.50

        if distance_km <= 0:
            raise ValueError("distance_km must be greater than 0")

        travel_cost = distance_km * rate_per_km
        total_cost = travel_cost + toll_cost

        return {
            "distance_km": distance_km,
            "toll_cost": toll_cost,
            "rate_per_km": rate_per_km,
            "travel_cost": travel_cost,
            "total_cost": total_cost,
        }

    def calculate_juros(
        self,
        principal: Decimal,
        rate_per_month: float,
        days: int,
    ) -> Dict[str, Any]:
        """
        Calculate juros (interest).

        Formula:
            interest = principal × rate_per_month × (days / 30)
            total = principal + interest

        Uses simple interest calculation (not compound).
        Months are normalized to 30 days.

        Args:
            principal: Principal amount in R$ (must be > 0)
            rate_per_month: Monthly interest rate as decimal (e.g., 0.01 = 1%)
            days: Number of days (must be > 0)

        Returns:
            Dict with:
                - principal: Original principal
                - rate_per_month: Monthly interest rate
                - days: Number of days
                - interest_amount: Calculated interest
                - total_amount: Total (principal + interest)

        Raises:
            ValueError: If principal <= 0 or days <= 0
        """
        if principal <= 0:
            raise ValueError("principal must be greater than 0")
        if days <= 0:
            raise ValueError("days must be greater than 0")

        # Convert to Decimal for precise calculation
        principal_decimal = Decimal(str(principal))
        rate_decimal = Decimal(str(rate_per_month))
        days_decimal = Decimal(str(days))

        # Calculate interest: principal × rate × (days/30)
        interest = principal_decimal * rate_decimal * (days_decimal / Decimal("30"))

        # Round to 2 decimal places
        interest = interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total = principal_decimal + interest

        return {
            "principal": principal_decimal,
            "rate_per_month": rate_per_month,
            "days": days,
            "interest_amount": interest,
            "total_amount": total,
        }


# Singleton instance
_calculator_service: Optional[CalculatorService] = None


def get_calculator_service() -> CalculatorService:
    """
    Get or create singleton calculator service.

    Returns:
        CalculatorService singleton instance
    """
    global _calculator_service
    if _calculator_service is None:
        _calculator_service = CalculatorService()
    return _calculator_service
