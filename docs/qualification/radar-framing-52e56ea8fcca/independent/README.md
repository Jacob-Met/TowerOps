# Independent drawing-coordinate receiving

Root wrote the nine-case Canvas-command receiver before inspecting the candidate implementation. The exact source-bound Node v24.19.0 execution improved from **5/9 on unchanged baseline** to **9/9 on the exact radar v1 candidate**. This uses a recording Canvas adapter and actual TypeScript draw/core/helper source. It does not claim native browser rasterization; the separate author packet records real Chrome receiving.

The cases cover several common translations (zero per-marker coordinate delta), order independence, east/right and north/up with equal-axis scale, current/projected point visibility, absolute ticks bound to their grid lines, rings at true world origin, empty/single/coincident finite drawing, explicit finite-overflow refusal, and a collapsed canvas. Inputs are deep-frozen and checked for mutation.

The receiver body SHA256 is 7173fc939e43ec84b693bd2e76fdda91541f40203f89ddc486826d2bab8a4ee5. Both executions used the same body. The source bindings and raw tool outputs are included. Source-core SHA256 is 4f705e060ec70735c2687c7f27ccefb4f070a699352a974b4436ebf693b615ac; exact drawing/helper hashes appear in each result.

The initial loader failed before executing any case: Node's stripTypeScriptTypes retains mixed imports of interfaces. The corrected loader removes only imported names explicitly declared as exported interfaces/types in the exact dependency source. Candidate product bytes and receiver assertions were unchanged. The initial tool output had already been truncated when returned; initial-loader-failure.json preserves precisely that returned result, not a claim of complete stderr.

## Reproduce

Using Node v24.19.0:

~~~sh
node run.cjs source-baseline.json
node run.cjs source-candidate.json
~~~

The first command is expected to report five passes and four behavioral failures; the second nine passes. Node emits its experimental type-stripping warning. The small run.cjs wrapper reconstructs the same injected SOURCE/PIN bindings used by the original executions; no production source is rewritten.

The author's frozen native archive remains immutable. These independent receipts are an additional packet. Integration and public deployment remain separate gates.
