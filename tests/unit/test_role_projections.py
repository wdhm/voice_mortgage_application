from app.domain.models import CapacityResult, CreditResult
from app.domain.projections import customer_projection, service_projection
from app.realtime.events import add_event, project_event


def test_customer_projection_excludes_internal_lending_and_activity(ready_case):
    ready_case.credit_result = CreditResult(
        score=781,
        risk_band="low",
        existing_debt_balance=180_000,
        monthly_payment=4_200,
        defaults="none",
    )
    ready_case.capacity_result = CapacityResult(
        property_price=7_000_000,
        deposit=1_750_000,
        requested_mortgage=5_250_000,
        ltv=0.75,
        total_debt=5_430_000,
        annual_gross_income=1_152_000,
        debt_ratio=4.71,
        base_amortization_monthly=8_750,
        additional_amortization_monthly=4_375,
        total_amortization_monthly=13_125,
        stressed_interest_rate=0.07,
        stressed_gross_interest_monthly=30_625,
        illustrative_tax_adjustment_monthly=9_188,
        stressed_net_interest_monthly=21_437,
        living_cost_monthly=12_500,
        property_running_cost_monthly=6_000,
        existing_debt_payment_monthly=4_200,
        kalp_surplus_monthly=5_138,
        outcome="preliminary_positive",
        assumptions=["demo"],
    )
    event = add_event(ready_case, "tool.completed", "Run credit check", "completed", "Mock credit bureau")

    customer = customer_projection(ready_case)
    service = service_projection(ready_case)

    assert "credit_result" not in customer
    assert "capacity_result" not in customer
    assert "events" not in customer
    assert "extracted_income" not in customer
    assert service["credit_result"]["score"] == 781
    assert project_event(event, "customer") is None
    assert project_event(event, "service") is not None