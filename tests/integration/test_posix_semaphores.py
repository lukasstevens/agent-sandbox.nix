import ctypes
import json
import os
import uuid
from collections.abc import Iterator

import pytest

from harness.build import BuildSandbox
from harness.launch import Launch

pytestmark = pytest.mark.darwin


@pytest.fixture
def host_semaphore() -> Iterator[str]:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
    libc.sem_open.restype = ctypes.c_void_p
    libc.sem_close.argtypes = [ctypes.c_void_p]
    libc.sem_unlink.argtypes = [ctypes.c_char_p]
    name = f"/asbx-{uuid.uuid4().hex[:16]}"
    handle = libc.sem_open(name.encode(), os.O_CREAT | os.O_EXCL, 0o600, 0)
    assert handle != ctypes.c_void_p(-1).value, f"host sem_open: errno={ctypes.get_errno()}"
    try:
        yield name
    finally:
        libc.sem_unlink(name.encode())
        libc.sem_close(handle)


@pytest.mark.parametrize("access", ["none", "create-unlink", "full"])
def test_creation_inherited_synchronization_and_cleanup(
    access: str, build_sandbox: BuildSandbox, launch: Launch
) -> None:
    result = launch(build_sandbox("posix-semaphores", {"access": access}), "semaphore-probe lifecycle")
    assert result.returncode == 0, result.stderr
    expected = {"create": "EPERM"} if access == "none" else {
        "create": "ok",
        "reopen": "ok" if access == "full" else "EPERM",
        "inherited_post_wait": "ok",
        "unlink": "ok",
    }
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize("access", ["none", "create-unlink", "full"])
def test_opening_an_existing_host_semaphore_requires_full_access(
    access: str, build_sandbox: BuildSandbox, launch: Launch, host_semaphore: str
) -> None:
    result = launch(
        build_sandbox("posix-semaphores", {"access": access}),
        f"semaphore-probe open {host_semaphore}",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"open": "ok" if access == "full" else "EPERM"}


@pytest.mark.parametrize("access", ["none", "create-unlink", "full"])
def test_unlink_permission_also_applies_to_host_names(
    access: str, build_sandbox: BuildSandbox, launch: Launch, host_semaphore: str
) -> None:
    # Deliberately exercise the documented limitation using our own test object.
    result = launch(
        build_sandbox("posix-semaphores", {"access": access}),
        f"semaphore-probe unlink {host_semaphore}",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"unlink": "EPERM" if access == "none" else "ok"}
