"""Generic Darwin named-semaphore probe; no third-party Python dependencies."""

import ctypes
import errno
import json
import os
import sys

libc = ctypes.CDLL(None, use_errno=True)
# Declare the fixed arguments of this variadic call: required by Apple ARM64's ABI.
libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
libc.sem_open.restype = ctypes.c_void_p
for function in ("sem_close", "sem_post", "sem_trywait"):
    getattr(libc, function).argtypes = [ctypes.c_void_p]
    getattr(libc, function).restype = ctypes.c_int
libc.sem_unlink.argtypes = [ctypes.c_char_p]
libc.sem_unlink.restype = ctypes.c_int
FAILED = ctypes.c_void_p(-1).value


def error() -> str:
    return errno.errorcode.get(ctypes.get_errno(), str(ctypes.get_errno()))


def main() -> dict[str, str]:
    operation = sys.argv[1]
    name = (sys.argv[2] if len(sys.argv) > 2 else f"/asbx-{os.getpid()}").encode()
    if operation == "unlink":
        return {"unlink": "ok" if libc.sem_unlink(name) == 0 else error()}
    flags = os.O_CREAT | os.O_EXCL if operation == "lifecycle" else 0
    semaphore = libc.sem_open(name, flags, 0o600, 0)
    key = "create" if operation == "lifecycle" else "open"
    if semaphore == FAILED:
        return {key: error()}
    result = {key: "ok"}
    try:
        if operation != "lifecycle":
            return result
        reopened = libc.sem_open(name, 0)
        result["reopen"] = error() if reopened == FAILED else "ok"
        if reopened != FAILED:
            libc.sem_close(reopened)
        child = os.fork()
        if child == 0:
            os._exit(0 if libc.sem_post(semaphore) == 0 else 1)
        _, status = os.waitpid(child, 0)
        result["inherited_post_wait"] = (
            "ok" if status == 0 and libc.sem_trywait(semaphore) == 0 else "failed"
        )
        return result
    finally:
        if operation == "lifecycle":
            result["unlink"] = "ok" if libc.sem_unlink(name) == 0 else error()
        libc.sem_close(semaphore)


if __name__ == "__main__":
    print(json.dumps(main()))
