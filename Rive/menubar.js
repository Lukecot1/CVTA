/* CVTA nav menubar (Rive-driven)
   -------------------------------------------------------------------
   Replaces the SVG + clip-path track-matte arrow on every page.

   Mounts hamburger.riv into #nav-rive-canvas with artboard "MenuBar" (WebGL2
   Rive Renderer, @rive-app/webgl2, so vector feathering renders) and
   state machine "State Machine 1". VM "MenuBar" exposes:
     - maskproperty (number, 0..100) — track-matte sweep. 0 while the
       canvas is fully over the landing hero, rising to 100 as the hero's
       bottom edge scrolls past the canvas. Pages with no hero sit at 100.
     - hover (boolean) — true while pointer is over the canvas.
     - arrowClicked (boolean) — toggles the open/close state (Rive
       internally shows an arrow when false, X when true). Observing
       this drives the drawer open/close.

   Hide on scroll (separate from the mask): scrolling down carries the
   canvas up and out of view with the page; any scroll up (even 1px)
   springs it straight back. It always shows at the top of the page, while
   the menu is open, and on landing pages until the mask sweep has finished
   (the canvas has fully cleared the hero) so the sweep is always seen.

   Property names mirror the ones embedded in the .riv binary exactly
   (note lowercase 'p' in `maskproperty`). */
(function () {
  const TAG = '[CVTA menubar]';
  const canvas = document.getElementById('nav-rive-canvas');
  console.log(TAG, 'script started, canvas =', canvas);
  if (!canvas) { console.error(TAG, 'no #nav-rive-canvas in DOM'); return; }
  if (typeof rive === 'undefined') { console.error(TAG, 'Rive runtime missing'); return; }
  console.log(TAG, 'Rive runtime available, version check:', typeof rive.Rive);

  // Resolve .riv next to this script so it works from any page depth.
  const scriptSrc = (document.currentScript && document.currentScript.src) || '';
  const rivUrl = scriptSrc.replace(/menubar\.js(\?.*)?$/, 'hamburger.riv');

  let vm = null;
  let maskProp = null;
  let hoverProp = null;
  let clickedProp = null;

  // Pick the hero that's actually rendered — desktop #hero is display:none on
  // mobile and vice versa, and getBoundingClientRect on a display:none element
  // returns all zeros which my math reads as "hero fully past" (mask = 100).
  const heroEl = () => {
    if (window.innerWidth <= 500) {
      return document.querySelector('.m-hero') || document.getElementById('hero');
    }
    return document.getElementById('hero') || document.querySelector('.m-hero');
  };

  // The canvas's resting slot from its CSS (top: 24px; height: 40px). Both the
  // mask and the hide logic read this, so the hide transform never moves it.
  function restingSlot() {
    const top = parseFloat(getComputedStyle(canvas).top) || 0;
    return { top, bottom: top + canvas.offsetHeight };
  }

  // mask = how much of the Rive canvas has left the landing (hero) section.
  //   0   = every pixel of the canvas still sits over the hero
  //   100 = the canvas has fully left the hero (or the page has no hero)
  // The sweep runs over the canvas's own height: it starts the moment the
  // hero's bottom edge rises past the canvas's bottom pixel and finishes when
  // it passes the canvas's top pixel.
  function computeMask() {
    const h = heroEl();
    if (!h) return 100;
    const hero = h.getBoundingClientRect();
    if (hero.height <= 0) return 100;
    const slot = restingSlot();
    const cH = slot.bottom - slot.top;
    if (cH <= 0) return 0;
    const outside = slot.bottom - hero.bottom; // px of canvas below the hero's bottom edge
    return Math.max(0, Math.min(1, outside / cH)) * 100;
  }

  let scrollTicking = false;
  function onScroll() {
    if (scrollTicking || !maskProp) return;
    scrollTicking = true;
    requestAnimationFrame(() => {
      maskProp.value = computeMask();
      scrollTicking = false;
    });
  }

  // ── Hide on scroll down, spring back on scroll up ─────────────────────
  let menuOpen = false;
  let lastY = Math.max(0, window.scrollY);
  let hiddenBy = 0; // px the canvas is pushed up (0 = fully shown)
  const SPRING = 'transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1)';

  const siteLogo = document.querySelector('.site-logo');   // rides with the arrow
  function placeCanvas(px, animate) {
    hiddenBy = px;
    for (const el of [canvas, siteLogo]) {
      if (!el) continue;
      el.style.transition = animate ? SPRING + ', opacity 0.4s ease' : 'opacity 0.4s ease';
      el.style.transform = px ? `translateY(${-px}px)` : '';
    }
  }
  // Logo stays hidden while the arrow is over a landing hero (its big CVTA
  // letters already say who we are).
  function syncLogo() {
    if (siteLogo) siteLogo.classList.toggle('is-hidden', overHero());
  }
  // True while any part of the canvas slot is still over the landing hero,
  // i.e. the mask sweep hasn't finished — keep the arrow in view for it.
  function overHero() {
    const h = heroEl();
    if (!h) return false;
    const hero = h.getBoundingClientRect();
    return hero.height > 0 && hero.bottom > restingSlot().top;
  }
  function onScrollHide() {
    const y = Math.max(0, window.scrollY);   // ignore iOS top bounce
    const dy = y - lastY;
    lastY = y;
    if (menuOpen || y <= 0 || overHero()) { if (hiddenBy) placeCanvas(0, true); return; }
    if (dy > 0) {
      // Move up with the page until fully off-screen.
      const max = restingSlot().bottom + 8;
      const next = Math.min(max, hiddenBy + dy);
      if (next !== hiddenBy) placeCanvas(next, false);
    } else if (dy < 0 && hiddenBy) {
      placeCanvas(0, true);
    }
  }
  window.addEventListener('scroll', onScrollHide, { passive: true });
  window.addEventListener('scroll', syncLogo, { passive: true });
  window.addEventListener('resize', syncLogo);
  syncLogo();
  document.addEventListener('cvta:drawer-toggle', (e) => {
    menuOpen = !!(e.detail && e.detail.open);
    if (menuOpen && hiddenBy) placeCanvas(0, true);
  });

  const riveInstance = new rive.Rive({
    src: rivUrl,
    canvas: canvas,
    artboard: 'MenuBar',
    stateMachine: 'State Machine 1',
    autoplay: true,
    autoBind: true,
    // WebGL2 Rive Renderer (vector feathering); one shared GL context for
    // the menubar + loader instances.
    useOffscreenRenderer: true,
    layout: new rive.Layout({ fit: rive.Fit.Contain, alignment: rive.Alignment.Center }),
    onLoad: () => {
      console.log(TAG, 'onLoad fired. artboards:', riveInstance.contents);
      riveInstance.resizeDrawingSurfaceToCanvas();

      vm = riveInstance.viewModelInstance || null;
      if (!vm) {
        try {
          const named = riveInstance.viewModelByName('MenuBar');
          vm = named && (named.defaultInstance() || named.instanceByIndex(0));
          if (vm) riveInstance.bindViewModelInstance(vm);
        } catch (e) { console.error(TAG, 'manual VM bind failed:', e); }
      }
      if (!vm) { console.error(TAG, 'no viewModelInstance; aborting wiring'); return; }

      // Property lookups — names must match the .riv binary exactly.
      maskProp    = vm.number('maskproperty');  // lowercase p intentional
      hoverProp   = vm.boolean('hover');
      clickedProp = vm.boolean('arrowClicked');

      // Hover
      canvas.addEventListener('pointerenter', () => { if (hoverProp) hoverProp.value = true; });
      canvas.addEventListener('pointerleave', () => { if (hoverProp) hoverProp.value = false; });

      // Observe arrowClicked. Rive fires once on subscribe with the current
      // value — read it synchronously first and set the drawer state directly,
      // then subscribe for future changes.
      if (clickedProp) {
        syncDrawer(!!clickedProp.value);
        if (typeof clickedProp.on === 'function') {
          clickedProp.on((v) => syncDrawer(!!v));
        }
      }

      // Landing pages start at 0 and sweep to 100 as the canvas scrolls
      // off the hero; pages without a hero sit at 100.
      if (maskProp) {
        maskProp.value = computeMask();
        if (heroEl()) {
          window.addEventListener('scroll', onScroll, { passive: true });
          window.addEventListener('resize', onScroll);
        }
      } else {
        console.error(TAG, 'maskproperty lookup failed! Property name mismatch?');
      }
    },
    onLoadError: (e) => { console.error(TAG, 'rive load error:', e); }
  });

  window.addEventListener('resize', () => riveInstance.resizeDrawingSurfaceToCanvas());

  // Public API — called by menu-link click handlers to close the drawer
  // AND flip the Rive arrow back to its default state in one call.
  window.CVTANav = {
    close() {
      if (clickedProp) clickedProp.value = false;
      // Fallback: if Rive isn't loaded yet, dispatch the event anyway so
      // any pending drawer open can still close.
      document.dispatchEvent(new CustomEvent('cvta:drawer-toggle', { detail: { open: false } }));
    }
  };

  function syncDrawer(open) {
    document.dispatchEvent(new CustomEvent('cvta:drawer-toggle', { detail: { open } }));
  }
})();
