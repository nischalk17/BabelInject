/** Hash router: works on project Pages without any server configuration.
 *  `#/replay/some-id` opens the route `replay` with the parameter `some-id`. */

import { clear, h } from "./dom";

export interface Route {
  id: string;
  label: string;
  title: string;
  /** May return a cleanup function (for timers); it runs before the next route renders. */
  render: (main: HTMLElement, param?: string) => void | (() => void);
}

export function parseHash(hash: string): { id: string; param: string | undefined } {
  const [id = "", ...rest] = hash.replace(/^#\/?/, "").split("/");
  return { id, param: rest.length ? rest.join("/") : undefined };
}

export function startRouter(routes: Route[], nav: HTMLElement, main: HTMLElement): void {
  const byId = new Map(routes.map((r) => [r.id, r]));
  const first = routes[0];
  if (!first) throw new Error("no routes");

  const links = routes.map((route) =>
    h("a", { href: `#/${route.id}`, "data-route": route.id }, route.label),
  );
  nav.replaceChildren(...links);

  let cleanup: (() => void) | undefined;

  const show = (): void => {
    const parsed = parseHash(location.hash);
    const route = byId.get(parsed.id) ?? first;
    for (const link of links) {
      if (link.getAttribute("data-route") === route.id) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    cleanup?.();
    cleanup = undefined;
    clear(main);
    cleanup = route.render(main, parsed.param) ?? undefined;
    document.title = `${route.title} - BabelInject Results Explorer`;
    const heading = main.querySelector("h1");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
    window.scrollTo(0, 0);
  };

  window.addEventListener("hashchange", show);
  show();
}
