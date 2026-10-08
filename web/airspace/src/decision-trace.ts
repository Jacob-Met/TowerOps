import './decision-trace.css';

export const MAX_TRACE_BYTES = 2 * 1024 * 1024;

export interface DecisionTraceReport {
  chain_valid: boolean;
  ok: boolean;
  event_count: number;
  advisories: Array<{
    advisory_hash: unknown;
    screen_seq: number | null;
    screen_world_hash: unknown;
    approval_seq: number | null;
    approver: unknown;
    ack_seq: number | null;
    actuations: Array<{seq: number; before_world_hash: unknown; after_world_hash: unknown}>;
    issues: string[];
  }>;
  rejects: Array<{seq: number; reason: unknown}>;
  issues: string[];
}

interface DecisionTraceOptions {
  getCurrentTrace: () => string;
  reviewTrace: (raw: string) => Promise<DecisionTraceReport>;
}

export function checkTraceSize(raw: string): void {
  if (new TextEncoder().encode(raw).byteLength > MAX_TRACE_BYTES) {
    throw new Error('This trace exceeds the 2 MiB browser review limit.');
  }
}

// Do not parse and stringify the audit in JavaScript: its native JSON number
// spellings are part of the input to Python's canonical hash verification.
export function traceDownload(raw: string): Blob {
  return new Blob([raw], {type: 'application/json;charset=utf-8'});
}

function display(value: unknown): string {
  if (value === null || value === undefined) return 'Not recorded';
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function eventLabel(seq: number | null): string {
  return seq === null ? 'Not recorded' : `Event ${seq}`;
}

function countLabel(count: number, singular: string, plural = singular + 's'): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function addText(parent: HTMLElement, tag: 'p' | 'li' | 'h4', value: string): HTMLElement {
  const node = document.createElement(tag);
  node.textContent = value;
  parent.append(node);
  return node;
}

function showReport(target: HTMLElement, report: DecisionTraceReport, source: string): void {
  target.replaceChildren();
  const verdict = !report.chain_valid ? 'chain-invalid' : !report.ok ? 'semantic-invalid' : report.event_count ? 'valid' : 'empty';
  target.dataset.verdict = verdict;
  addText(target, 'h4', !report.chain_valid ? 'Hash chain invalid' : !report.ok ? 'Decision sequence has issues' : report.event_count ? 'Recorded decision sequence checks passed' : 'Empty trace');
  addText(target, 'p', `${source} · ${countLabel(report.event_count, 'event')} · ${countLabel(report.advisories.length, 'advisory', 'advisories')} · ${countLabel(report.rejects.length, 'rejection')}`);
  addText(target, 'p', `Hash chain: ${report.chain_valid ? 'valid' : 'invalid'}. Decision sequence: ${!report.chain_valid ? 'not reviewed because the chain is invalid' : report.ok ? 'checks passed' : 'issues found'}.`);
  if (!report.event_count) addText(target, 'p', 'No recorded decisions to review.');
  if (report.issues.length) {
    const issues = document.createElement('ul');
    issues.className = 'decision-trace-issues';
    for (const issue of report.issues) addText(issues, 'li', issue);
    target.append(issues);
  }
  for (const advisory of report.advisories) {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = `Advisory ${display(advisory.advisory_hash)} · ${advisory.actuations.length} actuation${advisory.actuations.length === 1 ? '' : 's'}${advisory.issues.length ? ' · issues found' : ''}`;
    details.append(summary);
    const steps = document.createElement('dl');
    for (const [label, value] of [
      ['Screened', eventLabel(advisory.screen_seq)],
      ['Approval', `${eventLabel(advisory.approval_seq)} · ${display(advisory.approver)}`],
      ['Readback', eventLabel(advisory.ack_seq)],
      ['Screened world', display(advisory.screen_world_hash)],
    ]) {
      const term = document.createElement('dt'), description = document.createElement('dd');
      term.textContent = label!; description.textContent = value!; steps.append(term, description);
    }
    details.append(steps);
    for (const actuation of advisory.actuations) {
      addText(details, 'p', `${eventLabel(actuation.seq)} · simulated actuation`);
      addText(details, 'p', `Before world: ${display(actuation.before_world_hash)}`);
      addText(details, 'p', `After world: ${display(actuation.after_world_hash)}`);
    }
    target.append(details);
  }
  if (report.rejects.length) {
    const heading = addText(target, 'h4', 'Recorded rejections');
    heading.className = 'decision-trace-rejections';
    const list = document.createElement('ol');
    for (const rejection of report.rejects) addText(list, 'li', `${eventLabel(rejection.seq)} · ${display(rejection.reason)}`);
    target.append(list);
  }
}

export function initializeDecisionTrace(options: DecisionTraceOptions): {setBusy: (busy: boolean) => void} {
  const find = <T extends HTMLElement>(id: string): T => {
    const node = document.getElementById(id);
    if (!node) throw new Error(`Missing decision trace control: ${id}`);
    return node as T;
  };
  const current = find<HTMLButtonElement>('review-current-trace');
  const download = find<HTMLButtonElement>('download-current-trace');
  const openedButton = find<HTMLButtonElement>('review-opened-trace');
  const file = find<HTMLInputElement>('open-trace-file');
  const feedback = find('decision-trace-feedback');
  const openedLabel = find('decision-trace-file');
  const result = find('decision-trace-result');
  let hostBusy = false, reviewing = false, reading = false, fileTicket = 0;
  let opened: {raw: string; name: string} | null = null;

  function availability(): void {
    current.disabled = hostBusy || reviewing;
    openedButton.disabled = hostBusy || reviewing || reading || !opened;
    file.disabled = hostBusy || reviewing;
    download.disabled = hostBusy;
  }

  async function review(raw: string, source: string): Promise<void> {
    if (hostBusy || reviewing) return;
    reviewing = true;
    result.replaceChildren(); delete result.dataset.verdict;
    feedback.textContent = `Reviewing ${source}…`;
    availability();
    try {
      checkTraceSize(raw);
      const report = await options.reviewTrace(raw);
      showReport(result, report, source);
      feedback.textContent = `Review complete for ${source}. Reviewing does not apply decisions or replace the live trace.`;
    } catch (error) {
      feedback.textContent = `NOT REVIEWED: ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      reviewing = false;
      availability();
    }
  }

  current.addEventListener('click', () => void review(options.getCurrentTrace(), 'current trace snapshot'));
  openedButton.addEventListener('click', () => {
    if (opened) void review(opened.raw, opened.name);
  });
  download.addEventListener('click', () => {
    if (hostBusy) return;
    const url = URL.createObjectURL(traceDownload(options.getCurrentTrace()));
    const link = document.createElement('a');
    link.href = url; link.download = 'towerops-decision-trace.json';
    document.body.append(link); link.click(); link.remove();
    // Keep the URL alive until the browser has started consuming the download.
    setTimeout(() => URL.revokeObjectURL(url), 0);
    feedback.textContent = 'Current trace downloaded. Open the JSON file here to review it later.';
  });
  file.addEventListener('change', () => {
    const ticket = ++fileTicket, selectedFile = file.files?.[0];
    opened = null;
    openedLabel.textContent = 'No trace file opened.';
    if (!selectedFile) {reading = false; availability(); return;}
    reading = true; availability();
    void (async () => {
      try {
        if (selectedFile.size > MAX_TRACE_BYTES) throw new Error('This file exceeds the 2 MiB browser review limit.');
        const raw = await selectedFile.text();
        if (ticket !== fileTicket) return;
        checkTraceSize(raw);
        opened = {raw, name: selectedFile.name};
        openedLabel.textContent = `Opened: ${selectedFile.name}`;
        feedback.textContent = 'File ready. Review opened trace reads its history without loading aircraft or applying decisions.';
      } catch (error) {
        if (ticket === fileTicket) feedback.textContent = `NOT OPENED: ${error instanceof Error ? error.message : String(error)}`;
      } finally {
        if (ticket === fileTicket) {reading = false; availability();}
      }
    })();
  });
  availability();
  return {setBusy: busy => {hostBusy = busy; availability();}};
}
