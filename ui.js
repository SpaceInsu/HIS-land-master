// ===== 화면 다듬기 (게임 동작과 따로) =====
// 매물 정보 카드가 새로 그려질 때마다:
//  - '전용면적' 줄에 강조 표시(area)
//  - '참고 시세' 줄 빼기, '최근 거래일'은 세부 정보 안으로
//  - '세부 정보' 띠를 눌러 아래 줄을 접고 펼 수 있게 (선택은 이 기기에 기억)
(() => {
  const hints = document.getElementById('hints');
  if (!hints) return;
  const KEY = 'detailsOpen';
  let open = true;
  try { open = localStorage.getItem(KEY) !== '0'; } catch (_) {}

  let moving = false;
  function apply() {
    if (moving) return;
    const label = r => (r.firstElementChild && r.firstElementChild.textContent.trim()) || '';
    const rows = [...hints.children];
    rows.forEach(r => {
      const k = label(r);
      if (k === '전용면적') r.classList.add('area');
      if (k === '참고 시세') r.remove();            // 사용자 요청: 참고 시세 줄 빼기
    });
    const sec = hints.querySelector('.sec');
    if (!sec) return;
    // 최근 거래일(또는 거래 시점·시세 기준)은 세부 정보 안 맨 위로
    const dateRow = [...hints.children].find(r => ['최근 거래일', '거래 시점', '시세 기준'].includes(label(r)));
    if (dateRow && !(sec.compareDocumentPosition(dateRow) & Node.DOCUMENT_POSITION_FOLLOWING)) {
      moving = true; sec.after(dateRow); moving = false;
    }
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
