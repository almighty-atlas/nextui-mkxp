# H700 engine build-input preflight (Issue #4 static slice)

Recorded 2026-10-28.

**STATIC PREPARATION ONLY — real manifest BLOCKED; no build or release grant.**
This independent branch starts from main `107db135b8e8ef72f6d61c78be14416330727b0d`.
It does not merge/change [PR #30](https://github.com/almighty-atlas/nextui-mkxp/pull/30)
or copy its implementation. Its [engine plan at 91b5a27][PLAN] was read as input.
No upstream engine code, source archives, binaries, games, vendor libraries,
device logs or private host paths are imported. Original checker/tests are
MIT-marked; that does not select a license for unrelated project/upstream code.

## Prerequisite decision

Read AGENTS, README, architecture, roadmap, test plan, Issues #1–#4 and their
comments, PR #19/#27/#30, plus PR #19's distribution gate and selected input
inventory. Issues #1–#4 remain OPEN. No acceptance checkboxes are completed here.

| Prerequisite | Existing evidence | Remaining gate / consequence |
| --- | --- | --- |
| #1 hardware baseline | Owner inventory: AArch64/kernel 4.9.170; libc GLIBC_2.27 namespace; PR #30 one visible Mali-G31 video/normal-return PASS | Exact firmware identity for that trial and full engine library/input/audio baseline incomplete; inventory/video is not engine validation |
| #2 architecture | Standalone native preference; unmerged PR #21 ADR / source-based discovery contract | Proposed decision and real engine discovery/lifecycle not accepted; no MinArch GL/menu/save-state promises |
| #3 rights | PR #19 `9d482dc981401166b40155678ad00e29daad9163`: GO for static provenance research and pinned-manifest planning | R36S import and binary release BLOCKED; combined work, SDL Mali/patch grants, embedded assets, source/relinking and full selected closure unresolved |
| #4 environment | Existing working Debian builder on **tiny02**, per explicit owner correction; GCC 8.3 AArch64, complete Linux-4.9.170/glibc-2.28 sysroot, successful SDL/AArch64 testbuild | Not missing-builder BLOCKED. Current tool/package fingerprints, source/output receipt binding and clean-room reproducibility remain incomplete |

**Decision:** the task explicitly authorizes only the source/static preparation
below, which fits PR #19's research GO. This does **not** start the full #4 build
phase or waive its #1/#2/#3 prerequisites. A separate Draft PR is appropriate;
actual build use and every publication remain gated. A validator PASS is never
an execution/import/deployment/release authorization.

## tiny02 correction and documentary configuration review

The earlier plan's “no compatible host/container provisioned” describes its
Alpine authoring environment, **not tiny02**. The owner now confirms a working
Debian builder and successful private builds there. No SSH, Docker socket,
container operation, downloads, service change or target execution was needed
or performed for this review.

The inspected PR #27 at `1c04c578e3a35acc40b8669986228e3a2ae056c0`
contains `docs/build/issue-26-inputs.json`, host-tool fingerprints, evidence,
source build drivers and successful source/SDL/proc-link results. These
documented technical facts are consistent with the reported tiny02 configuration:

| Configuration | Documentary check / interpretation |
| --- | --- |
| Compiler | GCC 8.3.0, `aarch64-nextui-linux-gnu`, x86_64 Linux host; recipe `d37268f5160ec6cd4da541524c8111797e060c36`, archive SHA-256 `d4ac4ef1968668f93f625f2b226c69d74739ae58ff640d2ce3aaae6b4d1b93d3` |
| Target glibc | Complete source-built 2.28; `--host=aarch64-nextui-linux-gnu --build=x86_64-pc-linux-gnu --with-headers=<private>/kernel-headers/include --enable-kernel=4.9.0 --disable-werror --disable-nscd`; staged install, not a partial libc or spoofed ELF note |
| Kernel | Linux 4.9.170 UAPI; GNU Linux ABI note 4.9.0 in produced executable/startup objects. The original SDK kernel-4.19 floor must not silently return |
| Link selection | Explicit `--sysroot`, startup-object `-B`, target include/library paths, `-rpath-link`, strict undefined references and actual link-input audit. Libtool needed `-Wc` forwarding of startup/static-GCC flags; `--sysroot` alone is not complete isolation |
| Native bootstrap | M4 1.4.21 + make 4.3, bison 3.8.2, gawk 5.3.2; earlier failures are history, not grounds for repeating full builds |
| SDL/private variant | Pinned Mali fork + H700 patch; audio-disabled private link SDL differs from stock SDL. Executable AArch64, `/lib/ld-linux-aarch64.so.1`, ABI 4.9.0, direct GLIBC_2.17, SDL + libc NEEDED; private SDL itself requires GLIBC_2.27. Same-workspace repeat-link, not clean-room reproducibility |
| Later owner hardware trial | PR #30 `91b5a27378150bb479fc8546f2bddb6c6e5b1da7`: ELF `d41477f3a3803ee22e778629d4b5c9a0947cd4449e1717f1e7f347226a09a5f9`, visible animation and usable NextUI return, SOURCE_ONLY restored. Not a C++/engine result |

Evidence levels: prior builds **verified-on-host as documented / owner-confirmed**;
this session's comparison **STATIC**, not an independently repeated tiny02 build.
No tiny02-named host-specific receipt was found in the inspected #27/#30 trees.
Do not relabel earlier per-experiment sysroot/tool hashes as tiny02's current
hashes without receipt binding. Host existence is established by the owner;
host fingerprint/clean-room reproducibility is a distinct unfinished gate.

## Implemented input contract

- `build/h700-engine/inputs.json`: 11 **required candidates**, including pinned
  compiler, six GNU/kernel archives, mkxp-z, SDL, H700 patch and Ruby. Roles
  distinguish source/engine-source/patch/cross-toolchain, with host-target vs
  neutral placement. License expressions are candidate component terms with
  evidence/obligations, **not whole-archive legal clearance**. Input approval is
  intentionally BLOCKED, including previously host-used artifacts.
- Real checksums are selected metadata from PR #27's lock and PR #19's Ruby wrap,
  not newly downloaded/verified bytes. Ruby's hash is upstream-declared. Release
  names are content-pinned by SHA-256; Git inputs require a full 40-hex commit.
- mkxp-z/SDL **archive SHA-256 are null**: no verified archive bytes/digest were
  supplied. PR #27's custom SDL tree/configure digest is not an archive hash.
  No invented hashes or vendored source. The H700 patch's file hash is known,
  but its exact grant is unresolved (`NOASSERTION`, refused by the checker).
- Top gates cover #1/#2/#3, dependency closure and builder identity. This is a
  seed, **not a complete engine lockfile**: native Meson/Ninja/CMake/Ruby tools,
  sysroot output binding, GL headers, libstdc++/libgcc, media/text dependencies,
  nested patches and embedded resources need explicit later entries/review.
  Nothing optional is silently fetched or treated as approved.

## Validator usage and guarantees

Python **3.10+**, standard library only, POSIX/Linux for descriptor-safe cache
access (`O_NOFOLLOW`, `dir_fd`, `O_NONBLOCK`). Portable offline commands from repo root:

```sh
python3 -I -B -m unittest discover -s tests -p 'test_h700_engine_inputs.py' -v
python3 -I -B scripts/check_h700_engine_inputs.py --cache /explicit/private/input-cache
```

The second command intentionally exits **2 / BLOCKED** with the checked-in
manifest, even if files exist. Exit 0 means only the explicitly supplied manifest
and cache passed the offline contract. JSON always retains `build_authorized:
false` and `distribution: BLOCKED`. There is no `--force`, approval bypass,
fetch, extract, configure, ARM/host-input execution or deployment path.

The checker enforces strict JSON/schema keys, required source identities/gates,
target baseline, immutable references/checksums, license metadata, input blockers,
recorded approvals and cache bytes. It reports **all top gates and the first
failed check per input**, using bounded numeric input indexes/fixed codes, not
private paths or payloads. Invalid JSON/duplicate keys, absent files, directories,
FIFOs, unknown license, open approvals and mutations fail closed. Checksums are
streamed before tar parsing. Existing regular cache files only; read-only open.

Cache paths must be canonical relative POSIX paths, no `..`, absolute paths,
Windows separators/drives or control characters. Descriptor-relative opens reject
symlinks at root, directory and file components (even internal links). Caller
selects a trusted cache parent; ancestors of that explicit root and manifest are
not an OS sandbox. Tar checking rejects traversal, duplicate names, links,
special devices and setuid/setgid modes, limits members/declared unpacked size,
and never extracts. **All tar links are conservatively blocked**, even legitimate
internal compiler/source links; passing this format policy requires a separately
reviewed extension, not silently repacking/changing a known archive's checksum.
Raw/archived ELF headers are checked against declared host/target roles; this is
only an ABI-header sanity check, not interpreter/NEEDED/version/closure inspection.

Trust boundary: the manifest and reviewer records require human review; strings
are not signatures or proof of legal consent. The validator does not authenticate
a claimed upstream commit inside an archive, license texts, compiler execution,
full build recipes, ELF dependency closure or hostile/concurrent OS behavior.
Before/after file metadata detects ordinary in-place mutation, not all adversarial
same-user races. Python/tar parsing is not a security sandbox. Limits do not
promise a hard CPU/memory bound against every malformed compressed stream.

## Executed verification

**verified-on-host**, this authoring environment only. Existing private Python
3.14.10 reused; no packages installed, no input archive downloaded/read from tiny02.

```sh
LD_LIBRARY_PATH=/home/opencode/.cache/nextui-host-tools/usr/lib /home/opencode/.cache/nextui-host-tools/usr/bin/python3 -I -B -m unittest discover -s tests -p 'test_h700_engine_inputs.py' -v
```

```text
Ran 32 tests in 0.679s
OK
```

The suite uses temporary **synthetic non-executable** blobs/tars and synthetic
ELF headers, never genuine compiler/engine/runtime inputs. Positive input and tar
checks pass without granting build/release. Negatives cover checksum before
parsing, missing archives, traversal, symlink escapes, FIFO/no hang, unsafe tar
members/modes, missing/unknown license, host-target mixing, wrong ABI baseline,
open approvals, missing hashes, mutable refs, duplicate/malformed JSON and scope
escalation. CLI exit codes and deterministic sanitized JSON are exercised. Real
repository manifest must remain BLOCKED. Static API checks catch accidental
network/process/extraction imports/calls; they are regression guards, not a jail.

Also executed: a standard-library JSON comparison against local pinned git blobs
(`git show 1c04c578e3a35acc40b8669986228e3a2ae056c0:docs/build/issue-26-inputs.json`
and `git show 9d482dc981401166b40155678ad00e29daad9163:docs/audit/source-inventory.json`).
Compared the six archive hashes, compiler archive, H700 patch and Ruby wrap hash,
plus compiler/SDL revisions; exit 0:

```text
PASS: 9 available file/archive hashes and compiler/SDL revisions match pinned PR metadata; 2 archive hashes remain null/BLOCKED
```

This verifies transcription, not external archive bytes. The real CLI was also
run with an explicitly absent local cache (no files created):

```sh
LD_LIBRARY_PATH=/home/opencode/.cache/nextui-host-tools/usr/lib /home/opencode/.cache/nextui-host-tools/usr/bin/python3 -I -B scripts/check_h700_engine_inputs.py --cache /home/opencode/.cache/nextui-h700-engine-not-supplied
```

Expected actual **exit 2**, deterministic JSON `status: BLOCKED`,
`checked_inputs: 0`, `build_authorized: false`, `distribution: BLOCKED`;
five prerequisite/closure/builder approval blockers and eleven first-input
blockers (approvals, explicit input blockers or missing patch-license grant).
No real cache/compiler/sysroot input was approved or opened. Missing-file and
hash-mutation refusal with otherwise valid metadata are separately tested by
the synthetic suite. `git diff --check` passed (exit 0, no output).

The read-only pinned-checkout CI workflow runs only these tests and full
base-to-head whitespace checks. It never installs/builds dependencies, executes
ARM, uses credentials after checkout or uploads artifacts. CI success must be
reported separately from local tests and prior build evidence.

## Next separate C++14 ABI work (not performed here)

1. Obtain review of the prerequisite/rights scope and bind **existing** tiny02
   compiler/sysroot receipts to exact current paths/digests/native tool inventory,
   without repeating downloads or changing productive containers. If unavailable,
   report the specific missing receipt, not “builder absent”. Extend the manifest
   with reviewed C++ headers, libstdc++, libgcc and provider decisions.
2. In a separate branch add a tiny original exception/`std::string`/allocation
   probe and native host compile/run tests. No SDL, Ruby, mkxp-z or game assets.
3. Under a separately reviewed host-only build scope, use tiny02's existing GCC
   8.3 `g++` and Linux-4.9 sysroot for one private C++14 compile/link, capture actual
   includes/startup/link-map/runtime providers and repeat-link. Merely setting
   `--sysroot` does not isolate GCC's configured C++ include/libstdc++ searches.
4. Inspect (never execute) AArch64 ELF on host: interpreter, GNU kernel ABI,
   GLIBC/GLIBCXX/CXXABI imports and transitive libstdc++/libgcc provider requirements,
   NEEDED, RPATH, stack/TEXTREL and exact hashes. Do not reuse the C triangle's
   two-NEEDED/21-SDL contract or assume installed C++ providers are compatible.
   Static libstdc++ is not a shortcut around license/ABI review. Keep output private.

No C++14 compile, full engine build/import, device change, release, merge or issue
closure is included here. Rollback is branch removal only; no runtime state changed.

[PLAN]: https://github.com/almighty-atlas/nextui-mkxp/blob/91b5a27378150bb479fc8546f2bddb6c6e5b1da7/docs/H700_MINIMAL_ENGINE_PLAN.md
