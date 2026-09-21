from app.triage.mock import MockTriageProvider
from app.triage.port import TicketContent

provider = MockTriageProvider()


def evaluate(title: str, description: str):
    return provider.evaluate(TicketContent(title=title, description=description))


def test_outage_is_technical_and_maximally_urgent():
    result = evaluate("Checkout down", "Our checkout page throws a 500 error, we are losing sales.")
    assert result.department.choice == "technical"
    assert result.urgency.score == 4
    assert result.refund.probability < 0.5


def test_duplicate_charge_is_billing_with_refund():
    result = evaluate("Charged twice", "I was charged twice, I'd like a refund for the duplicate.")
    assert result.department.choice == "billing"
    assert result.refund.probability >= 0.5


def test_explicitly_not_a_refund_stays_below_threshold():
    result = evaluate("Pricing", "Why did my plan renew higher? I want clarity, not a refund.")
    assert result.department.choice == "billing"
    assert result.refund.probability < 0.5


def test_no_rush_question_is_general_and_low_urgency():
    result = evaluate("Display name", "Is there a way to change my display name? No rush.")
    assert result.department.choice == "general"
    assert result.urgency.score == 0


def test_probabilities_sum_to_one_and_confidence_present():
    result = evaluate("Anything", "Some text")
    assert abs(sum(result.department.probabilities.values()) - 1) < 1e-6
    assert abs(sum(result.urgency.probabilities.values()) - 1) < 1e-6
    assert set(result.confidence) == {"department", "urgency", "refund_requested"}


def test_is_deterministic():
    a = evaluate("A", "The export crashes every time")
    b = evaluate("A", "The export crashes every time")
    assert a == b


def test_provider_name():
    assert provider.name == "mock"
