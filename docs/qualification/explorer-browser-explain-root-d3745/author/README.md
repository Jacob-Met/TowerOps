# Explorer browser explanation — author controls

This root-authored increment adds an explicit **Explain this mismatch** action to the current saved-file replay and an additive `/api/replay/explain` route. The route calls the maintained `replay_explain.explain_replay`; the ordinary replay route, engine and scenario bodies stay unchanged. The action compares the already accepted parsed selection. It displays complete typed expected/actual values and missing-side envelopes as literal text, retains the original verdict and displayed run, and retires details on every new or cleared selection.

## Source and author execution

Base: `6991198cde605b683331290c8c898ac5dbec6643` / tree `bf63ce7b3ac761bf02c9184747575f989a2876ab`. `candidate-packet-v1.json` contains the exact twelve-file runtime/test projection, with byte, SHA-256, Git-blob and mode bindings. Source publication selects eight changed/new paths; the remaining helper, scenarios, engine and existing Python controls are unchanged bindings.

`author-course-v1.py` checked packet identity before reconstructing an exclusive candidate directory on the authorized ThinkPad. Native PID 4104523 completed with exit 0. Its five commands passed 31 test executions: four actual HTTP tests normally, the same four under actual Python `-O`, five new Node presentation tests, ten existing selection Node tests, and eight existing Python Explorer controls. The Node presentation controls use a controlled DOM/fetch; Loom's separate receiving evidence covers the actual browser and production HTTP path.

`author-receipt-v1.json` is the complete 16,898-byte native receipt, SHA-256 `c1c9a909273cfd9a7826d406351998ed5238462b17adb473aea942a8280bcd80`. All twelve projected source files retained their exact bytes/modes. Every subprocess argv, exit, complete stdout and stderr is retained in that receipt with byte and SHA-256 bindings. Published `streams-v1/` files are exact aliases of those original native streams. Cloud aliases were reconstructed from the receipt's complete captured UTF-8 fields and independently checked against their hashes; this extraction is not a new execution.

The candidate packet was frozen before this course. The complete independent browser criteria/driver were frozen separately before candidate exposure. Anvil's distinct source and harness reviews are read-only reviews, not additional runtime runs. The original browser receipt with a premature socket-count failure is preserved unchanged beside its explicit later closure audit and narrowly versioned driver; it must not be rewritten as a passing original receipt.

## Focused developer commands

Run these from the repository root:

```sh
python3 -B -m unittest discover -s tests -p 'test_explorer_explanation_http.py' -v
python3 -O -B -m unittest discover -s tests -p 'test_explorer_explanation_http.py' -v
node tests/test_explorer_explanation.cjs
node tests/test_explorer_replay_selection.cjs
python3 -B -m unittest test_explorer -v
```

No GitHub Actions were requested. This is local synthetic comparison evidence; it does not establish real-world aviation behavior, file provenance, causal explanation, or preservation of the browser input's original JSON spelling/bytes.
