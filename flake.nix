{
  description = "flake pinning the nixpkgs version for this project";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/25.05";

  outputs =
    { self, nixpkgs }:
    {
      devShells.x86_64-linux.default = nixpkgs.legacyPackages.x86_64-linux.mkShell {
        packages = with nixpkgs.legacyPackages.x86_64-linux; [
          python313Full
          python313Packages.requests
          python313Packages.aiohttp
          python313Packages.websockets
        ];
      };
    };
}
