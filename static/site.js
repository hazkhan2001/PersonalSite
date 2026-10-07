// site.js: the site's two small interactive pieces.
//   1. Filter buttons (Writing, Manuscripts, Images, Poetry)
//   2. "Show image" buttons on images marked sensitive
//
// ---- 1. Filters ----
//
// How it fits together:
//   - The area to filter is marked  <div data-filter-root>
//   - Each button says what it filters:  <button data-filter="script" data-value="kufic">
//   - Each item says what it is:  <li data-item data-script="kufic" data-century="9">
// Clicking a button records the choice for that group, then shows only the
// items that match every chosen group. A value of "" means "All".

document.querySelectorAll("[data-filter-root]").forEach((root) => {
  const items = root.querySelectorAll("[data-item]");
  const status = root.querySelector("[data-filter-status]");
  const empty = root.querySelector("[data-filter-empty]");
  const chosen = {}; // e.g. { script: "kufic", century: "" }

  function apply() {
    let shown = 0;
    items.forEach((item) => {
      // Object.entries turns { a: 1 } into [["a", 1]], like Python's .items()
      const matches = Object.entries(chosen).every(
        ([group, value]) => value === "" || item.dataset[group] === value
      );
      item.hidden = !matches;
      if (matches) shown += 1;
    });
    const filtering = Object.values(chosen).some((value) => value !== "");
    if (status) status.textContent = filtering ? `Showing ${shown} of ${items.length}` : "";
    if (empty) empty.hidden = shown > 0;
  }

  root.querySelectorAll("button[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.dataset.filter;
      chosen[group] = button.dataset.value;
      // Mark this button as pressed and the others in its group as not.
      root.querySelectorAll(`button[data-filter="${group}"]`).forEach((other) => {
        other.setAttribute("aria-pressed", String(other === button));
      });
      apply();
    });
  });
});

// ---- 2. Sensitive images ----
// An image marked sensitive starts blurred, with a button over it. Clicking
// the button adds the class "revealed" (CSS then removes the blur) and
// removes the button.
document.querySelectorAll("[data-reveal]").forEach((button) => {
  button.addEventListener("click", () => {
    button.closest(".sensitive").classList.add("revealed");
    button.remove();
  });
});
