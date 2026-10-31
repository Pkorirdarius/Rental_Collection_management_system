import base64
import io
import json
import secrets

import pyotp
import qrcode

BACKUP_CODE_COUNT = 10


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str = "Rent Manager") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def qr_data_uri(uri: str) -> str:
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(str(code).strip().replace(" ", ""), valid_window=1)


def generate_backup_codes() -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(BACKUP_CODE_COUNT)]


def dump_backup_codes(codes: list[str]) -> str:
    return json.dumps(codes)


def load_backup_codes(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        return list(json.loads(raw))
    except (ValueError, TypeError):
        return []


def consume_backup_code(user, code: str) -> bool:
    codes = load_backup_codes(user.backup_codes)
    candidate = str(code).strip().upper()
    if candidate not in codes:
        return False
    codes.remove(candidate)
    user.backup_codes = dump_backup_codes(codes)
    user.save(update_fields=["backup_codes", "updated_at"])
    return True
