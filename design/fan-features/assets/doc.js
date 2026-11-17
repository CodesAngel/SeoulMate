/* Builds every <section class="fig"> on a proposal page:
   data-screen   mock screen (screens/*.html), loaded in a 390 px phone and a 1280 px window
   data-url      the route shown in the window bar
   data-states   "key:Label,key:Label"   data-default  starting state
   data-today-phone / data-today-desk   screenshots of the live site today
   data-today-cap                        caption for the screenshots
   data-today-none                       text when nothing exists today
   Child <div class="state-notes" data-for="key"> blocks become the notes column. */
(function () {
  const W = 1280, H = 860;
  document.querySelectorAll('.fig').forEach((fig, n) => {
    const d = fig.dataset;
    const states = (d.states || '').split(',').filter(Boolean).map((s) => s.split(':'));
    const notes = [...fig.querySelectorAll('.state-notes')];
    let state = d.default || (states[0] && states[0][0]) || '';
    let theme = 'light', view = 'phone', side = 'proposed';
    // Today screenshots can differ per state: "stateA=file.webp;stateB=other.webp".
    const pick = (v) => {
      if (!v || !v.includes('=')) return v;
      const map = Object.fromEntries(v.split(';').map((x) => x.split('=')));
      return map[state] || map['*'] || Object.values(map)[0];
    };
    const none = d.todayNone ? `<div class="nothing"><div>${d.todayNone}</div></div>` : '';
    const todayHTML = (v, alt) => (pick(v) ? `<img src="${pick(v)}" alt="${alt}">` : none);
    const todayPhone = todayHTML(d.todayPhone, 'Today on a phone');
    const todayDesk = todayHTML(d.todayDesk, 'Today on a computer');
    fig.innerHTML = `
      <div class="toggle">
        <span class="grp"><button data-view="phone">Phone</button><button data-view="desk">Computer</button></span>
        ${states.length > 1 ? `<span class="sep"></span><span class="grp"><span class="hint">State:</span>${states.map(([k, l]) => `<button data-state="${k}">${l}</button>`).join('')}</span>` : ''}
        <span class="sep"></span><span class="grp"><span class="hint">Theme:</span><button data-theme="light">Light</button><button data-theme="dark">Dark</button></span>
      </div>
      <div class="view v-phone">
        <div class="col"><div class="cap"><b>Today</b><small class="today-cap"></small></div><div class="phone today">${todayPhone}</div></div>
        <div class="col"><div class="cap"><b>Proposed</b><small>${d.url}</small></div><div class="phone"><iframe title="Proposed, phone" src="${d.screen}"></iframe></div></div>
        <div class="col notes"><div class="cap"><b>In this state</b><small>Scroll inside the screens; buttons in the mock work.</small></div></div>
      </div>
      <div class="view v-desk">
        <div class="toggle"><span class="grp"><button data-side="today">Today</button><button data-side="proposed">Proposed</button></span><span class="hint">Same scale. Today: <span class="today-cap"></span></span></div>
        <div class="browser"><div class="bar"><i></i><i></i><i></i><span class="url"></span></div><div class="stage"></div></div>
        <p class="desk-caption">1280 × 860 window, shown at <span class="pct"></span>.</p>
      </div>`;
    const notesCol = fig.querySelector('.notes');
    notes.forEach((x) => notesCol.appendChild(x));
    if (!notes.length) notesCol.remove();
    const phoneFrame = fig.querySelector('.v-phone iframe');
    const stage = fig.querySelector('.stage');
    const url = fig.querySelector('.url');
    let deskFrame = null, todayImg = null;

    function post(f) { if (f && f.contentWindow) f.contentWindow.postMessage({ mock: 1, state, theme }, '*'); }
    function sync() {
      fig.querySelectorAll('[data-view]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.view === view));
      fig.querySelectorAll('[data-state]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.state === state));
      fig.querySelectorAll('[data-theme]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.theme === theme));
      fig.querySelectorAll('[data-side]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.side === side));
      fig.querySelector('.v-phone').classList.toggle('on', view === 'phone');
      fig.querySelector('.v-desk').classList.toggle('on', view === 'desk');
      notes.forEach((x) => x.classList.toggle('on', x.dataset.for.split(' ').includes(state) || x.dataset.for === '*'));
      const tp = fig.querySelector('.phone.today img');
      if (tp && pick(d.todayPhone)) tp.src = pick(d.todayPhone);
      if (todayImg && todayImg.tagName === 'IMG' && pick(d.todayDesk)) todayImg.src = pick(d.todayDesk);
      fig.querySelectorAll('.today-cap').forEach((c) => { c.textContent = pick(d.todayCap) || ''; });
      if (view === 'desk') {
        if (!deskFrame) {
          deskFrame = document.createElement('iframe');
          deskFrame.title = 'Proposed, computer';
          deskFrame.src = d.screen;
          deskFrame.addEventListener('load', () => post(deskFrame));
          stage.appendChild(deskFrame);
          stage.insertAdjacentHTML('beforeend', todayDesk);
          todayImg = stage.querySelector('img, .nothing');
        }
        deskFrame.style.display = side === 'proposed' ? 'block' : 'none';
        if (todayImg) todayImg.style.display = side === 'today' ? 'block' : 'none';
        url.textContent = side === 'proposed' ? 'seoulmate-azure.vercel.app' + d.url : (d.todayUrl || 'seoulmate-azure.vercel.app');
        scale();
      }
      post(phoneFrame); post(deskFrame);
    }
    function scale() {
      if (!deskFrame) return;
      const s = Math.min(1, stage.clientWidth / W);
      deskFrame.style.transform = `scale(${s})`;
      stage.style.height = side === 'today' && todayImg && todayImg.tagName === 'IMG' ? 'auto' : Math.round(H * s) + 'px';
      if (todayImg && todayImg.tagName !== 'IMG') todayImg.style.height = Math.round(H * s) + 'px';
      fig.querySelector('.pct').textContent = Math.round(s * 100) + '%';
    }
    new ResizeObserver(scale).observe(stage);
    phoneFrame.addEventListener('load', () => post(phoneFrame));
    fig.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.view) view = b.dataset.view;
      if (b.dataset.state) state = b.dataset.state;
      if (b.dataset.theme) theme = b.dataset.theme;
      if (b.dataset.side) side = b.dataset.side;
      sync();
    });
    window.addEventListener('message', (e) => {
      const m = e.data || {};
      if (!m.mockState || (e.source !== phoneFrame.contentWindow && !(deskFrame && e.source === deskFrame.contentWindow))) return;
      state = m.mockState;
      sync();
    });
    sync();
  });
})();
