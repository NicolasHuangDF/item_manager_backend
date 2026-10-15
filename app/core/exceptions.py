from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

#: MySQL 中通过 SIGNAL SQLSTATE '45000' 抛出的错误码。
#: 建表脚本用它实现 units 的公共单位重名检查触发器。
MYSQL_SIGNAL_ERRNO = 1644


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

    @app.exception_handler(OperationalError)
    async def db_operational_error_handler(
        _: Request, exc: OperationalError
    ) -> JSONResponse:
        """把数据库触发器抛出的业务校验错误转成 409，而不是 500。

        units 表用 BEFORE INSERT/UPDATE 触发器实现公共单位重名规则，
        触发时错误码为 1644（SIGNAL SQLSTATE '45000'），消息是中文提示。
        并发写入时应用层的预检查可能失效，这里兜底。
        """
        orig = getattr(exc, "orig", None)
        args = getattr(orig, "args", ()) or ()
        if args and args[0] == MYSQL_SIGNAL_ERRNO:
            detail = args[1] if len(args) > 1 else "数据库校验失败"
            return JSONResponse(
                status_code=409,
                content={"detail": detail, "code": "conflict"},
            )
        raise exc
