{ pkgs ? import ../../pinned-nixpkgs.nix { }, access ? "none" }:
let
  sandbox = import ../../../default.nix { pkgs = pkgs; };
  probe = pkgs.writeScriptBin "semaphore-probe" ''
    #!${pkgs.python3}/bin/python3
    ${builtins.readFile ../payloads/posix_semaphores.py}
  '';
in sandbox.mkSandbox {
  pkg = pkgs.bashInteractive;
  binName = "bash";
  outName = "sandboxed-semaphore-test";
  allowedPackages = [ pkgs.coreutils probe ];
  darwinPosixSemaphoreAccess = access;
}
