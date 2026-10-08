(() => {
  // ---------- Reaction Speed Test ----------
  const pad = document.getElementById('rt-pad');
  const bestEl = document.getElementById('rt-best');
  let state = 'idle', timer = null, startTs = 0, best = null;
  try { best = parseInt(localStorage.getItem('rt-best'), 10) || null; } catch (e) {}
  if (best) bestEl.textContent = best + ' ms';

  const setPad = (cls, text) => { pad.className = pad.className.replace(/rt-\w+/g, '').trim() + ' ' + cls; pad.textContent = text; };

  pad.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    if (state === 'idle') {
      state = 'waiting';
      setPad('rt-ready', 'Kuting… yashil bo\'lishini kuting');
      timer = setTimeout(() => { state = 'go'; startTs = performance.now(); setPad('rt-go', 'HOZIR BOSING!'); }, 1500 + Math.random() * 3000);
    } else if (state === 'waiting') {
      clearTimeout(timer); state = 'idle';
      setPad('rt-wait', 'Juda erta! Qayta urinib ko\'ring');
    } else if (state === 'go') {
      const ms = Math.round(performance.now() - startTs);
      state = 'idle';
      if (!best || ms < best) { best = ms; bestEl.textContent = ms + ' ms'; try { localStorage.setItem('rt-best', ms); } catch (e) {} }
      setPad('rt-wait', ms + ' ms — qayta o\'ynash uchun bosing');
    }
  });

  // ---------- Number guessing ----------
  const form = document.getElementById('ng-form');
  const input = document.getElementById('ng-input');
  const msg = document.getElementById('ng-msg');
  const left = document.getElementById('ng-left');
  const reset = document.getElementById('ng-reset');
  const MAX_TRIES = 7;
  let secret, tries, over;

  function start() {
    secret = 1 + Math.floor(Math.random() * 100);
    tries = MAX_TRIES; over = false;
    left.textContent = tries; msg.textContent = ''; input.value = ''; input.disabled = false;
  }
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (over) return;
    const n = parseInt(input.value, 10);
    if (!(n >= 1 && n <= 100)) { msg.textContent = '1 dan 100 gacha son kiriting.'; return; }
    tries--; left.textContent = tries;
    if (n === secret) { msg.textContent = `To'g'ri! Son ${secret} edi. ${MAX_TRIES - tries} urinishda topdingiz.`; over = true; input.disabled = true; }
    else if (tries === 0) { msg.textContent = `Urinishlar tugadi. Son ${secret} edi.`; over = true; input.disabled = true; }
    else msg.textContent = n < secret ? 'Kattaroq son ayting ↑' : 'Kichikroq son ayting ↓';
    input.value = ''; input.focus();
  });
  reset.addEventListener('click', start);
  start();
})();
