/** Hash router: works on project Pages without any server configuration. */

import { clear, h } from "./dom";

export interface Route {
  id: string;
  label: string;
  title: string;
  render: (main: HTMLElement) => void;
}

export function startRouter(routes: Route[], nav: HTMLElement, main: HTMLElement): void {
  const byId = new Map(routes.map((r) => [r.id, r]));
  const first = routes[0];
  if (!first) throw new Error("no routes");

  const links = routes.map((route) =>
    h("a", { href: `#/${route.id}`, "data-route": route.id }, route.label),
  );
  nav.replaceChildren(...links);

  const show = (): void => {
    const id = location.hash.replace(/^#\/?/, "") || first.id;
    const route = byId.get(id) ?? first;
    for (const link of links) {
      if (link.getAttribute("data-route") === route.id) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    clear(main);
    route.render(main);
    document.title = `${route.title} - Results Explorer`;
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
