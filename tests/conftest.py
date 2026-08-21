from datetime import date

import pytest

from app.domain.fixture import canonical_case
from app.domain.models import AcceptedIncome, IdentityStatus


@pytest.fixture
def ready_case():
    case = canonical_case()
    case.identity_status = IdentityStatus.IDENTIFIED
    case.accepted_income = AcceptedIncome(
        employer_name="Northstar AB",
        gross_salary_monthly=96_000,
        net_salary_monthly=62_400,
        employment_type="permanent_full_time",
        pay_date=date(2026, 8, 25),
        provenance="automatically-verified",
    )
    return case