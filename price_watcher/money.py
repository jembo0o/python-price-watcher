from decimal import Decimal, InvalidOperation


def parse_price_to_cents(raw_price: str) -> int:
    try:
        value = Decimal(raw_price)
    except InvalidOperation as exc:
        raise ValueError("Target price must be a decimal number") from exc

    if not value.is_finite():
        raise ValueError("Target price must be a finite decimal number")

    if value < 0:
        raise ValueError("Target price must be greater than or equal to 0")

    cents = value * Decimal("100")
    if cents != cents.to_integral_value():
        raise ValueError("Target price must have no more than two decimal places")

    return int(cents)
