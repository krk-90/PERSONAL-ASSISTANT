import os
import shutil
import tempfile
import subprocess
from urllib.parse import urlparse
import time
import shutil

from agent.graph.git_agent import (
    create_git_agent,
    get_git_agent_response,
)


class RepoError(Exception):
    pass


def is_github_url(value: str) -> bool:
    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc == "github.com"
        )
    except Exception:
        return False


def clone_repo(repo_url: str) -> str:
    git_exe = shutil.which("git")

    print("GIT PATH:", git_exe)

    if not git_exe:
        raise RepoError(
            "Git executable not found in container. "
            "Install git in Dockerfile."
        )

    temp_dir = tempfile.mkdtemp(prefix="repo_")

    try:
        subprocess.run(
            [
                git_exe,
                "clone",
                "--depth",
                "1",
                repo_url,
                temp_dir,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        return temp_dir

    except Exception as e:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        raise RepoError(
            f"Failed to clone repository: {e}"
        )

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RepoError(f"Failed to clone repository: {e}")


def resolve_repo(repo: str) -> tuple[str, bool]:
    if is_github_url(repo):
        local_path = clone_repo(repo)
        return local_path, True

    if os.path.exists(repo):
        return repo, False

    raise RepoError(
        f"Repository not found: {repo}"
    )


async def run_git_query(
    llm,
    repo,
    query,
    user_id=None,
):
    local_repo = None
    cloned = False

    try:
        start = time.perf_counter()

        print("[GIT] Resolving repo")

        local_repo, cloned = resolve_repo(repo)

        print(
            f"[GIT] Resolve took "
            f"{time.perf_counter() - start:.2f}s"
        )

        start = time.perf_counter()

        print("[GIT] Creating agent")

        agent = await create_git_agent(
            llm,
            local_repo,
        )

        print(
            f"[GIT] Agent creation took "
            f"{time.perf_counter() - start:.2f}s"
        )

        start = time.perf_counter()

        print("[GIT] Executing agent")

        result = await get_git_agent_response(
            agent=agent,
            query=query,
            user_id=user_id,
        )

        print(
            f"[GIT] Execution took "
            f"{time.perf_counter() - start:.2f}s"
        )

        print("[GIT] RESULT:")
        print(result)

        return result

    finally:
        if cloned and local_repo:
            print("[GIT] Cleaning temporary repo")
            shutil.rmtree(
                local_repo,
                ignore_errors=True,
            )