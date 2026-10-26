Original MIT fixtures from PR #23 commit `60721c1a81a9f54e507650f313a479ecaa9b6d2a`, `spikes/h700-video/`.

`triangle-original.c` is byte-identical to the pinned source. Headers and mock implementation are original mock API declarations, adapted here for proc lookups/profile checks; they are not SDL/Khronos or vendor headers. The experimental C variant is generated in private temporary directories. Retain LICENSE; it does not clear linked SDL/vendor dependencies.
