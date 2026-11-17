/* Shared script for the mock screens in screens/.
   - <i data-icon="name"></i> becomes an inline Lucide icon (same icons the site uses).
   - <div data-header="discover"></div> becomes the site's real header.
   - Elements with data-when="a b" show only in those states. The proposal page sets the
     state and theme with postMessage; opening a screen directly reads #state=a&theme=dark.
   - Clicking an element with data-go="state" switches state and tells the proposal page. */
(function () {
  const P = {
    heart: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    bookmark: '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
    star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    clapperboard: '<path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3Z"/><path d="m6.2 5.3 3.1 3.9"/><path d="m12.4 3.4 3.1 4"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    pen: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    menu: '<line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    'arrow-right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    'arrow-left': '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    'chevron-down': '<path d="m6 9 6 6 6-6"/>',
    'chevron-left': '<path d="m15 18-6-6 6-6"/>',
    'chevron-right': '<path d="m9 18 6-6-6-6"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    minus: '<path d="M5 12h14"/>',
    sparkles: '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"/>',
    flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    calendar: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    lock: '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    shuffle: '<path d="m18 14 4 4-4 4"/><path d="m18 2 4 4-4 4"/><path d="M2 18h1.973a4 4 0 0 0 3.3-1.7l5.454-8.6a4 4 0 0 1 3.3-1.7H22"/><path d="M2 6h1.972a4 4 0 0 1 3.6 2.2"/><path d="M22 18h-6.041a4 4 0 0 1-3.3-1.8l-.359-.45"/>',
    lightbulb: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
    list: '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
    'list-plus': '<path d="M11 12H3"/><path d="M16 6H3"/><path d="M16 18H3"/><path d="M18 9v6"/><path d="M21 12h-6"/>',
    trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    grip: '<circle cx="9" cy="12" r="1"/><circle cx="9" cy="5" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="19" r="1"/>',
    flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
    tv: '<rect width="20" height="15" x="2" y="7" rx="2"/><polyline points="17 2 12 7 7 2"/>',
    eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    image: '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
    zoom: '<circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/><line x1="11" x2="11" y1="8" y2="14"/><line x1="8" x2="14" y1="11" y2="11"/>',
    route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  };
  function icon(name, size) {
    const s = size || 16;
    const fill = name === 'star' || name === 'play' ? 'currentColor' : 'none';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 24 24" fill="${fill}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || ''}</svg>`;
  }
  window.mockIcon = icon;

  /* A drama card with the site's real markup. d: {t, img, r, eps, g, sub, badge, seen, saved, attrs} */
  window.mockCard = (d) => `<article class="drama-card"${d.attrs || ''}><div class="poster-frame"><a class="poster-link-wrap" href="#"><img class="poster-img" alt="${d.t} poster" src="../posters/${d.img}.webp" style="position:absolute;height:100%;width:100%;inset:0"><span class="genre-pill">${d.g}</span><span class="card-gradient"></span></a>${d.badge ? `<span class="card-ai-badge">${d.badge}</span>` : ''}${d.seen ? '<span class="m-badge seen card-seen"><i data-icon="check" data-size="11"></i> Seen</span>' : ''}<button type="button" class="save-button ${d.saved ? 'saved' : ''}" aria-label="Save"><i data-icon="bookmark" data-size="18"></i></button></div><div class="card-copy"><a class="card-title-link" href="#"><h3>${d.t}</h3></a><div class="card-meta"><span class="rating"><i data-icon="star" data-size="13"></i> ${d.r}</span><span class="card-sub-info">${d.sub || d.eps + ' eps'}</span></div></div></article>`;

  function header(active) {
    const nav = [['Discover', 'discover'], ['Community', 'community'], ['My list', 'watchlist'], ['Taste profile', 'profile'], ['Watch Together', 'fusion']]
      .map(([label, key]) => `<a href="#" class="${key === active ? 'active' : ''}">${label}</a>`).join('');
    return `<header class="site-header"><div class="shell header-inner"><a class="header-brand" href="#"><span class="brand-lockup" aria-label="SeoulMate"><span class="brand-icon" aria-hidden="true">${icon('clapperboard', 18)}</span><span class="brand-name">Seoul<span>Mate</span></span></span></a><nav class="desktop-nav" aria-label="Primary navigation">${nav}</nav><form class="header-search" role="search">${icon('search', 15)}<input placeholder="Search a mood, actor, or story" aria-label="Search dramas"><kbd aria-hidden="true">↵</kbd></form><div class="header-actions"><button type="button" class="icon-button theme-toggle-btn" aria-label="Theme">${icon('moon', 18)}</button><a class="icon-button" aria-label="My list" href="#">${icon('heart', 18)}</a><a class="auth-link" aria-label="Account" href="#">${icon('user', 16)}<span class="hdr-user">Minji</span><span class="hdr-guest">Sign in</span></a><button type="button" class="mobile-menu-button" aria-label="Toggle navigation">${icon('menu', 20)}</button></div></div></header>`;
  }

  function apply(state, theme) {
    const root = document.documentElement;
    if (theme) root.dataset.theme = theme;
    if (state) root.dataset.state = state;
    const cur = root.dataset.state;
    document.querySelectorAll('[data-when]').forEach((el) => {
      el.classList.toggle('when-on', el.dataset.when.split(/\s+/).includes(cur));
    });
    document.querySelectorAll('[data-go]').forEach((el) => {
      el.classList.toggle('is-current', el.dataset.go === cur);
    });
    if (state && window.onMockState) window.onMockState(state);
  }
  window.mockSetState = (s) => { apply(s); parent.postMessage({ mockState: s, screen: location.pathname.split('/').pop() }, '*'); };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-header]').forEach((el) => { el.outerHTML = header(el.dataset.header); });
    document.querySelectorAll('i[data-icon]').forEach((el) => { el.outerHTML = icon(el.dataset.icon, Number(el.dataset.size) || 16); });
    const h = new URLSearchParams(location.hash.slice(1));
    apply(h.get('state') || document.documentElement.dataset.state, h.get('theme') || 'light');
    document.addEventListener('click', (e) => {
      const go = e.target.closest('[data-go]');
      if (go) { e.preventDefault(); window.mockSetState(go.dataset.go); }
      else if (e.target.closest('a[href="#"]')) e.preventDefault();
    });
  });
  window.addEventListener('message', (e) => {
    const d = e.data || {};
    if (d.mock) apply(d.state, d.theme);
  });
})();
