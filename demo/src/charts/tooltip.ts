import { h } from "../dom";

export interface Tooltip {
  el: HTMLElement;
  show: (anchor: HTMLElement, lines: string[]) => void;
  hide: () => void;
}

/** A visual-only tooltip (the same text is the anchor's aria-label). Lives inside `container`. */
export function createTooltip(container: HTMLElement): Tooltip {
  const el = h("div", { class: "tooltip", "aria-hidden": "true", hidden: true });
  container.append(el);

  const hide = (): void => {
    el.hidden = true;
  };

  const show = (anchor: HTMLElement, lines: string[]): void => {
    el.replaceChildren(...lines.map((line, i) => h("div", { class: i === 0 ? "tip-title" : "" }, line)));
    el.hidden = false;
    const box = container.getBoundingClientRect();
    const a = anchor.getBoundingClientRect();
    const width = el.offsetWidth;
    const left = Math.min(Math.max(a.left - box.left + a.width / 2 - width / 2, 0), Math.max(box.width - width, 0));
    el.style.left = `${left}px`;
    el.style.top = `${a.bottom - box.top + 6}px`;
  };

  return { el, show, hide };
}

/** Show on hover and keyboard focus; hide on leave, blur and Escape. */
export function attachTooltip(target: HTMLElement, tip: Tooltip, lines: string[]): void {
  const open = (): void => tip.show(target, lines);
  target.addEventListener("mouseenter", open);
  target.addEventListener("focus", open);
  target.addEventListener("mouseleave", tip.hide);
  target.addEventListener("blur", tip.hide);
  target.addEventListener("keydown", (event) => {
    if (event.key === "Escape") tip.hide();
  });
}
