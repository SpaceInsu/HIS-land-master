"""국토부 아파트 매매 실거래가 → data/questions.json

- 수도권(서울·경기·인천) 시군구별 최근 N개월 거래를 받아서
  단지·면적별 가장 최근 거래 1건씩 추린 뒤, 1억~50억 범위만 문제로 저장합니다.
- 필요: 환경변수 DATA_GO_KR_KEY (공공데이터포털 일반 인증키, Decoding 키 권장)
- 좌표는 게임 화면에서 카카오 주소검색으로 찾습니다(여기서는 주소만 저장).
"""
import json, os, random, sys, datetime, urllib.parse, urllib.request, urllib.error
import xml.etree.ElementTree as ET

KEY = urllib.parse.unquote(os.environ.get("DATA_GO_KR_KEY", "").strip())  # Encoding 키를 넣어도 동작하게
MONTHS = int(os.environ.get("MONTHS", "3"))
PER_REGION = int(os.environ.get("PER_REGION", "12"))
# 사용자가 신청한 "아파트 매매 실거래가 상세 자료" API
URL = os.environ.get("TRADE_URL", "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev")

# (법정동 시군구 코드 5자리, 시도, 시군구 이름) — KB 데이터허브 지역 이름과 같게 맞춤
REGIONS = [
 ("11110","서울","종로구"),("11140","서울","중구"),("11170","서울","용산구"),("11200","서울","성동구"),("11215","서울","광진구"),
 ("11230","서울","동대문구"),("11260","서울","중랑구"),("11290","서울","성북구"),("11305","서울","강북구"),("11320","서울","도봉구"),
 ("11350","서울","노원구"),("11380","서울","은평구"),("11410","서울","서대문구"),("11440","서울","마포구"),("11470","서울","양천구"),
 ("11500","서울","강서구"),("11530","서울","구로구"),("11545","서울","금천구"),("11560","서울","영등포구"),("11590","서울","동작구"),
 ("11620","서울","관악구"),("11650","서울","서초구"),("11680","서울","강남구"),("11710","서울","송파구"),("11740","서울","강동구"),
 # 인천: 2026년 행정구역 개편 전후 코드를 모두 시도 (결과 없는 코드는 그냥 건너뜀)
 ("28110","인천","중구"),("28140","인천","동구"),("28260","인천","서구"),
 ("28125","인천","제물포구"),("28155","인천","영종구"),("28177","인천","미추홀구"),("28185","인천","연수구"),("28200","인천","남동구"),
 ("28237","인천","부평구"),("28245","인천","계양구"),("28275","인천","서해구"),("28290","인천","검단구"),("28710","인천","강화군"),
 ("41111","경기","수원시 장안구"),("41113","경기","수원시 권선구"),("41115","경기","수원시 팔달구"),("41117","경기","수원시 영통구"),
 ("41131","경기","성남시 수정구"),("41133","경기","성남시 중원구"),("41135","경기","성남시 분당구"),("41150","경기","의정부시"),
 ("41171","경기","안양시 만안구"),("41173","경기","안양시 동안구"),("41192","경기","부천시 원미구"),("41194","경기","부천시 소사구"),
 ("41196","경기","부천시 오정구"),("41190","경기","부천시"),("41210","경기","광명시"),("41220","경기","평택시"),("41250","경기","동두천시"),
 ("41271","경기","안산시 상록구"),("41273","경기","안산시 단원구"),("41281","경기","고양시 덕양구"),("41285","경기","고양시 일산동구"),
 ("41287","경기","고양시 일산서구"),("41290","경기","과천시"),("41310","경기","구리시"),("41360","경기","남양주시"),("41370","경기","오산시"),
 ("41390","경기","시흥시"),("41410","경기","군포시"),("41430","경기","의왕시"),("41450","경기","하남시"),("41461","경기","용인시 처인구"),
 ("41463","경기","용인시 기흥구"),("41465","경기","용인시 수지구"),("41480","경기","파주시"),("41500","경기","이천시"),("41550","경기","안성시"),
 ("41570","경기","김포시"),("41590","경기","화성시"),("41591","경기","화성시 만세구"),("41593","경기","화성시 효행구"),
 ("41595","경기","화성시 병점구"),("41597","경기","화성시 동탄구"),("41610","경기","광주시"),("41630","경기","양주시"),("41650","경기","포천시"),
 ("41670","경기","여주시"),("41800","경기","연천군"),("41820","경기","가평군"),("41830","경기","양평군"),
]

def months_back(n):
    d = datetime.date.today().replace(day=1)
    out = []
    for _ in range(n):
        out.append(d.strftime("%Y%m"))
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    return out

def t(item, *names):
    for n in names:
        e = item.find(n)
        if e is not None and e.text and e.text.strip():
            return e.text.strip()
    return ""

def fetch(lawd, ym):
    # 국토부 서버가 자주 느리거나 503을 줘서 최대 4번까지 다시 시도
    import time
    for attempt in range(4):
        try:
            return _fetch(lawd, ym)
        except Exception as e:
            if "SERVICE_KEY" in str(e) or "게이트웨이" in str(e) or attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))

UA = {"User-Agent": "Mozilla/5.0 (compatible; his-land-data/1.0)", "Accept": "application/xml"}
STATS = {}

def _note(kind):
    STATS[kind] = STATS.get(kind, 0) + 1

def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()

def _fetch(lawd, ym):
    import time
    rows, page = [], 1
    while True:
        q = urllib.parse.urlencode({"serviceKey": KEY, "LAWD_CD": lawd, "DEAL_YMD": ym, "numOfRows": 1000, "pageNo": page})
        time.sleep(0.3)  # 너무 몰아서 부르지 않기
        try:
            status, ctype, body = _get(f"{URL}?{q}")
        except urllib.error.HTTPError as e:
            _note(f"HTTP {e.code}")
            raise RuntimeError(f"HTTP {e.code} {lawd} {ym}: {e.read()[:300].decode('utf-8', 'replace')}")
        except Exception as e:
            _note(type(e).__name__)
            raise
        snippet = body[:300].decode("utf-8", "replace").replace(KEY, "***")
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            _note("XML 아님")
            raise RuntimeError(f"XML이 아닌 응답 {lawd} {ym} ({ctype}): {snippet}")
        # 공공데이터포털 게이트웨이 오류(키·호출량 초과 등)는 모양이 다름
        reason = root.findtext(".//returnReasonCode") or root.findtext(".//errMsg")
        if reason:
            msg = root.findtext(".//returnAuthMsg") or reason
            _note(f"게이트웨이 {msg}")
            raise RuntimeError(f"게이트웨이 오류 {lawd} {ym}: {msg} ({reason})")
        code = root.findtext(".//resultCode") or ""
        if code not in ("00", "000"):
            _note(f"결과코드 {code or '없음'}")
            raise RuntimeError(f"API 오류 {lawd} {ym}: {code or '코드 없음'} {root.findtext('.//resultMsg')} / {snippet}")
        if root.find(".//totalCount") is None:
            _note("totalCount 없음")
            raise RuntimeError(f"건수 정보 없는 응답 {lawd} {ym}: {snippet}")
        items = root.findall(".//item")
        rows += items
        total = int(root.findtext(".//totalCount") or 0)
        _note("정상" if total else "정상(0건)")
        if page * 1000 >= total or not items:
            return rows
        page += 1

def probe():
    """시작 전에 1번만 불러보고 응답 모양을 기록 (키는 가림)"""
    ym = months_back(2)[1]
    q = urllib.parse.urlencode({"serviceKey": KEY, "LAWD_CD": "11680", "DEAL_YMD": ym, "numOfRows": 5, "pageNo": 1})
    for base in (URL, URL.replace("https://", "http://")):
        try:
            status, ctype, body = _get(f"{base}?{q}")
            print(f"[시험 호출] {base.split('/')[0]} 강남구 {ym}: HTTP {status}, {ctype}, {len(body)}바이트")
            print("  응답 앞부분:", body[:400].decode("utf-8", "replace").replace(KEY, "***").replace("\n", " "))
        except Exception as e:
            print(f"[시험 호출] {base.split('/')[0]} 실패: {type(e).__name__} {str(e)[:200]}")

def main():
    if not KEY:
        sys.exit("DATA_GO_KR_KEY 가 없습니다 (GitHub 저장소 Settings → Secrets → Actions 에 등록)")
    raw = os.environ.get("DATA_GO_KR_KEY", "")
    import re as _re
    print(f"[키 점검] 길이 {len(raw)} / 앞뒤 공백 {'있음' if raw != raw.strip() else '없음'} / %포함 {'예' if '%' in raw else '아니오'}"
          f" / 끝이 == {'예' if KEY.endswith('==') else '아니오'} / 허용 외 문자 {'있음' if _re.search(r'[^A-Za-z0-9+/=%]', raw.strip()) else '없음'}")
    probe()
    yms = months_back(MONTHS)
    out, seen_regions, fails = [], 0, 0
    prev = {}
    try:
        for it in json.load(open("data/questions.json", encoding="utf-8")).get("items", []):
            prev.setdefault((it.get("sido"), it.get("sgg")), []).append(it)
    except Exception:
        pass
    for lawd, sido, sgg in REGIONS:
        best = {}
        for ym in yms:
            try:
                items = fetch(lawd, ym)
            except Exception as e:
                print("건너뜀:", e); fails += 1
                if fails >= 6 and not out and not best:
                    sys.exit("처음부터 계속 실패해서 멈춥니다. 위 오류 내용을 확인하세요.")
                continue
            for it in items:
                if t(it, "cdealType", "해제여부"):  # 해제(취소)된 거래 제외
                    continue
                name = t(it, "aptNm", "아파트")
                try:
                    price = int(t(it, "dealAmount", "거래금액").replace(",", ""))
                    area = float(t(it, "excluUseAr", "전용면적"))
                except ValueError:
                    continue
                if not (10000 <= price <= 500000) or not name:
                    continue
                y, m, d = t(it, "dealYear", "년"), t(it, "dealMonth", "월"), t(it, "dealDay", "일")
                date = f"{y}-{int(m):02d}-{int(d or 1):02d}" if y and m else ""
                dong = t(it, "umdNm", "법정동")
                key = (name, dong, round(area))
                rec = {"name": name, "sido": sido, "sgg": sgg, "dong": dong, "jibun": t(it, "jibun", "지번"),
                       "region": f"{sido} {sgg} {dong}".strip(), "area": round(area, 2), "floor": int(t(it, "floor", "층") or 0) or None,
                       "built": int(t(it, "buildYear", "건축년도") or 0) or None, "ym": date[:7], "date": date, "price": price,
                       "address": f"{sido} {sgg} {dong} {t(it, 'jibun', '지번')}".strip()}
                if key not in best or rec["date"] > best[key]["date"]:
                    best[key] = rec
        recs = list(best.values())
        if not recs and prev.get((sido, sgg)):
            out += prev[(sido, sgg)]; seen_regions += 1
            print(f"{sido} {sgg}: 이번엔 못 받아서 이전 문제 {len(prev[(sido, sgg)])}개 유지")
            continue
        if recs:
            seen_regions += 1
            random.shuffle(recs)
            # 같은 단지가 몰리지 않게 단지당 1건씩 우선 뽑기
            picked, names = [], set()
            for r in recs:
                if r["name"] in names: continue
                names.add(r["name"]); picked.append(r)
                if len(picked) >= PER_REGION: break
            out += picked
        print(f"{sido} {sgg}: 거래 {len(recs)}건 → {min(len(recs), PER_REGION)}문제")
    print("[호출 결과 집계]", ", ".join(f"{k} {v}회" for k, v in sorted(STATS.items(), key=lambda x: -x[1])))
    if len(out) < 20:
        sys.exit(f"문제가 너무 적습니다({len(out)}). 키나 API 상태를 확인하세요.")
    data = {"source": "국토교통부 아파트 매매 실거래가", "updated": datetime.date.today().isoformat(),
            "months": yms, "regions": seen_regions, "items": out}
    os.makedirs("data", exist_ok=True)
    with open("data/questions.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"저장: data/questions.json ({len(out)}문제, {seen_regions}개 시군구)")

if __name__ == "__main__":
    main()
