"""项目启动入口：自动确保运行在 conda 的 item_manager 环境中。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ENV_NAME = "item_manager"
RELAUNCH_FLAG = "ITEM_MANAGE_RELAUNCHED"


def _is_target_env() -> bool:
    """判断当前 Python 是否运行在 item_manager conda 环境中。"""

    default_env = (os.environ.get("CONDA_DEFAULT_ENV") or "").strip()
    prefix = (os.environ.get("CONDA_PREFIX") or "").strip()

    if default_env.lower() == ENV_NAME.lower():
        return True

    if prefix and Path(prefix).name.lower() == ENV_NAME.lower():
        return True

    if Path(sys.prefix).name.lower() == ENV_NAME.lower():
        return True

    return False


def _find_conda() -> str | None:
    """查找 conda 可执行文件。"""

    for command in ("conda.exe", "conda.bat", "conda"):
        found = shutil.which(command)
        if found:
            return found

    candidates: list[Path] = []

    conda_exe = os.environ.get("CONDA_EXE")
    if conda_exe:
        candidates.append(Path(conda_exe))

    python_exe = Path(sys.executable)
    candidates.extend(
        [
            python_exe.parent / "Scripts" / "conda.exe",
            python_exe.parent / "Scripts" / "conda.bat",
            python_exe.parent / "condabin" / "conda.bat",
            python_exe.parent / "condabin" / "conda.exe",
        ]
    )

    home = Path.home()
    candidates.extend(
        [
            home / "anaconda3" / "Scripts" / "conda.exe",
            home / "miniconda3" / "Scripts" / "conda.exe",
            home / "anaconda3" / "condabin" / "conda.bat",
            home / "miniconda3" / "condabin" / "conda.bat",
            Path("C:/ProgramData/Anaconda3/Scripts/conda.exe"),
            Path("C:/ProgramData/miniconda3/Scripts/conda.exe"),
            Path("D:/software/anaconda/anaconda3/Scripts/conda.exe"),
            Path("D:/software/anaconda/anaconda3/condabin/conda.bat"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def _relaunch_in_conda(conda_exe: str) -> int:
    """在 conda 的 item_manager 环境中重新运行当前脚本。"""

    script_path = Path(__file__).resolve()
    project_root = script_path.parent

    env = os.environ.copy()
    env[RELAUNCH_FLAG] = "1"

    if Path(conda_exe).suffix.lower() in {".bat", ".cmd"}:
        command = [
            "cmd.exe",
            "/c",
            conda_exe,
            "run",
            "--no-capture-output",
            "-n",
            ENV_NAME,
            "python",
            str(script_path),
        ]
    else:
        command = [
            conda_exe,
            "run",
            "--no-capture-output",
            "-n",
            ENV_NAME,
            "python",
            str(script_path),
        ]

    print(f"当前未在 conda 环境 {ENV_NAME} 中运行。")
    print(f"正在重新启动：{' '.join(command)}")

    try:
        return subprocess.call(command, cwd=str(project_root), env=env)
    except OSError as exc:
        print(f"进入 conda 环境失败：{exc}")
        return 1


def main() -> None:
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    if not _is_target_env() and not os.environ.get(RELAUNCH_FLAG):
        conda_exe = _find_conda()

        if not conda_exe:
            print("未找到 conda 命令，无法自动进入 item_manager 环境。")
            print("请先手动执行：conda activate item_manager")
            sys.exit(1)

        sys.exit(_relaunch_in_conda(conda_exe))

    import uvicorn

    from app.core.config import settings

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = settings.DEBUG

    print(f"当前 Python：{sys.executable}")
    print(
        "当前 Conda 环境："
        f"{os.environ.get('CONDA_DEFAULT_ENV') or Path(sys.prefix).name}"
    )
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