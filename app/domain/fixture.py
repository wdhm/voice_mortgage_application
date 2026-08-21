from app.domain.models import Card, CustomerProfile, DemoCase


def canonical_case() -> DemoCase:
    return DemoCase(
        case_id="case-emma",
        session_id="session-demo",
        customer_profile=CustomerProfile(
            customer_id="customer-emma",
            display_name="Emma Lindberg",
            city="Täby",
            relationship_since=2018,
            contact_summary="Preferred contact: secure Bank Alfa message",
            car_loan_balance=180_000,
            car_loan_payment=4_200,
        ),
        cards=[
            Card(
                card_id="card-mastercard-4471",
                card_type="Bank Alfa Mastercard",
                last_four="4471",
            )
        ],
    )
