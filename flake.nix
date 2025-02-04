{
  description = "oliviabot";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, poetry2nix, flake-utils }:
    flake-utils.lib.eachDefaultSystem (sys:
    let
      pkgs = nixpkgs.legacyPackages.${sys};
      python = pkgs.python311;
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryEnv overrides;
      problematic-dependencies = (deps: overrides.withDefaults
        (final: prev:
          (builtins.mapAttrs (dep: extras:
            prev.${dep}.overridePythonAttrs
            (old: {
              buildInputs = (old.buildInputs or [ ]) ++ map (package: prev.${package}) extras;
            })
          ) deps)
        ));
      env = mkPoetryEnv {
        projectDir = ./.;
        inherit python;
        preferWheels = true;
        extraPackages = (pkgs: [ pkgs.pip ]);
        overrides = problematic-dependencies {
          HyFetch = [ "setuptools" ];
          colour-science = [ "hatchling" ];
        };
      };
    in 
    {
      devShells.default = pkgs.mkShell {
        buildInputs = [env];
        packages = [
          pkgs.poetry
          (pkgs.writeScriptBin "x" ''
            ${env}/bin/watchmedo auto-restart \
              --debounce-interval 2 \
              --directory . \
              --pattern .reload-trigger \
              --no-restart-on-command-exit \
              ${env}/bin/python3.11 -- run.py
          '')
        ];
        # This is a bit of a hack but it is quite helpful!
        shellHook = ''
          ${pkgs.coreutils}/bin/cat ./.vscode/settings.json |
          ${pkgs.jq}/bin/jq -n 'input? // {} | .["python.defaultInterpreterPath"] = "${env}/bin/python"' |
          ${pkgs.moreutils}/bin/sponge ./.vscode/settings.json
        '';
      };
    }
  );
}