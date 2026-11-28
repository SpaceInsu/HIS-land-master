// ===== 의견 보내기 (피드백) =====
// 게임 화면 어디서나 [의견 보내기]를 누르면 작은 창이 뜨고, 보낸 의견은 구글 시트에 바로 한 줄씩 쌓입니다.
// 어느 화면·어느 문제에서 쓴 글인지, 화면 크기가 얼마인지 함께 자동으로 붙습니다.
// 게임 스크립트(index.html)와는 따로 동작합니다. 화면 내용은 읽기만 합니다.
(() => {
  // 의견 시트 연결 주소 (구글 Apps Script 웹 앱 …/exec). 비어 있으면 이 브라우저에만 임시 보관합니다.
  // 시트 쪽 코드는 tools/feedback-apps-script.gs
  const ENDPOINT = '';
  const ready = () => !!ENDPOINT;

  // 지금 보고 있는 화면과 문제를 읽어 옴
  function context() {
    const on = document.querySelector('.screen.on');
    const names = { 's-start': '시작', 's-round': '문제', 's-result': '결과', 's-final': '최종 점수' };
    let page = names[on && on.id] || (on && on.id) || '?';
    const round = $('#round-label');
    if (on && (on.id === 's-round' || on.id === 's-result') && round) page += ' · ' + round.textContent.trim();
    if ($('#rv-modal.on')) page += ' · 로드뷰';
    const nameRow = $('#hints .name span:last-child');
    const region = [...document.querySelectorAll('#hints > div')].find(d => d.firstElementChild && d.firstElementChild.textContent.trim() === '지역');
    const item = [nameRow && nameRow.textContent.trim(), region && region.lastElementChild.textContent.trim()]
      .filter(Boolean).join(' · ') || ($('#r-name') && $('#r-name').textContent.trim()) || '';
    return { page, item, viewport: `${innerWidth}x${innerHeight}`, ua: navigator.userAgent.slice(0, 180) };
  }

  // 화면 만들기
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'fb-open'; btn.textContent = '의견 보내기';
  const header = document.querySelector('header');
  const wrap = document.createElement('div'); wrap.className = 'head-right';
  const badge = header.querySelector('.badge');
  if (badge) wrap.appendChild(badge);
  wrap.appendChild(btn); header.appendChild(wrap);

  const modal = document.createElement('div');
  modal.className = 'modal'; modal.id = 'fb-modal';
  modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true'); modal.setAttribute('aria-label', '의견 보내기');
  modal.innerHTML = `
    <form class="modal-box fb-box" novalidate>
      <div class="modal-head"><b>의견 보내기</b><button type="button" class="fb-close">닫기</button></div>
      <div class="fb-body">
        <p class="fb-lead">불편한 점, 틀린 정보, 바라는 기능을 편하게 적어 주세요.</p>
        <textarea id="fb-text" maxlength="2000" rows="6" placeholder="예) 이 단지 가격이 너무 낮게 나와요 / 초등학교 거리가 이상해요"></textarea>
        <p class="fb-ctx" id="fb-ctx"></p>
        <div class="fb-actions"><span class="fb-msg" id="fb-msg" role="status"></span><button type="submit" class="fb-send">보내기</button></div>
      </div>
    </form>`;
  document.body.appendChild(modal);

  const text = modal.querySelector('#fb-text'), msg = modal.querySelector('#fb-msg'), send = modal.querySelector('.fb-send');
  let ctx = null;
  function open() {
    ctx = context();
    modal.querySelector('#fb-ctx').textContent = `함께 보내는 정보: ${ctx.page}${ctx.item ? ' · ' + ctx.item : ''} · 화면 ${ctx.viewport}`;
    msg.textContent = ''; send.disabled = false;
    modal.classList.add('on'); setTimeout(() => text.focus(), 30);
  }
  function close() { modal.classList.remove('on'); }
  btn.addEventListener('click', open);
  modal.querySelector('.fb-close').addEventListener('click', close);
  modal.addEventListener('click', e => { if (e.target === modal) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && modal.classList.contains('on')) close(); });

  modal.querySelector('form').addEventListener('submit', async e => {
    e.preventDefault();
    const body = text.value.trim();
    if (!body) { msg.textContent = '내용을 적어 주세요.'; text.focus(); return; }
    const last = +(sessionStorage.getItem('fbLast') || 0);
    if (Date.now() - last < 10000) { msg.textContent = '잠시 후 다시 보내 주세요.'; return; }
    send.disabled = true; msg.textContent = '보내는 중…';
    const rec = { body, ...ctx, at: new Date().toISOString() };
    try {
      if (!ready()) throw new Error('not-configured');
      // text/plain으로 보내면 브라우저 사전 확인 없이 바로 전달됩니다. 응답은 읽지 못하므로(no-cors) 네트워크 오류만 실패로 봅니다
      await fetch(ENDPOINT, { method: 'POST', mode: 'no-cors', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body: JSON.stringify(rec) });
      sessionStorage.setItem('fbLast', String(Date.now()));
      text.value = ''; msg.textContent = '고마워요! 잘 받았어요.';
      setTimeout(close, 1200);
    } catch (err) {
      // 연결 전이거나 실패하면 이 브라우저에 임시 보관
      try { const q = JSON.parse(localStorage.getItem('fbQueue') || '[]'); q.push(rec); localStorage.setItem('fbQueue', JSON.stringify(q.slice(-50))); } catch (_) {}
      msg.textContent = err.message === 'not-configured' ? '아직 의견함 연결 전이라 이 기기에 임시로 저장했어요.' : '전송에 실패해 이 기기에 임시로 저장했어요.';
      send.disabled = false;
    }
  });
})();
