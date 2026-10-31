from decimal import Decimal

MESSAGES = {
    "en": {
        "receipt": (
            "Hello {name}, we received KES {amount:,.2f} for {property} {unit}. "
            "Receipt {receipt}. Balance KES {balance:,.2f}. Asante."
        ),
        "pre_due": (
            "Hello {name}, your rent of KES {amount:,.2f} for {unit} is due on "
            "{due_date}. Pay via M-Pesa Paybill {shortcode}, account {bill_ref}."
        ),
        "due": (
            "Hello {name}, rent of KES {amount:,.2f} for {unit} is due today. "
            "Pay via M-Pesa Paybill {shortcode}, account {bill_ref}."
        ),
        "overdue": (
            "Hello {name}, rent for {unit} is overdue by {days} day(s). "
            "Amount due KES {amount:,.2f}. Pay via M-Pesa Paybill {shortcode}, "
            "account {bill_ref}."
        ),
        "promise": (
            "Hello {name}, we have noted your promise to pay KES {amount:,.2f} "
            "on {date}. Thank you."
        ),
    },
    "sw": {
        "receipt": (
            "Habari {name}, tumepokea KES {amount:,.2f} kwa {property} {unit}. "
            "Risiti {receipt}. Salio KES {balance:,.2f}. Asante."
        ),
        "pre_due": (
            "Habari {name}, kodi yako ya KES {amount:,.2f} kwa {unit} inatakiwa "
            "kulipwa tarehe {due_date}. Lipa kupitia M-Pesa Paybill {shortcode}, "
            "akaunti {bill_ref}."
        ),
        "due": (
            "Habari {name}, kodi ya KES {amount:,.2f} kwa {unit} inatakiwa leo. "
            "Lipa kupitia M-Pesa Paybill {shortcode}, akaunti {bill_ref}."
        ),
        "overdue": (
            "Habari {name}, kodi ya {unit} imechelewa siku {days}. Salio "
            "KES {amount:,.2f}. Lipa kupitia M-Pesa Paybill {shortcode}, akaunti {bill_ref}."
        ),
        "promise": (
            "Habari {name}, tumepokea ahadi yako ya kulipa KES {amount:,.2f} "
            "tarehe {date}. Asante."
        ),
    },
}


def money(value) -> str:
    return f"{Decimal(value):,.2f}"


def render(language: str, key: str, **kwargs) -> str:
    language = language if language in MESSAGES else "en"
    template = MESSAGES[language].get(key) or MESSAGES["en"][key]
    return template.format(**kwargs)
