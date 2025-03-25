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
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication mkPoetryEnv overrides;
      problematic-dependencies = (deps: overrides.withDefaults
        (final: prev:
          (builtins.mapAttrs (dep: extras:
            prev.${dep}.overridePythonAttrs
            (old: {
              buildInputs = (old.buildInputs or [ ]) ++ map (package: prev.${package}) extras;
            })
          ) deps)
        ));
      config = {
        projectDir = ./.;
        inherit python;
        preferWheels = true;
      };
      app = mkPoetryApplication (config // {
        checkGroups = [ ];
      });
      env = mkPoetryEnv (config // {
        extraPackages = (pkgs: [ pkgs.pip ]);
        overrides = problematic-dependencies {
          HyFetch = [ "setuptools" ];
          colour-science = [ "hatchling" ];
          parse-discord = [ "flit" ];
        } # extra problematic dependencies
        ++ (overrides.withoutDefaults
          (final: prev: {
            icupy = prev.icupy.overridePythonAttrs (old: {
              buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools pkgs.icu76 ];
              nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.cmake pkgs.icu76 ];
              preConfigure = ''
                export PKG_CONFIG_PATH=${pkgs.icu76}/lib/pkg-config:$PKG_CONFIG_PATH
                export LD_LIBRARY_PATH=${pkgs.icu76}/lib:$LD_LIBRARY_PATH
                cd src
              '';
              preBuild = ''
                cd ../..
              '';
            });
          })
        );
      });
    in 
    {
      apps.default = {
        type = "app";
        program = "${env}/bin/prod";
      };
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
              ${env}/bin/dev
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