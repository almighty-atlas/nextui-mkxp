# Distribution STOP/GO gate

M0 / issue #3, 2026-10-25. Evidence: [SOURCES](SOURCES.md),
[inventory](audit/source-inventory.json), [commands](audit/ISSUE-003-EVIDENCE.md).

**Current decision: BLOCKED for code import from R36S and all binary releases.**
GO is limited to static research, attribution clarification and planning a pinned
source manifest. The audit's existence does not authorize engine build Issue #4.
No hardware or legal clearance is claimed.

| Gate | State | Evidence needed to change state / reviewer |
| --- | --- | --- |
| Engine and R36S research snapshots identified | GO (research only) | Immutable commits and source citations in SOURCES |
| No upstream implementation/game/binary imported | GO (this change) | Git diff and automated static validation |
| R36S individual file/patch grants and base revisions | BLOCKED | Maintainer/human resolves authorship, GPL version scope, SDL patch licensing and exact base; record decision per imported file |
| Build dependency closure | BLOCKED | Build owner pins exact source commits/archives/checksums, nested submodules, patches, system packages, toolchain/sysroot and all enabled optional features |
| Embedded resources and original project code | BLOCKED | Human approves font/icon/controller DB/shader notices or lawful replacements; select license for this project's original implementation before publishing it |
| Combined GPL version / optional OpenSSL | BLOCKED | Human reviews configuration, all license alternatives/compatibility and any applicable installation-information requirement |
| Corresponding source and LGPL relinking | BLOCKED | Source delivery plus tested source rebuild/relink or suitable dynamic replacement route; artifacts described below |
| Binary and package provenance | BLOCKED | Exact package file list, hashes, ELF/link map and dependency notice mapping reviewed; no foreign ARM32/prebuilt unknown files |
| Release approval | BLOCKED | Named human reviewer, dated evidence and no unresolved rights; separate H700 technical acceptance also required |

## Required concrete release artifacts

A later release candidate must make the following reviewable **before** publication:

1. `manifest.json`: engine commit, every dependency and submodule commit/archive
   SHA-256, patch hashes/authors/licenses, compiler/binutils/sysroot/package
   versions, configuration flags, static/shared/runtime/build-only role, output
   hashes and file-to-source/license/notice mapping. Mark excluded features
   explicitly. Resolve every `UNKNOWN` affecting shipped files.
2. `source/` archive accompanying binaries: preferred editable source for exact
   engine/dependencies/changes, headers, generated-input sources, build and
   installation scripts, patch ordering, configuration and reproducible commands.
   Record any justified system-library exclusions. Do not use this inventory's
   unverified archive metadata or moving branches as a release lockfile.
3. `LICENSES/` with full applicable texts, `THIRD_PARTY_NOTICES` with copyright,
   attribution, disclaimers, license elections and relevant upstream NOTICE
   contents; changed files carry required modification notices/dates. Include
   font-specific notices and preserve any reserved-font-name restrictions.
4. `relink/` for each statically linked LGPL component: exact library source and
   patches, application objects/archives or complete usable source rebuild route,
   linker script/order/flags, ABI/toolchain instructions and a verified command
   relinking a modified library. Preserve unstripped intermediate files needed
   for relinking. If using shared LGPL libraries instead, document and actually
   verify compatible library replacement; still satisfy source/notices duties.
5. `BUILDING.md` with non-privileged pinned build/relink instructions, environment
   requirements and installation steps; sanitized build logs, Meson dependency
   resolution, linker map and `readelf -h/-l/-d` output. ELF `NEEDED` alone misses
   static code and `dlopen` libraries, so reconcile all three with the manifest.
6. Release zip, source/relink archives and checksums; offline archive allowlist
   validation, notice/source coverage report and human sign-off. If relying on an
   alternative source-offer mechanism, obtain review of its exact text, scope,
   availability, validity period and fulfillment process before use.

## End-user archive boundary

Permitted only **after all gates pass**: reviewed native H700 engine, necessary
redistributable libraries, original/reviewed launcher/configuration, approved
font/resources, license/attribution texts, build/source/relink instructions and
legal test content with its own documented rights. Source/relink artifacts may be
separate accompanying archives with an explicit mapping to the binary checksum.

Always exclude games, fan-game bundles, Pokémon materials, RTP, ROMs, proprietary
RGSS/RPG Maker executables, proprietary fonts, saves, license keys, personal logs
and unreviewed firmware/GPU binaries. Do not package an R36S release archive or
claim its ARM32 libraries are H700-compatible. No release assets were downloaded
or inspected here.

## Precise next unblocked step

In an M0 documentation/provenance follow-up, have a human review the R36S file
and patch grant questions and resolve the intended source/configuration profile,
including fonts, shaders and HTTPS. Then produce a checksum-verified lockfile for
that profile and assign source/relink deliverables. Historical R36S binary reuse
stays blocked if its exact source cannot be reconstructed; it is not required
for a new source-based H700 port. Hardware/ABI work remains separately gated by
the roadmap. Do not start Issue #4 from this audit.
