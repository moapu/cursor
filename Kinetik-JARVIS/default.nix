{ lib, stdenvNoCC }:

stdenvNoCC.mkDerivation {
  pname = "kinetik-jarvis-cursors";
  version = "1.0";
  src = ./.;

  dontConfigure = true;
  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/icons/Kinetik-JARVIS"
    cp -a cursors index.theme cursor.theme "$out/share/icons/Kinetik-JARVIS/"
    runHook postInstall
  '';

  meta = {
    description = "JARVIS-inspired Kinetik animated cursor theme";
    platforms = lib.platforms.linux;
  };
}
