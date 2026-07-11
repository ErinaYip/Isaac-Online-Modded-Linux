{
  description = "Standalone Linux/Nix package for Isaac Online Modded";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      pkgsFor = system: import nixpkgs { inherit system; };
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "isaac-online-modded-linux";
            version = "1.4.0";
            src = ./.;

            pyproject = true;
            build-system = [ pkgs.python3Packages.setuptools ];

            pythonImportsCheck = [ "isaac_online_modded" ];
            checkPhase = ''
              runHook preCheck
              PYTHONPATH="$PWD/src:$PYTHONPATH" python -m unittest discover -s tests -v
              runHook postCheck
            '';

            meta = {
              description = "Standalone Linux CLI patcher for Isaac Online Modded";
              homepage = "https://github.com/ErinaYip/Isaac-Online-Modded";
              mainProgram = "isaac-online-modded";
              platforms = pkgs.lib.platforms.linux;
            };
          };
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/isaac-online-modded";
          meta.description = "Run Isaac Online Modded Linux";
        };
      });

      checks = forAllSystems (system: {
        default = self.packages.${system}.default;
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.python3
              pkgs.nixfmt
            ];
          };
        }
      );

      formatter = forAllSystems (system: (pkgsFor system).nixfmt);
    };
}
