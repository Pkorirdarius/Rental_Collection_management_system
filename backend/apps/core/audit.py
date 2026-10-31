from contextvars import ContextVar

_current_request: ContextVar = ContextVar("audit_current_request", default=None)


def get_current_request():
    return _current_request.get()


def set_current_request(request):
    return _current_request.set(request)


def reset_current_request(token) -> None:
    _current_request.reset(token)


def audit(action, **kwargs):
    from apps.core.models import AuditLog

    return AuditLog.record(action, **kwargs)
