// Auto-advance for .ls-carousel scroll-snap carousels.
// Cycles through slides on a timer, pausing while the user interacts.
//
// The docs use Material's `navigation.instant`, which swaps page content
// without re-firing DOMContentLoaded. We therefore (re)initialize on every
// emission of Material's `document$` observable and tear down the previous
// page's timers first, so carousels work after instant navigation and no
// interval is left running against detached DOM.

(function () {
  var INTERVAL_MS = 4000; // time each slide is shown
  var RESUME_MS = 8000; // wait after user interaction before resuming

  // Returns a cleanup function that stops this carousel's timers/listeners.
  function initCarousel(track) {
    var timer = null;
    var resumeTimer = null;
    var hovering = false; // pointer is currently over the track

    function advance() {
      // One slide == the visible width of the track. Loop back at the end.
      var atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 1;
      var target = atEnd ? 0 : track.scrollLeft + track.clientWidth;
      track.scrollTo({ left: target, behavior: "smooth" });
    }

    function start() {
      if (timer === null) {
        timer = window.setInterval(advance, INTERVAL_MS);
      }
    }

    function stop() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
      // Cancel any pending interaction-resume too, so it can't restart
      // autoplay after we've been asked to stop.
      window.clearTimeout(resumeTimer);
      resumeTimer = null;
    }

    function onEnter() {
      hovering = true;
      stop();
    }

    function onLeave() {
      hovering = false;
      start();
    }

    function pauseThenResume() {
      stop();
      // While hovering, mouseleave owns the restart (indefinite pause). Only
      // arm a timed resume when the pointer is not over the carousel (e.g.
      // touch scroll), otherwise this timer would undercut the hover pause.
      if (!hovering) {
        resumeTimer = window.setTimeout(start, RESUME_MS);
      }
    }

    // Pause while hovering or touching; resume shortly after.
    track.addEventListener("mouseenter", onEnter);
    track.addEventListener("mouseleave", onLeave);
    track.addEventListener("pointerdown", pauseThenResume);
    track.addEventListener("wheel", pauseThenResume, { passive: true });

    start();

    return function cleanup() {
      stop();
      track.removeEventListener("mouseenter", onEnter);
      track.removeEventListener("mouseleave", onLeave);
      track.removeEventListener("pointerdown", pauseThenResume);
      track.removeEventListener("wheel", pauseThenResume);
    };
  }

  var cleanups = [];

  function setup() {
    // Tear down carousels from the previously rendered page.
    cleanups.forEach(function (fn) {
      fn();
    });
    cleanups = [];

    // Respect users who prefer reduced motion: no auto-play.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    var tracks = document.querySelectorAll(".ls-carousel");
    for (var i = 0; i < tracks.length; i++) {
      cleanups.push(initCarousel(tracks[i]));
    }
  }

  // Material's `document$` emits on initial load and after every instant
  // navigation. Fall back to DOMContentLoaded if it is unavailable.
  if (typeof document$ !== "undefined") {
    document$.subscribe(setup);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
