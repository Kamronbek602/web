(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // Theme toggle
  $('#theme-toggle')?.addEventListener('click', () => {
    const dark = document.documentElement.classList.toggle('dark');
    try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (e) {}
  });

  // Ripple on buttons
  document.addEventListener('pointerdown', (e) => {
    const btn = e.target.closest('.btn');
    if (!btn) return;
    const r = btn.getBoundingClientRect();
    const size = Math.max(r.width, r.height);
    const s = document.createElement('span');
    s.className = 'ripple';
    s.style.width = s.style.height = size + 'px';
    s.style.left = e.clientX - r.left - size / 2 + 'px';
    s.style.top = e.clientY - r.top - size / 2 + 'px';
    btn.appendChild(s);
    s.addEventListener('animationend', () => s.remove());
  });

  // Fade-in on scroll
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) { en.target.classList.add('visible'); io.unobserve(en.target); }
    });
  }, { threshold: 0.1 });
  $$('.reveal').forEach((el) => io.observe(el));

  // Likes (fetch, sahifa yangilanmaydi)
  $$('.like-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.closest('[data-post]').dataset.post;
      try {
        const res = await fetch(`/api/posts/${id}/like`, { method: 'POST' });
        if (!res.ok) return;
        const d = await res.json();
        const c = $('.like-count', btn);
        c.textContent = d.count;
        c.classList.remove('bump'); void c.offsetWidth; c.classList.add('bump');
        btn.classList.toggle('liked', d.liked);
        btn.setAttribute('aria-pressed', d.liked);
        if (d.liked) { btn.classList.remove('pop'); void btn.offsetWidth; btn.classList.add('pop'); }
      } catch (e) {}
    });
  });

  // Comments
  $$('.comment-form').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const post = form.closest('[data-post]');
      const fd = new FormData(form);
      const body = (fd.get('body') || '').trim();
      if (!body) return;
      try {
        const res = await fetch(`/api/posts/${post.dataset.post}/comments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ author: fd.get('author'), body }),
        });
        if (!res.ok) return;
        const d = await res.json();
        const wrap = document.createElement('div');
        wrap.className = 'text-sm reveal';
        const name = document.createElement('span');
        name.className = 'font-medium'; name.textContent = d.author;
        const date = document.createElement('span');
        date.className = 'text-xs text-stone-500 ml-1'; date.textContent = d.date;
        const p = document.createElement('p');
        p.className = 'text-stone-600 dark:text-stone-400 whitespace-pre-line'; p.textContent = d.body;
        wrap.append(name, date, p);
        $('.comments', post).appendChild(wrap);
        requestAnimationFrame(() => wrap.classList.add('visible'));
        const cc = $('.comment-count', post);
        cc.textContent = +cc.textContent + 1;
        form.elements.body.value = '';
      } catch (e) {}
    });
  });

  // Lightbox
  const lb = $('#lightbox'), lbImg = $('#lightbox-img');
  const close = () => lb.classList.remove('open');
  document.addEventListener('click', (e) => {
    const img = e.target.closest('.lightbox-trigger');
    if (img) { lbImg.src = img.src; lbImg.alt = img.alt; lb.classList.add('open'); }
    else if (e.target.closest('#lightbox')) close();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
})();
