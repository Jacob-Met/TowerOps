import { MAX_SCENARIO_BYTES, ScenarioFile, ScenarioSnapshot, parseScenario, serializeScenario } from './scenario-file';

interface ScenarioControls {
  capture: () => ScenarioSnapshot;
  context: () => readonly unknown[];
  available: () => boolean;
  load: (scenario: ScenarioFile) => void;
}
interface Review { scenario: ScenarioFile; context: readonly unknown[] }

export function connectScenarioFiles(options: ScenarioControls): { refresh: () => void } {
  const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const fileInput = get<HTMLInputElement>('scenario-file');
  const save = get<HTMLButtonElement>('save-scenario');
  const choose = get<HTMLButtonElement>('choose-scenario');
  const apply = get<HTMLButtonElement>('load-scenario');
  const cancel = get<HTMLButtonElement>('cancel-scenario');
  const panel = get('scenario-review');
  const status = get('scenario-status');
  let review: Review | null = null, reading: readonly unknown[] | null = null, epoch = 0;
  const urls = new Set<string>();
  const sameContext = (context: readonly unknown[]) => {
    const current = options.context();
    return current.length === context.length && current.every((value, index) => Object.is(value, context[index]));
  };
  function clear(message?: string): void {
    epoch++; review = null; reading = null; panel.hidden = true;
    cancel.hidden = true; apply.disabled = true; fileInput.value = '';
    if (message !== undefined) status.textContent = message;
  }
  function refresh(): void {
    const available = options.available();
    save.disabled = !available; choose.disabled = !available;
    get('scenario-availability').textContent = available
      ? 'Files stay on your device. Loading starts a fresh decision trace.'
      : 'Pause traffic or finish the active planner or flight edit before using scenario files.';
    const context = review?.context ?? reading;
    if (context && (!available || !sameContext(context))) {
      clear('The simulation changed. Choose the file again to review its replacement.');
    }
    apply.disabled = !review || !available;
  }
  function showReview(scenario: ScenarioFile, filename: string): void {
    get('scenario-summary').textContent =
      `${filename}: ${scenario.world.aircraft.length} aircraft, world version ${scenario.world.version}. Clock ${scenario.now} s; ${scenario.time_scale}× time scale; selected ${scenario.selected_aircraft_id}.`;
    const list = get('scenario-policy'); list.replaceChildren();
    const fields: [string, number, string][] = [
      ['Horizontal separation', scenario.policy.min_horizontal_nm, 'NM'],
      ['Vertical separation', scenario.policy.min_vertical_ft, 'FT'],
      ['Look-ahead', scenario.policy.horizon_min, 'MIN'],
      ['Recorded sample step', scenario.policy.sample_step_min, 'MIN'],
      ['Maximum state age', scenario.policy.max_state_age_sec, 'SEC'],
      ['Speed limit', scenario.policy.max_speed_nm_min, 'NM/MIN'],
      ['Climb limit', scenario.policy.max_climb_ft_min, 'FT/MIN'],
    ];
    for (const [label, value, unit] of fields) {
      const dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = label; dd.textContent = `${value} ${unit}`; list.append(dt, dd);
    }
    panel.hidden = false; cancel.hidden = false;
    status.textContent = 'Review the saved scenario. The current simulation is unchanged.';
    refresh(); get('scenario-review-title').focus();
  }
  async function readSelectedFile(): Promise<void> {
    const file = fileInput.files?.[0];
    if (!file) return;
    clear(); refresh();
    if (!options.available()) { status.textContent = 'Pause traffic or finish the active operation before choosing a scenario.'; return; }
    const ticket = epoch, context = [...options.context()];
    reading = context; cancel.hidden = false; status.textContent = 'Reading the selected scenario…';
    try {
      if (file.size > MAX_SCENARIO_BYTES) throw new Error('Scenario files must be at most 256 KiB.');
      const text = await file.text();
      if (ticket !== epoch) return;
      if (!options.available() || !sameContext(context)) { clear('The simulation changed while reading. Choose the file again.'); return; }
      const scenario = parseScenario(text);
      reading = null; review = { scenario, context }; showReview(scenario, file.name);
    } catch (error) {
      if (ticket !== epoch) return;
      clear(`NOT LOADED: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  choose.addEventListener('click', () => { refresh(); if (options.available()) fileInput.click(); });
  fileInput.addEventListener('change', () => void readSelectedFile());
  cancel.addEventListener('click', () => { clear('Import canceled. The current simulation is unchanged.'); choose.focus(); });
  apply.addEventListener('click', () => {
    refresh();
    if (!review || !options.available()) return;
    const scenario = review.scenario;
    clear();
    try {
      options.load(scenario);
      status.textContent = 'Scenario loaded with its saved policy. Traffic is paused and the decision trace starts empty.';
      choose.focus();
    } catch (error) {
      status.textContent = `NOT LOADED: ${error instanceof Error ? error.message : String(error)}`;
    }
  });
  save.addEventListener('click', () => {
    refresh(); if (!options.available()) return;
    try {
      const file = serializeScenario(options.capture());
      const url = URL.createObjectURL(new Blob([file.text], { type: file.mime }));
      urls.add(url);
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = file.filename;
      document.body.append(anchor);
      try { anchor.click(); } finally { anchor.remove(); }
      setTimeout(() => { URL.revokeObjectURL(url); urls.delete(url); }, 30000);
      status.textContent = 'Scenario file prepared. Check your browser downloads.';
    } catch (error) {
      status.textContent = `NOT SAVED: ${error instanceof Error ? error.message : String(error)}`;
    }
  });
  window.addEventListener('pagehide', () => { clear(); for (const url of urls) URL.revokeObjectURL(url); urls.clear(); });
  refresh();
  return { refresh };
}
