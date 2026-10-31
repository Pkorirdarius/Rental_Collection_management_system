import re


def normalize_phone(value: str | None) -> str | None:
    """Normalize Kenyan phone numbers to 2547XXXXXXXX / 2541XXXXXXXX."""
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif digits.startswith("254"):
        pass
    elif len(digits) == 9 and digits[0] in "71":
        digits = "254" + digits
    elif digits.startswith("+"):
        digits = digits.lstrip("+")
    return digits


def mask_phone(value: str | None) -> str:
    if not value or len(value) < 6:
        return "****"
    return f"{value[:4]}***{value[-3:]}"
