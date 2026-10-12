import { SafetyPolicy, WorldState } from './core';
import { TrackCopyInput, TrackCopyPreview, TrackCopySession, applyTrackCopy, beginTrackCopy, previewTrackCopy } from './track-copy';

interface CopyControls {
  capture: () => { world: WorldState; policy: SafetyPolicy; now: number; selected: string };
  context: () => readonly unknown[];
  available: () => boolean;
  paused: () => boolean;
  pause: () => void;
  commit: (world: WorldState, selected: string) => void;
}

export function connectTrackCopy(options: CopyControls): { refresh: () => void } {
  const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const start = get<HTMLButtonElement>('copy-selected-track');
  const panel = get('track-copy-panel'), status = get('track-copy-status'), result = get('track-copy-preview');
  const previewButton = get<HTMLButtonElement>('preview-track-copy'), apply = get<HTMLButtonElement>('apply-track-copy');
  const fields = ['copy-callsign', 'copy-east', 'copy-north', 'copy-altitude'];
  let session: TrackCopySession | null = null, preview: TrackCopyPreview | null = null;
  let context: readonly unknown[] = [];
  const sameContext = () => {
    const current = options.context();
    return current.length === context.length && current.every((value, index) => Object.is(value, context[index]));
  };
  function clear(message: string): void {
    session = null; preview = null; context = []; panel.hidden = true; result.replaceChildren();
    apply.disabled = true; status.textContent = message;
  }
  function refresh(): void {
    const selected = options.capture().selected;
    start.textContent = `Copy ${selected} into a new flight`;
    start.disabled = !options.available();
    if (session && (!options.available() || !options.paused() || !sameContext())) {
      clear('The simulation changed. Start a fresh copy of the selected flight.');
    }
    previewButton.disabled = !session;
    apply.disabled = !session || !preview;
  }
  const input = (): TrackCopyInput => ({
    aircraft_id: get<HTMLInputElement>('copy-callsign').value,
    east_nm: get<HTMLInputElement>('copy-east').valueAsNumber,
    north_nm: get<HTMLInputElement>('copy-north').valueAsNumber,
    altitude_ft: get<HTMLInputElement>('copy-altitude').valueAsNumber,
  });
  function show(value: TrackCopyPreview): void {
    result.replaceChildren();
    const aircraft = value.world.aircraft[value.world.aircraft.length - 1]!;
    const description = document.createElement('p');
    description.textContent = `${aircraft.aircraft_id}: east ${aircraft.x_nm} NM, north ${aircraft.y_nm} NM, ${aircraft.altitude_ft} FT; vector ${aircraft.vx_nm_min} / ${aircraft.vy_nm_min} NM/M, climb ${aircraft.climb_ft_min} FT/M.`;
    const count = document.createElement('p');
    count.textContent = `${value.before.length} current → ${value.after.length} copied-world conflict pairs. All original flights remain unchanged.`;
    result.append(description, count);
    const table = document.createElement('table'), caption = document.createElement('caption');
    caption.textContent = 'Projected conflict intervals'; table.append(caption);
    const head = table.createTHead().insertRow();
    for (const label of ['Pair', 'Current interval', 'With copy']) {
      const th = document.createElement('th'); th.scope = 'col'; th.textContent = label; head.append(th);
    }
    const key = (w: TrackCopyPreview['before'][number]) => `${w.aircraft_a} / ${w.aircraft_b}`;
    const before = new Map(value.before.map(w => [key(w), w])), after = new Map(value.after.map(w => [key(w), w]));
    const interval = (w: TrackCopyPreview['before'][number] | undefined) => w ? `T+${w.start_min.toFixed(2)}–${w.end_min.toFixed(2)} min` : 'None';
    const body = table.createTBody();
    for (const pair of [...new Set([...before.keys(), ...after.keys()])].sort()) {
      const row = body.insertRow(), th = document.createElement('th'); th.scope = 'row'; th.textContent = pair; row.append(th);
      row.insertCell().textContent = interval(before.get(pair)); row.insertCell().textContent = interval(after.get(pair));
    }
    if (before.size || after.size) result.append(table);
    const note = document.createElement('p');
    note.textContent = 'This changes the synthetic scenario. After adding, run the planner before approval and readback. Displayed conflict times are rounded.';
    result.append(note);
  }
  start.addEventListener('click', () => {
    refresh(); if (!options.available()) return;
    try {
      options.pause();
      const current = options.capture();
      session = beginTrackCopy(current.world, current.selected, current.policy, current.now);
      context = [...options.context()]; preview = null; result.replaceChildren();
      let suffix = 2, id: string;
      do { const tail = String(suffix++); id = current.selected.slice(0, 10 - tail.length) + tail; }
      while (current.world.aircraft.some(a => a.aircraft_id === id));
      get<HTMLInputElement>('copy-callsign').value = id;
      get<HTMLInputElement>('copy-east').value = '0'; get<HTMLInputElement>('copy-north').value = '0';
      get<HTMLInputElement>('copy-altitude').value = '1000';
      get('track-copy-source').textContent = `Copying ${current.selected}. Offsets are relative to its current position; its velocity and climb stay exact.`;
      panel.hidden = false; status.textContent = 'Traffic is paused. Change the callsign and offsets, then preview before adding.';
      refresh(); get('copy-callsign').focus();
    } catch (error) { clear(`NOT COPYING: ${error instanceof Error ? error.message : String(error)}`); }
  });
  for (const id of fields) get(id).addEventListener('input', () => {
    preview = null; result.replaceChildren(); status.textContent = 'Fields changed. Preview again before adding.'; refresh();
  });
  previewButton.addEventListener('click', () => {
    refresh(); if (!session) return;
    try {
      const current = options.capture();
      preview = previewTrackCopy(session, input(), current.world, current.policy, current.now); show(preview);
      status.textContent = 'Copy preview ready. Review the resulting track and conflict intervals, then add or cancel.';
    } catch (error) { preview = null; result.replaceChildren(); status.textContent = `NOT PREVIEWED: ${error instanceof Error ? error.message : String(error)}`; }
    refresh();
  });
  apply.addEventListener('click', () => {
    refresh(); if (!session || !preview) return;
    try {
      const current = options.capture();
      const next = applyTrackCopy(session, preview, input(), current.world, current.policy, current.now);
      const id = next.aircraft[next.aircraft.length - 1]!.aircraft_id;
      clear(`${id} added at world version ${next.version}. Previous proposals cleared; decision trace retained. Run the planner again.`);
      options.commit(next, id); start.focus();
    } catch (error) { preview = null; status.textContent = `NOT ADDED: ${error instanceof Error ? error.message : String(error)}`; refresh(); }
  });
  get('cancel-track-copy').addEventListener('click', () => {
    clear('Copy canceled. World and pending proposal retained; traffic remains paused.'); start.focus();
  });
  return { refresh };
}
