import './flight-register.css';
import type { Aircraft } from './core';
import { projectFlightRegister, type FlightRegisterOrder } from './flight-register-model';

interface FlightRow {
  row: HTMLDivElement;
  button: HTMLButtonElement;
  meta: HTMLSpanElement;
}

/** Search/order state belongs to this view, independently of the simulation and its drafts. */
export function createFlightRegister(root: HTMLElement, selectFlight: (id: string) => void) {
  const element = <T extends HTMLElement>(id: string) => {
    const node = root.querySelector<T>('#' + id);
    if (!node) throw new Error('Missing traffic register control: ' + id);
    return node;
  };
  const query = element<HTMLInputElement>('flight-filter');
  const order = element<HTMLSelectElement>('flight-order');
  const clear = element<HTMLButtonElement>('flight-filter-clear');
  const matches = element<HTMLParagraphElement>('flight-matches');
  const selection = element<HTMLParagraphElement>('flight-hidden-selection');
  const selectionText = element<HTMLSpanElement>('flight-hidden-selection-text');
  const showSelected = element<HTMLButtonElement>('flight-show-selected');
  const empty = element<HTMLParagraphElement>('flight-no-matches');
  const list = element<HTMLDivElement>('flight-list');
  const rows = new Map<string, FlightRow>();
  let aircraft: readonly Aircraft[] = [], selected = '', selectionDisabled = false;
  const setText = (node: HTMLElement, text: string) => {
    if (node.textContent !== text) node.textContent = text;
  };

  function paint() {
    const view = projectFlightRegister(aircraft, query.value, order.value as FlightRegisterOrder, selected);
    const currentIds = new Set(aircraft.map(flight => flight.aircraft_id));
    const visibleIds = new Set(view.aircraft.map(flight => flight.aircraft_id));
    const focused = document.activeElement instanceof HTMLButtonElement && list.contains(document.activeElement)
      ? document.activeElement : null;
    for (const [id, value] of rows) {
      if (!visibleIds.has(id)) value.row.remove();
      if (!currentIds.has(id)) rows.delete(id);
    }
    view.aircraft.forEach((flight, index) => {
      let value = rows.get(flight.aircraft_id);
      if (!value) {
        const row = document.createElement('div');
        const button = document.createElement('button');
        const meta = document.createElement('span');
        button.type = 'button';
        button.textContent = flight.aircraft_id;
        button.onclick = () => {
          if (!selectionDisabled && aircraft.some(current => current.aircraft_id === flight.aircraft_id)) {
            selectFlight(flight.aircraft_id);
          }
        };
        meta.className = 'flight-meta';
        row.append(button, meta);
        value = { row, button, meta };
        rows.set(flight.aircraft_id, value);
      }
      value.row.className = 'flight-row' + (selected === flight.aircraft_id ? ' selected' : '');
      value.button.disabled = selectionDisabled;
      value.button.setAttribute('aria-pressed', String(selected === flight.aircraft_id));
      setText(value.meta, Math.round(flight.altitude_ft / 100) + ' FL / ' + flight.vx_nm_min.toFixed(1) + ', ' + flight.vy_nm_min.toFixed(1) + ' NM/M');
      const existing = list.children[index] ?? null;
      if (existing !== value.row) list.insertBefore(value.row, existing);
    });
    // Reordering an existing DOM node can blur its button. Restore only that same,
    // still-visible button; typing, hidden flights and removed flights never gain focus.
    if (focused?.isConnected && !focused.disabled && document.activeElement !== focused) {
      focused.focus({ preventScroll: true });
    }
    setText(matches, view.aircraft.length + ' of ' + view.total + ' flights shown');
    clear.disabled = query.value.length === 0;
    empty.hidden = view.aircraft.length !== 0;
    selection.hidden = !view.selectedHidden;
    setText(selectionText, view.selectedHidden ? 'Selected ' + selected + ' is outside this search.' : '');
  }

  query.addEventListener('input', paint);
  order.addEventListener('change', paint);
  clear.addEventListener('click', () => {
    query.value = '';
    paint();
    query.focus();
  });
  showSelected.addEventListener('click', () => {
    if (!aircraft.some(flight => flight.aircraft_id === selected)) return;
    query.value = selected;
    paint();
    query.focus();
  });
  return {
    update(current: readonly Aircraft[], selectedId: string, disabled: boolean): void {
      aircraft = current;
      selected = selectedId;
      selectionDisabled = disabled;
      paint();
    },
  };
}
