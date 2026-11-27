import { h } from "./dom";

export interface Option {
  value: string;
  label: string;
}

/** A labelled native <select>: keyboard and screen-reader support come with the element. */
export function selectControl(
  id: string,
  label: string,
  options: Option[],
  value: string,
  onChange: (value: string) => void,
): HTMLElement {
  const select = h("select", { id });
  for (const option of options) {
    const node = h("option", { value: option.value }, option.label);
    if (option.value === value) node.selected = true;
    select.append(node);
  }
  select.addEventListener("change", () => onChange(select.value));
  return h("div", { class: "control" }, h("label", { for: id }, label), select);
}
