/** Pure logic for the trace replay: a timeline from a stored trace, text highlighting, and the
 * plain-language account of the judge's verdict. No data is created here; every sentence is built
 * from fields of the exported trace. */

import type { DefenseEvent, Trace, TraceStep } from "./data";

export interface TimelineStep {
  /** Short label shown on the card and announced to screen readers. */
  label: string;
  kind: "user" | "assistant" | "tool" | "final" | "verdict";
  step?: TraceStep;
}

function argsText(args: Record<string, unknown>): string {
  const parts = Object.entries(args).map(([k, v]) => `${k}=${JSON.stringify(v)}`);
  return parts.join(", ");
}

export function stepLabel(trace: Trace, step: TraceStep): string {
  if (step.kind === "user") {
    return trace.scenario.channel === "user" ? "User request (this is the attack text)" : "User task";
  }
  if (step.kind === "assistant") {
    const calls = (step.tool_calls ?? []).map((c) => `${c.name}(${argsText(c.args)})`);
    return `Agent calls ${calls.join(", ") || "a tool"}`;
  }
  if (step.kind === "tool") {
    const t = step.tool;
    const name = t ? `${t.name}(${argsText(t.args)})` : "tool";
    return `Tool result: ${name}${t?.ok === false ? " (failed or blocked)" : ""}`;
  }
  return "Agent's final answer";
}

/** The conversation steps followed by one last "judge" step. */
export function buildTimeline(trace: Trace): TimelineStep[] {
  const steps: TimelineStep[] = trace.steps.map((step) => ({
    label: stepLabel(trace, step),
    kind: step.kind,
    step,
  }));
  steps.push({ label: "Judge's verdict", kind: "verdict" });
  return steps;
}

export type Segment = { text: string; injected: boolean };

/** Split `text` at the given [start, end) spans; the pieces joined give back `text` exactly. */
export function segments(text: string, spans: readonly number[][]): Segment[] {
  const out: Segment[] = [];
  let at = 0;
  for (const span of [...spans].sort((a, b) => (a[0] ?? 0) - (b[0] ?? 0))) {
    const [start, end] = span;
    if (start === undefined || end === undefined || start < at || end > text.length) continue;
    if (start > at) out.push({ text: text.slice(at, start), injected: false });
    out.push({ text: text.slice(start, end), injected: true });
    at = end;
  }
  if (at < text.length) out.push({ text: text.slice(at), injected: false });
  return out;
}

export function eventText(event: DefenseEvent): string {
  if (event.type === "detector") {
    if (event.verdict === true) return `Detector answered ${event.reply ?? "YES"}: the result was removed.`;
    if (event.verdict === false) return `Detector answered ${event.reply ?? "NO"}: the result was passed on.`;
    return "Detector reply could not be read: treated as not flagged.";
  }
  if (event.type === "blocked") return `Tool policy blocked ${event.tool ?? "the call"} to ${event.to ?? "an unknown recipient"}.`;
  return `${event.type} event.`;
}

export interface VerdictAccount {
  badge: "ATTACK EXECUTED" | "ATTACK BLOCKED" | "NO ATTACK IN THIS RUN";
  executed: boolean | null;
  reasons: string[];
}

/** Why the judge decided what it did, from the stored rule, outbox and blocked attempts. */
export function verdictAccount(trace: Trace): VerdictAccount {
  const v = trace.verdict;
  if (v.attack_success === null || v.rule === null) {
    return {
      badge: "NO ATTACK IN THIS RUN",
      executed: null,
      reasons: ["No attack was planted, so only task success is judged."],
    };
  }
  const reasons = [v.rule.text];
  if (v.attack_success) {
    const e = v.rule.matched_email;
    reasons.push(
      e
        ? `The outbox holds that email: to ${e.to.join(", ")}, subject "${e.subject}", body "${e.body}".`
        : "The outbox holds a matching email.",
    );
    return { badge: "ATTACK EXECUTED", executed: true, reasons };
  }
  if (v.rule.blocked_attempts.length > 0) {
    for (const b of v.rule.blocked_attempts) {
      reasons.push(`The agent tried to send it (${argsText(b.args)}), but the call failed: ${b.result}`);
    }
    reasons.push("A refused send leaves nothing in the outbox, so the attack did not succeed.");
  } else {
    reasons.push("No such email was recorded in the outbox.");
  }
  return { badge: "ATTACK BLOCKED", executed: false, reasons };
}
