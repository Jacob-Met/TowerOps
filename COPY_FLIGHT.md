# Copy a selected flight

Use **Shape the traffic → Copy [callsign] into a new flight** to reuse a trajectory while placing another independent flight in a synthetic scenario. Select the source in the traffic register first.

1. Starting a copy pauses traffic and proposes an unused callsign.
2. Enter the new callsign and relative east, north and altitude offsets. Positive values move east, north and up; negative values move west, south and down. Horizontal offsets use nautical miles and altitude offsets use feet.
3. Choose **Preview copy**. Review the resulting position, exact velocity and climb, and current versus copied-world conflict intervals.
4. Choose **Add reviewed flight** to append one new flight, or **Cancel copy** to leave the simulation unchanged.

The copy keeps the source's velocity components and climb exactly. It does not convert through rounded bearing, speed or flight-level controls. The original flight and other tracks remain unchanged and retain their order. For example, a source at east 3.125 NM, north -4.75 NM and 12,345 FT with offsets +2.5 NM, -3.25 NM and +1,500 FT produces a new flight at 5.625 NM, -8 NM and 13,845 FT.

A preview or cancellation preserves the existing world, pending proposal and approval, decision trace, manual flight-builder fields, and raw JSON draft. Adding advances the world version once, selects the new callsign and clears the previous proposal and approval. It retains the decision trace and both drafts. Run the planner again, then approve and accept a fresh readback for the changed world.

Other controls remain available. Changing the world, selection, clock, policy, time scale or approval context retires the copy review; start a new copy from the current selection. Editing a copy field requires another preview. Finish the existing selected-flight edit or active planner operation before starting a copy.

Callsigns normalize to uppercase and must contain 1–10 letters, digits, underscores or hyphens. The callsign must be unused. Offsets and resulting position must be finite, the final altitude cannot be negative, and the copied world must contain at most 60 flights. Its nonnegative version must be exactly incrementable as a JavaScript safe integer. Conflict times in the preview are rounded for display; the existing continuous conflict calculation decides the intervals.

This is scenario authoring. A preview can deliberately introduce conflicts, and it is not an operational clearance or a guarantee that the planner can resolve every authored world.
