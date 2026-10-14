from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, detail: str, status_code: int = 400, code: str = "app_error"):
        self.detail = detail
        self.status_code = status_code
        self.code = code
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "资源不存在", code: str = "not_found"):
        super().__init__(detail, status_code=404, code=code)


class PermissionDeniedError(AppError):
    def __init__(self, detail: str = "没有权限执行该操作", code: str = "permission_denied"):
        super().__init__(detail, status_code=403, code=code)


class ConflictError(AppError):
    def __init__(self, detail: str = "资源冲突", code: str = "conflict"):
        super().__init__(detail, status_code=409, code=code)


class BadRequestError(AppError):
    def __init__(self, detail: str = "请求参数错误", code: str = "bad_request"):
        super().__init__(detail, status_code=400, code=code)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "未认证或登录已过期", code: str = "unauthorized"):
        super().__init__(detail, status_code=401, code=code)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )
