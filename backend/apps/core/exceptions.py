from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response
    data = response.data
    if isinstance(data, dict) and "detail" not in data and len(data) == 1:
        key, value = next(iter(data.items()))
        response.data = {"detail": value, "field": key}
    elif isinstance(data, list):
        response.data = {"detail": data}
    return response
