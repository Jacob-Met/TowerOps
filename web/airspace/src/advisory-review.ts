import { AdvisoryOptionsReview } from './advisory-options';

const PAGE_SIZE = 6;

/** A local view of native results; this module neither plans nor applies. */
export class AdvisoryReviewPanel {
  private review: AdvisoryOptionsReview | null = null;
  private currentHash: string | null = null;
  private blocked = false;
  private flight = '';
  private page = 0;
  private status = '';
  private readonly list: HTMLOListElement;
  private readonly filter: HTMLSelectElement;
  private readonly previous: HTMLButtonElement;
  private readonly next: HTMLButtonElement;

  constructor(private readonly root: HTMLElement, choose: (hash: string) => void) {
    this.list = root.querySelector<HTMLOListElement>('#advisory-options-list')!;
    this.filter = root.querySelector<HTMLSelectElement>('#advisory-flight-filter')!;
    this.previous = root.querySelector<HTMLButtonElement>('#advisory-options-previous')!;
    this.next = root.querySelector<HTMLButtonElement>('#advisory-options-next')!;
    this.filter.addEventListener('change', () => { this.flight = this.filter.value; this.page = 0; this.draw(); });
    this.previous.addEventListener('click', () => { this.page--; this.draw(); });
    this.next.addEventListener('click', () => { this.page++; this.draw(); });
    this.list.addEventListener('click', event => {
      const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-advisory-hash]');
      if (button && !button.disabled && !this.blocked) choose(button.dataset.advisoryHash!);
    });
  }

  open(): void { this.root.hidden = false; }

  update(review: AdvisoryOptionsReview | null, status: string, currentHash: string | null, blocked: boolean): void {
    if (review === this.review && status === this.status && currentHash === this.currentHash && blocked === this.blocked) return;
    if (review !== this.review) {
      this.page = 0;
      this.flight = '';
      this.filter.replaceChildren(new Option('All flights', ''));
      for (const flight of new Set(review?.advisories.map(a => a.aircraft_id) ?? [])) {
        this.filter.append(new Option(flight, flight));
      }
    }
    this.review = review;
    this.status = status;
    this.currentHash = currentHash;
    this.blocked = blocked;
    this.draw();
  }

  private draw(): void {
    this.root.querySelector('#advisory-options-status')!.textContent = this.status;
    this.root.querySelector('#advisory-options-count')!.textContent = this.review
      ? `${this.review.advisories.length} ADMITTED / ${this.review.candidate_count} CHECKED`
      : 'NO CURRENT REVIEW';
    const entries = (this.review?.advisories ?? []).map((advisory, index) => ({ advisory, rank: index + 1 }))
      .filter(({ advisory }) => !this.flight || advisory.aircraft_id === this.flight);
    const pages = Math.max(1, Math.ceil(entries.length / PAGE_SIZE));
    this.page = Math.max(0, Math.min(this.page, pages - 1));
    this.filter.disabled = this.blocked || !this.review?.advisories.length;
    this.previous.disabled = this.blocked || this.page === 0;
    this.next.disabled = this.blocked || this.page + 1 >= pages;
    this.root.querySelector('#advisory-options-page')!.textContent = entries.length
      ? `Showing ${this.page * PAGE_SIZE + 1}–${Math.min((this.page + 1) * PAGE_SIZE, entries.length)} of ${entries.length}`
      : 'No options to select';
    this.list.replaceChildren();
    for (const { advisory, rank } of entries.slice(this.page * PAGE_SIZE, (this.page + 1) * PAGE_SIZE)) {
      const row = document.createElement('li');
      const current = advisory.advisory_hash === this.currentHash;
      row.className = `advisory-option${current ? ' current' : ''}`;
      row.dataset.advisoryHash = advisory.advisory_hash;
      row.value = rank;
      const heading = document.createElement('h3');
      heading.textContent = `${String(rank).padStart(2, '0')} / ${advisory.aircraft_id}`;
      const preference = document.createElement('p');
      preference.className = 'advisory-option-priority';
      preference.textContent = rank === 1 ? 'First in native planner order' : 'Native planner alternative';
      const values = document.createElement('dl');
      for (const [label, value] of [
        ['East velocity · NM/min', advisory.set_vx_nm_min],
        ['North velocity · NM/min', advisory.set_vy_nm_min],
        ['Climb · ft/min', advisory.set_climb_ft_min],
      ] as const) {
        const term = document.createElement('dt'), detail = document.createElement('dd');
        term.textContent = label; detail.textContent = String(value); values.append(term, detail);
      }
      const exact = document.createElement('details'), summary = document.createElement('summary'), body = document.createElement('pre');
      summary.textContent = 'Exact proposal and hash';
      body.textContent = JSON.stringify(advisory, null, 2);
      exact.append(summary, body);
      const button = document.createElement('button');
      button.className = `button button-wide ${current ? 'button-quiet' : 'button-primary'}`;
      button.dataset.advisoryHash = advisory.advisory_hash;
      button.textContent = current ? 'Current proposal' : 'Use this proposal';
      button.setAttribute('aria-label', `${current ? 'Current' : 'Use'} proposal ${rank} for ${advisory.aircraft_id}`);
      button.disabled = this.blocked || current;
      row.append(heading, preference, values, exact, button);
      this.list.append(row);
    }
  }
}
