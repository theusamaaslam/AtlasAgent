# nix/overlays.nix — Expose pkgs.atlas-agent for external NixOS configs
{ inputs, ... }:
{
  flake.overlays.default = final: _: {
    atlas-agent = final.callPackage ./atlas-agent.nix {
      inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
      npm-lockfile-fix = inputs.npm-lockfile-fix.packages.${final.stdenv.hostPlatform.system}.default;
      rev = inputs.self.rev or null;
    };
  };
}
