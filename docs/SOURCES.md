# External references and provenance

Checked when bootstrapping the repository on **2026-10-25**. These are references, not imported dependencies; their licenses and code may change.

1. [Official NextUI documentation](https://nextui.loveretro.games/docs/) — current supported devices, Pak conventions.
2. [NextUI PAKS.md](https://github.com/LoveRetro/NextUI/blob/main/PAKS.md) — `launch.sh`, tags, environment variables, standalone constraints, MinArch lacks OpenGL libretro API support. **Re-verify against pinned NextUI revision before implementation**.
3. [NextUI](https://github.com/LoveRetro/NextUI) — upstream; currently advertises a PolyForm Noncommercial license. Using patterns is distinct from redistributing NextUI code.
4. [mkxp-z](https://github.com/mkxp-z/mkxp-z) — main engine, RGSS/Ruby runtime.
5. [R36S native reference port](https://github.com/Periko21/mkxp-z-r36s), observed commit `b665091c1ff571a7a468bbf33af2f7c803c75220` — reports functioning Infinite Fusion 6.8.x on RK3326/ArkOS (32-bit target), KMS/DRM GLES, ALSA, game-specific zram workaround, build scripts and license notices. **Hardware results cannot be transferred to H700 without testing.**
6. [R36S legal notice](https://github.com/Periko21/mkxp-z-r36s/blob/main/NOTICE.md) — initial third-party license inventory, not sufficient for a new binary.
7. [H700 NextUI historical/experimental port](https://github.com/pvaibhav/NextUI) — controller mapping changes and H700 background; use upstream stable as source of truth.

## Must verify before copying/building/distributing

- Pin every upstream revision and save specific license texts and patch authors.
- Map individual source files and patches to licensing terms; record attribution.
- Confirm mkxp-z GPL obligations and the licensing impact of linked dependencies, in particular optional HTTPS/OpenSSL and static LGPL components; confirm that corresponding source/relinking requirements are met.
- Keep ROM/game content and proprietary assets entirely outside repository and build artifacts.
- Include an exact source manifest and source availability for each released binary.

_References above are technical research, not an endorsement or a guarantee of compatibility._
