"""Reusable budget calculation and validation tools."""

from dataclasses import dataclass
from collections.abc import Sequence

from app.services.event_planner import BudgetLine, allocate_budget


@dataclass(frozen=True)
class BudgetValidation:
    is_valid: bool
    budget: int
    allocated_total: int
    remaining: int
    message: str


def calculate_event_budget(total_budget: int) -> tuple[BudgetLine, ...]:
    """Calculate a category allocation that sums exactly to the given budget."""
    return allocate_budget(total_budget)


def validate_event_budget(total_budget: int, allocations: Sequence[BudgetLine]) -> BudgetValidation:
    """Report whether nonnegative category allocations fit the total budget."""
    allocated_total = sum(line.amount for line in allocations)
    if total_budget <= 0:
        return BudgetValidation(False, total_budget, allocated_total, total_budget - allocated_total, "Budget must be greater than zero.")
    if any(line.amount < 0 for line in allocations):
        return BudgetValidation(False, total_budget, allocated_total, total_budget - allocated_total, "Category allocations cannot be negative.")
    remaining = total_budget - allocated_total
    if remaining < 0:
        message = f"Allocations exceed the budget by ₹{abs(remaining):,}."
    elif remaining > 0:
        message = f"₹{remaining:,} remains unallocated."
    else:
        message = "Allocations match the total budget."
    return BudgetValidation(remaining == 0, total_budget, allocated_total, remaining, message)
