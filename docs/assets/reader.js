(() => {
  const contents = document.getElementById('contents');
  const progress = document.getElementById('progress');
  const story = document.getElementById('story');
  const summary = contents.querySelector('summary');
  contents.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#chapter-"]');
    if (!link) return;
    contents.open = false;
    const heading = document.querySelector(link.getAttribute('href') + ' h2');
    heading.setAttribute('tabindex', '-1');
    heading.focus({ preventScroll: true });
  });
  document.addEventListener('click', event => {
    if (!contents.contains(event.target)) contents.open = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && contents.open) {
      contents.open = false;
      summary.focus();
    }
  });
  let pending = false;
  const update = () => {
    const start = story.getBoundingClientRect().top + window.scrollY;
    const distance = Math.max(1, story.offsetHeight - window.innerHeight);
    const fraction = Math.min(1, Math.max(0, (window.scrollY - start) / distance));
    progress.style.transform = `scaleX(${fraction})`;
    pending = false;
  };
  const schedule = () => {
    if (!pending) { pending = true; requestAnimationFrame(update); }
  };
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  window.addEventListener('load', schedule);
  schedule();
})();
