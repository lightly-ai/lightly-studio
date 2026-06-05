// Auto-advance for .ls-carousel scroll-snap carousels.
// Cycles through slides on a timer, pausing while the user interacts.

(function () {
  var INTERVAL_MS = 4000; // time each slide is shown
  var RESUME_MS = 8000; // wait after user interaction before resuming

  function initCarousel(track) {
    var timer = null;

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
    }

    // Pause while hovering or touching; resume shortly after.
    track.addEventListener("mouseenter", stop);
    track.addEventListener("mouseleave", start);

    var resumeTimer = null;
    function pauseThenResume() {
      stop();
      window.clearTimeout(resumeTimer);
      resumeTimer = window.setTimeout(start, RESUME_MS);
    }
    track.addEventListener("pointerdown", pauseThenResume);
    track.addEventListener("wheel", pauseThenResume, { passive: true });

    start();
  }

  function init() {
    // Respect users who prefer reduced motion: no auto-play.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    var tracks = document.querySelectorAll(".ls-carousel");
    for (var i = 0; i < tracks.length; i++) {
      initCarousel(tracks[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
