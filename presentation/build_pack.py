"""Generate captions.srt from the segment list below (demo-script.md embeds the same segments; keep both in sync).
Usage: python presentation/build_pack.py  (from repo root). Stdlib only."""
import pathlib
root = pathlib.Path(__file__).resolve().parent
# (start_s, end_s, screen, narration)
SEG = [
 (0, 14, "Title card over architecture.png (fade in). Disclaimer strip: 'Synthetic research simulation only.'",
  "It started with a clip of two aircraft sharing one callsign. That raised a question: can an agent surface ambiguity, stale state, or a bad readback without becoming the safety authority? This is TowerOps. It is a synthetic research simulation, not air traffic control software."),
 (14, 34, "architecture.png, highlight the dashed proposal lane, then the teal trust boundary.",
  "The rule is simple. The model proposes; deterministic code decides. A proposal is bound to an exact hash of the world. To take effect it must pass a freshness check, a human approval fixture, and an acknowledgement fixture. Only then does the simulation change."),
 (34, 64, "Browser, 1280x900 explorer. Select 'Approval + acknowledgement', click Run, then drag the projected-time slider to 5 minutes.",
  "Here is the local explorer. Two fictional aircraft are converging, and the engine predicts a conflict. The advisory sets FIXTURE-B's north-south speed to two nautical miles a minute. Both fixtures arrive, the gates pass, and the projected conflict goes from true to false. Scrub the slider to compare the two constant-velocity paths."),
 (64, 88, "Scroll to Audit timeline: fixture_proposal, screen_pass, approval, ack, simulated_actuation. Zoom on the chain head line.",
  "Every step is in a hash-chained audit log: proposal, screen pass, approval, acknowledgement, and only then simulated actuation. Each event hashes the one before it."),
 (88, 122, "Change dropdown to 'Missing acknowledgement', Run. Show red 'Rejected - no simulated actuation', reason ack_missing, unchanged After panel, timeline ends in reject.",
  "Now the same scenario with the acknowledgement withheld. Approval alone is not enough. The engine rejects it with ack_missing, the world stays exactly as it was, and there is no actuation event in the log. The other six cases fail the same way: missing approval, late acknowledgement, stale observation, changed world hash, wrong advisory, and expired proposal."),
 (122, 150, "Click Export, then choose the file under 'Replay exported JSON' - show 'Replay MATCH'. Edit after.version in a copy, replay again - show 'Replay MISMATCH'.",
  "Any result can be exported and replayed. The backend re-runs the fixed inputs and compares the whole export. Change one field and it reports a mismatch. To be clear about what that proves: it is reproducibility under this engine. It is not a signature, and it is not authenticity."),
 (150, 170, "Terminal: python -m unittest -q test_explorer -> 'Ran 8 tests ... OK'. Cut to browser_acceptance.py JSON summary: two viewports, no page errors. Flash 390x844 mobile screenshot.",
  "We checked this. Eight tests cover all eight cases in every combination of fixture switches, and real HTTP requests. A Chromium acceptance run exercises the interface at desktop and phone sizes, including tampered replays."),
 (170, 180, "Closing card: repo name, branch, 'Synthetic research simulation - fixture identities, no real authority.'",
  "TowerOps: the model proposes, the gate decides, and everything is replayable. Synthetic data only."),
]
def ts(s, ms=0):
    return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d},{ms:03d}"
def cues():
    out = []
    n = 1
    for a, b, _, text in SEG:
        words = text.split(); chunks = []; cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 68 or w.endswith((".", "?")) and len(" ".join(cur)) > 30:
                chunks.append(" ".join(cur)); cur = []
        if cur: chunks.append(" ".join(cur))
        total = sum(len(c) for c in chunks); t = a * 1000
        for c in chunks:
            dur = int((b - a) * 1000 * len(c) / total)
            s, e = t, t + dur
            # wrap to two lines max of ~42 chars
            ws, lines, line = c.split(), [], ""
            for w in ws:
                if len(line) + len(w) + 1 > 42 and line:
                    lines.append(line); line = w
                else:
                    line = (line + " " + w).strip()
            lines.append(line)
            out.append(f"{n}\n{ts(s//1000, s%1000)} --> {ts(e//1000, e%1000)}\n" + "\n".join(lines) + "\n")
            n += 1; t = e
    return "\n".join(out)
(root / "captions.srt").write_text(cues())
def mmss(s): return f"{s//60}:{s%60:02d}"
rows = "\n".join(f"| {mmss(a)}-{mmss(b)} | {screen} | {text} |" for a, b, screen, text in SEG)
words = sum(len(t.split()) for *_, t in SEG)
print(words, "words", SEG[-1][1], "s", round(words / SEG[-1][1] * 60), "wpm")
