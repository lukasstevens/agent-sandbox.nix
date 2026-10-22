import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pytest

from harness.builders import make_host_darwin, make_session_darwin, make_spec_darwin
from launcher.lib import build_spec
from launcher.lib.build_spec import PosixSemaphoreAccess
from launcher.lib.launch_config.darwin.compute import compute_launch_config
from launcher.lib.launch_config.darwin.seatbelt import posix_semaphores
from launcher.lib.launch_log import write_launch_request


@pytest.mark.parametrize(
    ("access", "rules"),
    [
        ("none", []),
        ("create-unlink", ["(allow ipc-posix-sem-create ipc-posix-sem-unlink)"]),
        ("full", ["(allow ipc-posix-sem)"]),
    ],
)
def test_policy_only_adds_the_requested_semaphore_permissions(
    access: PosixSemaphoreAccess, rules: list[str]
) -> None:
    def profile(mode: PosixSemaphoreAccess) -> list[str]:
        config = compute_launch_config(
            make_spec_darwin(posix_semaphore_access=mode),
            make_host_darwin(),
            make_session_darwin(),
        )
        return [line for line in config.seatbelt_profile_lines if line]

    lines = profile(access)
    assert [line for line in lines if line.startswith("(allow ipc-posix-sem")] == rules
    assert [line for line in lines if line not in posix_semaphores(access)] == profile("none")


@pytest.mark.parametrize("access", ["none", "create-unlink", "full"])
def test_build_spec_roundtrip(
    access: PosixSemaphoreAccess, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = make_spec_darwin(posix_semaphore_access=access)
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(asdict(spec), default=str))
    monkeypatch.setattr(sys, "platform", "darwin")
    assert build_spec.load_build_spec(path) == spec


@pytest.mark.parametrize("access", ["none", "create-unlink", "full"])
def test_policy_is_recorded_in_launch_log(access: PosixSemaphoreAccess, tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    write_launch_request(
        log, tmp_path, Path("/spec.json"),
        make_spec_darwin(posix_semaphore_access=access), tmp_path, datetime(2026, 1, 1),
    )
    assert f"darwinPosixSemaphoreAccess: {access}" in log.read_text()
