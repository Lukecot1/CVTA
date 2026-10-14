/* Award rows open on tap (touch) and Enter/Space (keyboard); hover is CSS.
   One row open at a time. */
(function () {
  const rows = [...document.querySelectorAll('.js-award')];
  if (!rows.length) return;
  const touch = window.matchMedia('(hover: none)');

  function toggle(row) {
    const open = !row.classList.contains('is-open');
    rows.forEach(r => r.classList.remove('is-open'));
    if (open) row.classList.add('is-open');
    rows.forEach(r => r.setAttribute('aria-expanded', String(r.classList.contains('is-open'))));
  }

  rows.forEach(row => {
    row.setAttribute('aria-expanded', 'false');
    row.addEventListener('click', (e) => {
      if (!touch.matches || e.target.closest('a')) return;
      toggle(row);
    });
    row.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(row); }
    });
  });
})();
