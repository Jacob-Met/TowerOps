# Ruff treatment of immutable receiving history

This directory keeps the exact receiving scripts executed during the scenario feature's earlier reviews. PR47's original published head is 9c6bef26bfef04f1eca264dec533e47e0f270aa8 (tree d5d9827824e0d6f79fc54e5565698dc5d5a783ce). All 216 historical evidence files stay byte-for-byte and mode-for-mode unchanged in the PR46 composition.

The published-tree lint run exposed 18 findings in six of those historical scripts. The adjacent .ruff.toml applies only the listed rule codes to those exact relative paths. It changes no source script, application setting, workflow, root configuration, rule selection, or whole-directory exemption.

| Historical path | Retained rule codes | Findings |
| --- | --- | ---: |
| composition-pr39-pr42/receivers/run-ci-browser-python.py | I001 | 1 |
| composition-pr39-pr42/receivers/run-ci-capture.py | I001, S102 | 2 |
| independent-review/bootstrap-current-r2.py | I001, F401, PLW1510 | 4 |
| independent-review/bootstrap-current.py | I001, F401, PLW1510 | 4 |
| independent-review/bootstrap-r2.py | I001, F401, PLW1510 | 3 |
| independent-review/bootstrap.py | I001, F401, PLW1510 | 4 |

I001 and F401 cover import ordering and unused imports in the executed historical files. Reformatting or deleting those imports would change the bytes their preserved receipts identify. PLW1510 covers subprocess calls whose receiving wrappers retain and inspect exit codes instead of raising immediately. S102 covers one exact historical CI-capture wrapper: it executes the original checked-in capture source after redirecting only the capture destination into its isolated output directory; the original capture predicates remain unchanged. None of these exceptions is an application permission or a statement that other findings are acceptable.

The exact current base, 8d4933f33a0f5e0673fa9d00002e8b29302a1c53, has no .ruff.toml, ruff.toml or pyproject.toml, and native Ruff discovery reports default settings. There is no repository config to extend. Therefore this nested config adds only lint.extend-per-file-ignores and retains Ruff 0.16.10 defaults. Full-tree receiving records compare application settings before/after and run the normal ruff check . gate separately from the earlier product-source-only qualifications. The original 18 findings and hosted failing job log are retained in the composition-pr46 companion.

[Ruff configuration discovery](https://docs.astral.sh/ruff/configuration/) and [extend-per-file-ignores](https://docs.astral.sh/ruff/settings/#lint_extend-per-file-ignores) document the path-specific scope. Any future repository-level Ruff configuration should be explicitly inherited here so that later settings are not shadowed.
