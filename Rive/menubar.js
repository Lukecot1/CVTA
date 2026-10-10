/* CVTA nav menubar (Rive-driven)
   -------------------------------------------------------------------
   Replaces the SVG + clip-path track-matte arrow on every page.

   Mounts hamburger.riv into #nav-rive-canvas with artboard "MenuBar" and
   state machine "State Machine 1". VM "MenuBar" exposes:
     - maskproperty (number, 0..100) — track-matte sweep. On index.html
       this is driven by the hero's bottom edge scrolling past the
       canvas slot. On projects/studio.html it's pinned to 0 (per Luke).
     - hover (boolean) — true while pointer is over the canvas.
     - arrowClicked (boolean) — toggles the open/close state (Rive
       internally shows an arrow when false, X when true). Observing
       this drives the drawer open/close.

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

  const ARROW_TOP = 24;
  const ARROW_H   = 40;

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

  // mask = how far the hero has scrolled off the top, as a %.
  //   0   = hero fully in view (page at the very top)
  //   100 = hero fully scrolled above the viewport (next section fills the screen)
  // Gradual sweep over the ENTIRE hero height, not just the 40px sliver where the
  // hero's bottom edge physically crosses the arrow slot.
  function computeMask() {
    const h = heroEl();
    if (!h) { console.log(TAG, 'no hero → mask 0'); return 0; }
    const rect = h.getBoundingClientRect();
    if (rect.height <= 0) { console.log(TAG, 'hero height is 0! el=', h.className||h.id, 'rect=', rect); return 0; }
    const progress = Math.max(0, Math.min(1, -rect.top / rect.height));
    const mask = progress * 100;
    console.log(TAG, 'vw=', innerWidth, 'hero=', h.className||h.id, 'top=', Math.round(rect.top), 'height=', Math.round(rect.height), 'mask=', Math.round(mask));
    return mask;
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

  const riveInstance = new rive.Rive({
    src: rivUrl,
    canvas: canvas,
    artboard: 'MenuBar',
    stateMachine: 'State Machine 1',
    autoplay: true,
    autoBind: true,
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

      // Scroll handling. Pin maskproperty to 0 at load (landing state).
      if (maskProp) {
        console.log(TAG, 'maskproperty BEFORE pin:', maskProp.value);
        maskProp.value = 0;
        console.log(TAG, 'maskproperty AFTER pin:', maskProp.value, '(expect 0)');
        if (heroEl()) {
          console.log(TAG, 'hero found, attaching scroll listener. hero=', heroEl().className || heroEl().id);
          window.addEventListener('scroll', onScroll, { passive: true });
          window.addEventListener('resize', onScroll);
        } else {
          console.log(TAG, 'no hero on this page, maskproperty stays at 0');
        }
      } else {
        console.error(TAG, 'maskProp lookup failed! Property name mismatch?');
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
