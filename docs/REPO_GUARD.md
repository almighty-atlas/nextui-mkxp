# Repository guard (#9)

Status: **verified-on-host**. The integrated root test suite is also executed
by the existing H700 probe workflows: it includes the guard's negative fixtures
and a guard run against the repository index. The dedicated job remains an
inactive template at `.github/workflow-templates/repo-guard.yml`; it is not
required for those already active checks. No credential scope was expanded.

`scripts/repo_guard.py` is a dependency-free Python 3 script. It reads only
the **Git index**: tracked files plus anything staged with `git add`, exactly
as it would be committed. Worktree edits that are not staged are ignored.
It uses no network, credentials, game downloads or privileges.

```sh
python3 scripts/repo_guard.py          # text: FAIL <RULE> '<path>' ... REPO_GUARD=PASS|FAIL
python3 scripts/repo_guard.py --json   # {"schema": 1, "files": N, "findings": [...]}
python3 -m unittest discover -s tests -v
```

Exit codes: `0` pass, `1` findings, `2` not a readable Git repository.
Findings contain only a rule ID and the quoted path, **never file contents**,
so a leaked key or game text is not echoed into terminals or CI logs.

## Rules

| Rule | Trigger |
| --- | --- |
| `GAME_DATA_OR_ROM` | RGSS data/archives (`.rxdata`, `.rvdata*`, `.rgss*a`), RPG Maker project/MV assets, saves (`.sav`, `.srm`), ROM/disc images |
| `GAME_EXECUTABLE_OR_CONFIG` | `Game.exe`, `Game.ini`, official RGSS DLL names |
| `GAME_MEDIA` | Audio files (`.ogg`, `.mid`, `.wav`, `.mp3`, …) |
| `GAME_DIRECTORY` | Any path below `games/`, `game-data/`, `user-games/`, `roms/`, `saves/`, `rtp/` (case-insensitive) |
| `RMXP_ASSET_DIRECTORY` | Paths below `Graphics/` or `Audio/` outside `tests/` |
| `ARCHIVE_OR_WINDOWS_BINARY` | `.zip`, `.7z`, `.rar`, tarballs, `.exe`, `.dll` |
| `ELF_BINARY`, `PE_BINARY`, `MACHO_BINARY` | Executable magic bytes, regardless of name |
| `ZIP_ARCHIVE`, `7Z_ARCHIVE`, `RAR_ARCHIVE`, `XZ_ARCHIVE`, `GZIP_ARCHIVE`, `RGSS_ARCHIVE`, `RUBY_MARSHAL` | Archive or Ruby Marshal (`.rxdata`) magic bytes, regardless of name |
| `FILE_TOO_LARGE` | Blob larger than 256 KiB |
| `PRIVATE_KEY`, `GITHUB_TOKEN`, `AWS_ACCESS_KEY`, `SLACK_TOKEN`, `GENERIC_API_KEY` | Well-known secret formats |
| `CREDENTIAL_FILE` | `.env`, `id_rsa`, `id_ed25519`, `.pem`, `.key`, `.p12` |
| `SYMLINK`, `SUBMODULE` | Symlinks or gitlinks in the index |
| `REQUIRED_FILE_MISSING` | README, AGENTS, ROADMAP, ARCHITECTURE, TEST_PLAN, COMPATIBILITY or `.gitignore` missing |
| `BROKEN_MARKDOWN_LINK` | Relative Markdown link to a path not in the index, or escaping the repository |
| `INVALID_JSON` | Unparseable `.json` manifest |
| `SHELL_SYNTAX` | `sh -n` fails for `*.sh` or `#!/bin/sh` scripts |

`.gitignore` additionally covers RGSS2/3 data, common ROM/save formats,
`saves/`, `RTP/` and private key files. Ignoring is only a convenience;
`git add -f` bypasses it, which is why the guard checks the index directly.

## Optional local hook

Not installed automatically. To opt in for a local clone:

```sh
printf '#!/bin/sh\nexec python3 -I scripts/repo_guard.py\n' > .git/hooks/pre-commit
chmod 755 .git/hooks/pre-commit
```

## Limitations

- Heuristic. A renamed text-encoded asset, an unlisted token format or an
  image outside `Graphics/` will not be detected. Review remains mandatory.
- Checks the current index only, not history. Purging a previously committed
  file requires a separate, explicitly approved history rewrite.
- Paths and magic bytes are not legal provenance checks; see `docs/SOURCES.md`.
- A PASS does **not** imply engine build success or H700 runtime compatibility.

## Verification (2026-10-29)

- 9 host fixture tests PASS (Python 3, temporary Git repositories, synthetic
  data only). Every failing fixture contains a sentinel string that the tests
  assert is absent from all guard output.
- `main` at `107db13` and the open candidate branches for #6 (two), #7, #8,
  #10, #11 and #38 all PASS with zero findings, i.e. no false positives on
  existing tracked content.
- Not executed in GitHub Actions (blocked, see above).
