# H700 offline environment identity (#4)

The old runner checks the compiler archive, one native Ruby executable and the
sysroot receipt. That does not bind the **extracted** compiler/linker, headers,
native standard library or SDL. `scripts/h700_environment.py` records those
complete trees and all container packages without installing/downloading inputs
or executing target code. This is identity verification, not source rebuilding.

## Contract and use

Relative-tree-v1 binds relative names, file SHA-256 and execute bits, directories
(including empty ones) and literal internal link targets. `.git` metadata and
mtimes are excluded. Special files, escaping links, symlink roots, empty trees
and control-character paths are refused. Roots must remain quiescent: this is
not a sandbox for malicious concurrent filesystem writers.

The fixed tools image is inspected only for ID/OS/architecture and its sorted
Debian package list. No environment or credential dump occurs. Package inspection
uses read-only rootfs, caller UID/GID, no network/capabilities, no-new-privileges,
2 CPUs / 4 GiB and `--pull=never`. Component measurements before/after must agree.
Capture never overwrites; verify compares the entire trusted reference receipt.

```sh
python3 scripts/h700_environment.py capture \
  --toolchain "$TOOLCHAIN" --sysroot "$SYSROOT" --native "$NATIVE_RUBY_PREFIX" \
  --sdl "$SDL_PREFIX" --compiler-archive "$COMPILER_ARCHIVE" \
  --receipt /private/environment.json

# Run before/after a rebuild. Never recapture just to hide drift:
python3 scripts/h700_environment.py verify \
  --toolchain "$TOOLCHAIN" --sysroot "$SYSROOT" --native "$NATIVE_RUBY_PREFIX" \
  --sdl "$SDL_PREFIX" --compiler-archive "$COMPILER_ARCHIVE" \
  --receipt /private/environment.json
```

Use the reviewed **staged SDL prefix**, not a raw build run containing tool links
outside its root. Exit 0 means recorded/matched, exit 2 blocked. The full receipt
stays private; stdout contains only status/code/hash, never input contents or
absolute paths. This standalone tool does not silently change the historical
configure driver's input contract.

## Verification (2026-10-29, verified-on-host)

- Real capture then independent verify: `ENVIRONMENT_RECORDED`, `ENVIRONMENT_MATCH`.
- 217 package versions and 9,542 component entries bound to a private receipt:
  `016220abd4e4c52d456c3431d7cbe16886f33babe95513ec324506ee99629237`.
- [Sanitized fingerprints](../build/h700-engine/environment-identity-evidence.json).
- 12 synthetic tests: compiler drift despite archive equality, other component
  drift, execute bits/directories/links, relocation, FIFO safety, outward/root
  links, package/image drift, bad archive before Docker, concurrent modification,
  no-overwrite/privacy and container isolation.

## Exact remaining bootstrap blocker

The existing tools Dockerfile begins with `FROM nextui-mkxp-builder:local`.
That private base has ID
`sha256:eb1d35cbd58c4b6e2be9697c40d7ea11730282188fcdb6122212809ad21ebfe3`;
its complete publicly rebuildable recipe is not in this repository. A dated
Debian snapshot in the outer recipe does not reconstruct the base.

To finish #4: reconstruct a reviewed recipe from a public immutable base, pin
package source/version closure and rebuild it in a fresh private environment.
Rebuild native Ruby, toolchain/sysroot and SDL using their pinned recipes and
retain their receipts. Do not publish private images or third-party binaries
to fill this gap. Current results remain `clean_room_rebuild=NOT_VERIFIED` and
`distribution=BLOCKED`. Knight Blade's private playability remains **100%**.
