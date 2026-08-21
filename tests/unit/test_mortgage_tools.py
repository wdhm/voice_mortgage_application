from app.tools.actions import (
    calculate_borrowing_capacity,
    request_consent,
    resolve_consent,
    run_credit_check,
)


def test_canonical_mortgage_calculation(ready_case):
    consent = request_consent(ready_case, "credit_check", ready_case.customer_profile.customer_id)
    resolve_consent(ready_case, consent.consent_id, "Yes, you can run it", granted=True)
    run_credit_check(ready_case, consent.consent_id)

    result = calculate_borrowing_capacity(ready_case)

    assert result.requested_mortgage == 5_250_000
    assert result.ltv == 0.75
    assert result.total_debt == 5_430_000
    assert result.annual_gross_income == 1_152_000
    assert result.debt_ratio == 4.71
    assert result.base_amortization_monthly == 8_750
    assert result.additional_amortization_monthly == 4_375
    assert result.total_amortization_monthly == 13_125
    assert result.stressed_gross_interest_monthly == 30_625
    assert result.illustrative_tax_adjustment_monthly == 9_188
    assert result.stressed_net_interest_monthly == 21_437
    assert result.kalp_surplus_monthly == 5_138
    assert result.outcome == "preliminary_positive"
    assert result.advisor_decision_required is True