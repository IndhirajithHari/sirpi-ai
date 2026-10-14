# Sirpi source provenance

Sirpi is derived from Taiga-S1 by Shiv Shanmugam.

- Source: https://github.com/shhivv/taiga-s1
- Pinned revision: `84fdd19c487658a59805531fa306fa40e8f72555`
- Retrieval date: 2026-10-13
- Original weights: https://huggingface.co/shhivv/taiga-s1
- License: MIT; original copyright preserved in `LICENSE` and `release/hf/LICENSE`.

The source and released Taiga weights were imported from the pinned revision.
Sirpi adds a distribution name, CLI, CPU inference check, GUI rollout client,
Windows launcher, macro, boundary tests and documentation. The shared GUI
server banner now says Sirpi. Model parameters, training metadata, action
vocabulary, protocol and core module names preserve upstream compatibility.
Six POSIX-only watchdog tests are explicitly skipped on Windows; their runtime
implementation is unchanged and outside the Sirpi GUI launcher.

Git pack transfers stalled, so this snapshot was downloaded from GitHub's
raw-file endpoint at the pinned revision. Upstream history is not included.
Large demo assets, old checkpoints, the visualization project and Mesa weights
were excluded.
