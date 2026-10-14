"""项目启动入口

直接使用当前 Python 解释器启动服务，不再依赖 conda 环境。

推荐用项目虚拟环境运行（PowerShell 进入项目目录后会自动激活 .venv）：

    python run.py

也可以显式指定解释器：

    .venv\\Scripts\\python.exe run.py

可用环境变量：HOST、PORT。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

HOST_DEFAULT = "0.0.0.0"
PORT_DEFAULT = 8000


def _bootstrap_path() -> None:
    """确保项目根目录可导入（uvicorn reload 的子进程同样需要）。"""

    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _print_runtime_info() -> None:
    print(f"当前 Python：{sys.executable}")

    if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        print("提示：当前解释器不是项目虚拟环境，若缺少依赖请改用：")
        print(f"      {VENV_PYTHON} run.py")


def _exit_missing_dependency(exc: ModuleNotFoundError) -> None:
    print(f"缺少依赖：{exc.name}")
    print("请先安装依赖：")

    if VENV_PYTHON.exists():
        print(f"      {VENV_PYTHON} -m pip install -r requirements.txt")
        print(f"      {VENV_PYTHON} run.py")
    else:
        print("      python -m pip install -r requirements.txt")

    sys.exit(1)


def main() -> None:
    os.chdir(PROJECT_ROOT)
    _bootstrap_path()

    try:
        import uvicorn

        from app.core.config import settings
    except ModuleNotFoundError as exc:
        _exit_missing_dependency(exc)
        return

    host = os.getenv("HOST", HOST_DEFAULT)
    port = int(os.getenv("PORT", str(PORT_DEFAULT)))
    reload = settings.DEBUG

    _print_runtime_info()
    print(f"启动 {settings.APP_NAME}...")
    print(f"地址：http://127.0.0.1:{port}")
    print(f"文档：http://127.0.0.1:{port}/docs")
    print(f"reload={reload}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="debug" if settings.DEBUG else "info",
    )


if __name__ == "__main__":
    main()
