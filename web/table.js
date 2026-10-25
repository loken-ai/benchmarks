// A filter box above a result table: rows that do not contain every typed word are hidden.
(function () {
  "use strict";
  for (const box of document.querySelectorAll("input[data-filter]")) {
    const table = document.getElementById(box.dataset.filter);
    box.addEventListener("input", () => {
      const words = box.value.toLowerCase().split(/\s+/).filter(Boolean);
      for (const tr of table.tBodies[0].rows) {
        const text = (tr.cells[0].textContent + " " + tr.cells[5].textContent).toLowerCase();
        tr.style.display = words.every(w => text.includes(w)) ? "" : "none";
      }
    });
  }
})();
