// Runs before the app paints, so dark mode never flashes light. An external file (not an
// inline script) because the Content-Security-Policy only allows scripts from this origin.
;(function () {
  try {
    var saved = localStorage.getItem('afx-theme')
    var dark = saved ? saved === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.classList.toggle('dark', dark)
  } catch {
    /* storage blocked: fall back to the light default */
  }
})()
