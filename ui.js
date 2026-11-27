// ===== 화면 다듬기 (게임 동작과 따로) =====
// 매물 정보 카드가 새로 그려질 때마다:
//  - '전용면적' 줄에 강조 표시(area)
//  - '세부 정보' 띠를 눌러 아래 줄을 접고 펼 수 있게 (선택은 이 기기에 기억)
(() => {
  const hints = document.getElementById('hints');
  if (!hints) return;
  const KEY = 'detailsOpen';
  let open = true;
  try { open = localStorage.getItem(KEY) !== '0'; } catch (_) {}

  function apply() {
    const rows = [...hints.children];
    rows.forEach(r => {
      const label = r.firstElementChild && r.firstElementChild.textContent.trim();
      if (label === '전용면적') r.classList.add('area');
    });
    const sec = hints.querySelector('.sec');
    if (!sec) return;
    if (!sec.dataset.ready) {
      sec.dataset.ready = '1';
      sec.setAttribute('role', 'button');
      sec.setAttribute('tabindex', '0');
      sec.addEventListener('click', toggle);
      sec.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
    }
    sec.setAttribute('aria-expanded', String(open));
    hints.classList.toggle('details-closed', !open);
  }
  function toggle() {
    open = !open;
    try { localStorage.setItem(KEY, open ? '1' : '0'); } catch (_) {}
    apply();
  }
  new MutationObserver(apply).observe(hints, { childList: true });
  apply();
})();
