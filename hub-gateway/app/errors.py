from fastapi.responses import JSONResponse


def error_response(
    status_code: int,
    error_code: str,
    error_detail: str = "",
) -> JSONResponse:
    body = {"success": False, "error_code": error_code}
    if error_detail:
        body["error_detail"] = error_detail
    return JSONResponse(status_code=status_code, content=body)
