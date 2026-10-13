/* CVTA page loader
   -------------------------------------------------------------------
   Mounts hamburger.riv (artboard "loader", view model "Loader") into
   #cvta-loader-canvas, sets `loadEntrance = true` so the state machine
   plays its entrance + loop, then fires the `loadComplete` trigger once
   every image + font on the page has loaded. The overlay is removed
   when the SM fires the `loadEnd` trigger at the end of its exit anim.

   Fast loads: entrance + loop + exit play through quickly (minimum
     MIN_ENTRANCE_MS gate keeps very fast loads from blipping past).
   Slow loads: SM holds on its loop state until loadComplete fires. */
(function () {
  const TAG = '[CVTA loader]';
  const overlay = document.getElementById('cvta-loader');
  const canvas  = document.getElementById('cvta-loader-canvas');
  if (!overlay || !canvas) return;
  if (typeof rive === 'undefined') { console.error(TAG, 'Rive runtime missing'); overlay.remove(); return; }

  // Resolve the .riv next to this script so it works from any page depth.
  const scriptSrc = (document.currentScript && document.currentScript.src) || '';
  const rivUrl    = scriptSrc.replace(/loader\.js(\?.*)?$/, 'hamburger.riv');

  // Minimum time the entrance+loop portion gets on screen before we fire
  // loadComplete. Tune to taste for the Rive entrance duration.
  const MIN_ENTRANCE_MS = 2000;

  let vmInstance        = null;
  let riveReady         = false;
  let pageLoaded        = false;
  let dismissed         = false;
  let loadCompleteFired = false;
  let entranceAt        = 0;

  const riveInstance = new rive.Rive({
    src: rivUrl,
    canvas: canvas,
    artboard: 'loader',
    stateMachine: 'State Machine 1',  // SINGULAR per Rive docs
    autoplay: true,
    autoBind: true,                   // binds default instance of Loader VM to artboard
    useOffscreenRenderer: true,       // share the WebGL2 context with the menubar
    layout: new rive.Layout({ fit: rive.Fit.Contain, alignment: rive.Alignment.Center }),
    onLoad: () => {
      riveInstance.resizeDrawingSurfaceToCanvas();

      vmInstance = riveInstance.viewModelInstance || null;
      if (!vmInstance) {
        try {
          const vm = riveInstance.viewModelByName('Loader');
          vmInstance = vm && (vm.defaultInstance() || vm.instanceByIndex(0));
          if (vmInstance) riveInstance.bindViewModelInstance(vmInstance);
        } catch (e) { console.error(TAG, 'manual VM bind failed:', e); }
      }

      if (vmInstance) {
        const b = vmInstance.boolean('loadEntrance');
        if (b) { b.value = true; entranceAt = performance.now(); }

        // Subscribe to loadEnd — SM fires it when the exit animation ends.
        // Gated on loadCompleteFired so any premature callback can't dismiss early.
        const endTrigger = vmInstance.trigger('loadEnd');
        if (endTrigger && typeof endTrigger.on === 'function') {
          endTrigger.on(() => { if (loadCompleteFired) dismissOverlay(); });
        }
      }

      riveReady = true;
      maybeFinish();
    },
    onLoadError: (e) => { console.error(TAG, 'rive load error:', e); dismissOverlay(); }
  });

  window.addEventListener('resize', () => riveInstance.resizeDrawingSurfaceToCanvas());

  function dismissOverlay() {
    if (dismissed) return;
    dismissed = true;
    overlay.classList.add('is-done');
    overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
  }

  function maybeFinish() {
    if (dismissed || !riveReady || !pageLoaded || loadCompleteFired) return;

    const elapsed = performance.now() - entranceAt;
    const wait    = Math.max(0, MIN_ENTRANCE_MS - elapsed);

    setTimeout(() => {
      if (dismissed || loadCompleteFired) return;
      if (vmInstance) {
        const t = vmInstance.trigger('loadComplete');
        if (t) { t.trigger(); loadCompleteFired = true; }
      }
    }, wait);
  }

  const loadDone  = document.readyState === 'complete'
    ? Promise.resolve()
    : new Promise(res => window.addEventListener('load', res, { once: true }));
  const fontsDone = (document.fonts && document.fonts.ready) || Promise.resolve();

  Promise.all([loadDone, fontsDone]).then(() => {
    pageLoaded = true;
    maybeFinish();
  });

  // Safety net: if Rive never fires onLoad or loadEnd, don't leave the overlay stuck.
  setTimeout(() => { if (!dismissed) { console.warn(TAG, 'safety timeout'); dismissOverlay(); } }, 15000);
})();
