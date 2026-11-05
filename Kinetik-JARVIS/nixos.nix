{ pkgs, ... }:

{
  environment.systemPackages = [ (pkgs.callPackage ./default.nix { }) ];
  xdg.icons.fallbackCursorThemes = [ "Kinetik-JARVIS" ];
  environment.sessionVariables = {
    XCURSOR_THEME = "Kinetik-JARVIS";
    XCURSOR_SIZE = "32";
  };
}
