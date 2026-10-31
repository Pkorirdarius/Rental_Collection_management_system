import base64
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache


class DarajaError(Exception):
    pass


class DarajaClient:
    """Thin Safaricom Daraja API client. All secrets come from settings/env."""

    def __init__(self, config=None):
        self.config = config or settings.MPESA

    @property
    def base_url(self) -> str:
        if self.config.get("ENV") == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    def _require(self):
        if not self.config.get("ENABLED"):
            raise DarajaError("M-Pesa integration is disabled (set MPESA_ENABLED=true).")
        for key in ("CONSUMER_KEY", "CONSUMER_SECRET", "SHORTCODE", "PASSKEY"):
            if not self.config.get(key):
                raise DarajaError(f"M-Pesa setting {key} is missing.")

    def _cache_key(self) -> str:
        return f"daraja:token:{self.config.get('ENV')}:{self.config.get('CONSUMER_KEY')}"

    def get_access_token(self, force: bool = False) -> str:
        self._require()
        key = self._cache_key()
        if not force:
            cached = cache.get(key)
            if cached:
                return cached
        response = requests.get(
            f"{self.base_url}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=(self.config["CONSUMER_KEY"], self.config["CONSUMER_SECRET"]),
            timeout=20,
        )
        if response.status_code != 200:
            raise DarajaError(f"Daraja auth failed ({response.status_code}): {response.text[:300]}")
        token = response.json().get("access_token")
        if not token:
            raise DarajaError("Daraja auth response did not include an access token.")
        cache.set(key, token, timeout=3000)
        return token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.get_access_token()}"}

    @staticmethod
    def timestamp() -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def stk_password(self, timestamp: str | None = None) -> str:
        timestamp = timestamp or self.timestamp()
        raw = f"{self.config['SHORTCODE']}{self.config['PASSKEY']}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    def _post(self, path: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.base_url}{path}", json=payload, headers=self._headers(), timeout=30
        )
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}
        if response.status_code >= 400:
            raise DarajaError(
                f"Daraja request failed ({response.status_code}): {data}"
            )
        return data

    def stk_push(
        self,
        *,
        phone: str,
        amount: int,
        account_reference: str,
        description: str,
        callback_url: str,
    ) -> dict:
        self._require()
        timestamp = self.timestamp()
        payload = {
            "BusinessShortCode": self.config["SHORTCODE"],
            "Password": self.stk_password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": self.config.get("STK_TRANSACTION_TYPE", "CustomerPayBillOnline"),
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": self.config["SHORTCODE"],
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": description[:100],
        }
        return self._post("/mpesa/stkpush/v1/processrequest", payload)

    def stk_query(self, checkout_request_id: str) -> dict:
        self._require()
        timestamp = self.timestamp()
        payload = {
            "BusinessShortCode": self.config["SHORTCODE"],
            "Password": self.stk_password(timestamp),
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }
        return self._post("/mpesa/stkpushquery/v1/query", payload)

    def transaction_status(self, transaction_id: str, *, result_url: str, timeout_url: str) -> dict:
        self._require()
        payload = {
            "Initiator": self.config.get("INITIATOR_NAME", ""),
            "SecurityCredential": self.config.get("SECURITY_CREDENTIAL", ""),
            "CommandID": "TransactionStatusQuery",
            "TransactionID": transaction_id,
            "PartyA": self.config["SHORTCODE"],
            "IdentifierType": "4",
            "ResultURL": result_url,
            "QueueTimeOutURL": timeout_url,
            "Remarks": "Reconciliation",
            "Occasion": "Rent reconciliation",
        }
        return self._post("/mpesa/transactionstatus/v1/query", payload)

    def register_c2b_urls(self, *, validation_url: str, confirmation_url: str) -> dict:
        self._require()
        payload = {
            "ShortCode": self.config["SHORTCODE"],
            "ResponseType": "Completed",
            "ConfirmationURL": confirmation_url,
            "ValidationURL": validation_url,
        }
        return self._post("/mpesa/c2b/v1/registerurl", payload)

    def simulate_c2b(
        self,
        *,
        phone: str,
        amount: int,
        bill_ref: str,
        command_id: str = "CustomerPayBillOnline",
    ) -> dict:
        self._require()
        payload = {
            "ShortCode": self.config["SHORTCODE"],
            "CommandID": command_id,
            "Amount": int(amount),
            "Msisdn": phone,
            "BillRefNumber": bill_ref,
        }
        return self._post("/mpesa/c2b/v1/simulate", payload)
