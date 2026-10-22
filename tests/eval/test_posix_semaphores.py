import json
from typing import Literal

import pytest

from harness.nix_eval import nix_eval


@pytest.mark.parametrize("platform", ["darwin", "linux"])
def test_default_is_disabled(platform: Literal["darwin", "linux"]) -> None:
    result = nix_eval(platform=platform)
    assert result.returncode == 0, result.stderr
    spec = json.loads(result.stdout)
    if platform == "darwin":
        assert spec["posix_semaphore_access"] == "none"
    else:
        assert "posix_semaphore_access" not in spec


@pytest.mark.parametrize("access", ["none", "create-unlink", "full"])
def test_darwin_policy_is_serialized(access: str) -> None:
    result = nix_eval(platform="darwin", darwin_posix_semaphore_access=access)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["posix_semaphore_access"] == access


@pytest.mark.parametrize("access", ["create-unlink", "full"])
def test_linux_rejects_darwin_permissions(access: str) -> None:
    result = nix_eval(platform="linux", darwin_posix_semaphore_access=access)
    assert result.returncode != 0
    assert "darwinPosixSemaphoreAccess is only supported on macOS" in result.stderr


@pytest.mark.parametrize("access", [True, None, 1, [], {}, "create", "all"])
def test_invalid_values_are_rejected(access: object) -> None:
    result = nix_eval(platform="darwin", darwin_posix_semaphore_access=access)
    assert result.returncode != 0
    assert "darwinPosixSemaphoreAccess must be one of" in result.stderr
