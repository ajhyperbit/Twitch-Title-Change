{
  description = "flake pinning the nixpkgs version and python environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/25.05";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    system = "x86_64-linux";

    pkgs = nixpkgs.legacyPackages.${system};
    
    millify = pkgs.python313Packages.buildPythonPackage rec {
      pname = "millify";
      version = "0.1.1";

      src = pkgs.python313Packages.fetchPypi {
        inherit pname version;
        sha256 = "06kzb6349scv57x6yi6h9kvf1847pzsamr2w3fa3zlmnk3ffz7b1";
      };

      pyproject = true;
      buildInputs = [pkgs.python313Packages.setuptools];
    };

    obs-websocket-py = rec {
      pname = "obs-websocket-py";
      version = "1.0";

      src = pkgs.python313Packages.fetchPypi {
        inherit pname version;
        sha256 = "1580csnz01kk95q3c7wrqxhx6z2y9ihj0k1vg70idq8mrj00gwdk";
      };

      pyproject = true;
      buildInputs = [pkgs.python313Packages.setuptools];
    };

    channelPointsEnv = pkgs.python313.withPackages (ps:
      with ps; [
        aiohttp
        colorama
        irc
        requests
        validators
        websockets
        websocket-client
        emoji
        pillow
        python-dateutil
        pre-commit-hooks
        flask
        pandas
        pytz
        millify
        obs-websocket-py
      ]);
  in {
    devShells.${system}.default = pkgs.mkShell {
      venvDir = "./.venv";

      packages = [
        channelPointsEnv
      ];
    };
  };
}
