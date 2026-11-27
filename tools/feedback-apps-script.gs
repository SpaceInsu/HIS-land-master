/**
 * 이 집 얼마? 의견함 → 구글 시트 바로 기록
 * 붙이는 곳: 의견 시트(HIS-land-master) → 확장 프로그램 → Apps Script
 * 배포: 배포 → 새 배포 → 유형 '웹 앱' → 실행 사용자 '나' → 액세스 '모든 사용자' → 배포
 * 나온 웹 앱 주소(…/exec)를 게임의 feedback.js ENDPOINT 에 넣는다.
 */
const SHEET_NAME = '시트1';
const MAX_LEN = 2000;

function doPost(e) {
  try {
    const d = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const body = clean(d.body, MAX_LEN);
    if (!body) return out({ ok: false, error: 'empty' });

    // 같은 기기에서 너무 자주 보내면 막기 (10초에 1건)
    const cache = CacheService.getScriptCache();
    const key = 'fb_' + Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, String(d.ua || '') + String(d.viewport || '')));
    if (cache.get(key)) return out({ ok: false, error: 'too-fast' });
    cache.put(key, '1', 10);

    const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
    sh.appendRow([new Date(), body, clean(d.page, 100), clean(d.item, 200), clean(d.viewport, 20), clean(d.ua, 200), '']);
    return out({ ok: true });
  } catch (err) {
    return out({ ok: false, error: String(err) });
  }
}

// 셀이 수식으로 실행되지 않게 맨 앞 = + - @ 를 글자로 바꿈
function clean(v, n) {
  let s = String(v == null ? '' : v).trim().slice(0, n);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}
function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
