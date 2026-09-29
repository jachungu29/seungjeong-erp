#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
승정 ERP - 브라우저 원본 복사본 분석기 (브라우저백업_분석.py)

tools/브라우저백업.bat (브라우저백업_작업.ps1) 이 만든 '브라우저원본_<PC>_<시각>' 폴더를 읽어서
ERP 데이터만 골라 tools/data-backup.html 과 같은 형식
(format 'SEUNGJEONG_ERP_BROWSER_BACKUP', version 1) 의 JSON 파일로 풀어 줍니다.

  ERP 주소(origin) = file:// (ERP HTML 더블클릭), GitHub Pages(ERP 사이트),
                     http(s)://localhost:* 와 http(s)://127.0.0.1:* (개발 서버),
                     사내 LAN/NAS 주소 (사설 IP, *.local, 시놀로지 QuickConnect·DDNS - 일반 규칙만 사용)
  이 밖의 사이트 데이터는 절대 내보내지 않습니다 (몇 곳이 있었는지 개수만 셉니다).

사용법:
  python tools/브라우저백업_분석.py <원본폴더> [--out <출력폴더>] [--label <PC이름>]
  python tools/브라우저백업_분석.py --self-test      (LevelDB MANIFEST 해석 자체 점검)

  --out   : 결과 JSON 을 둘 폴더 (기본 = 원본폴더의 상위 폴더)
  --label : 파일 이름에 넣을 PC 이름 (기본 = manifest.json 의 computerName)

결과 파일:
  승정ERP_디스크추출_<PC이름>_<브라우저>[_<프로필>]_<구분>_<저장소>.json
    구분   = file | github | localhost-<포트> | 127-<포트> | lan-<주소>-<포트>
    저장소 = localStorage | indexedDB | cacheStorage | httpCache (HTTP 디스크 캐시, cacheStorage 모양)
  <PC이름>_분석요약.json  (주소별 개수·크기·마지막 변경 시각, 옛 Supabase 데이터 발견 여부, 연결된 파일)

안전 규칙:
  - 원본 폴더는 읽기만 합니다 (아무것도 쓰거나 지우지 않음. SQLite 는 임시 사본으로 읽음).
  - 이미 있는 결과 파일은 덮어쓰지 않고 이름 뒤에 _2, _3 … 을 붙여 새로 만듭니다.
  - 화면에는 키 이름·개수·크기만 출력하고 값(토큰·비밀번호 등)은 출력하지 않습니다.

종료 코드: 0 = 정상, 1 = 실행 불가(폴더·모듈 없음 등),
           2 = 일부 저장소 분석 오류 또는 불완전한 데이터(풀지 못한 레코드 / 없는 첨부 조각 파일) - 나머지는 저장됨

필요: Python 3.10 이상, ccl_chromium_reader
  pip install git+https://github.com/cclgroupltd/ccl_chromium_reader.git
"""

import argparse
import base64
import collections
import contextlib
import datetime
import hashlib
import io
import json
import math
import os
import pathlib
import re
import shutil
import sqlite3
import struct
import sys
import tempfile
import zlib

PARSER_VERSION = "1.1"


def _setup_stdout():
    # 콘솔이 아니면(파이프/파일) UTF-8 로 출력, 인코딩 못 하는 글자는 ? 로 바꿔 멈추지 않게
    for s in (sys.stdout, sys.stderr):
        try:
            if s.isatty():
                s.reconfigure(errors="replace")
            else:
                s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_setup_stdout()

if sys.version_info < (3, 10):
    print("[오류] Python 3.10 이상이 필요합니다. 지금 버전: %s" % sys.version.split()[0])
    sys.exit(1)

try:
    import ccl_chromium_reader
    from ccl_chromium_reader import ccl_chromium_indexeddb as idx
    from ccl_chromium_reader import ccl_chromium_cache as ccache
    from ccl_chromium_reader.storage_formats import ccl_leveldb
    from ccl_chromium_reader.serialization_formats import ccl_v8_value_deserializer as v8
    from ccl_chromium_reader.serialization_formats import ccl_blink_value_deserializer as blink
except ImportError as _e:
    print("[오류] ccl_chromium_reader 모듈이 없습니다 (%s)." % _e)
    print("  아래 명령으로 설치한 뒤 다시 실행하세요 (git 이 필요합니다):")
    print("    pip install git+https://github.com/cclgroupltd/ccl_chromium_reader.git")
    sys.exit(1)

try:
    from importlib.metadata import version as _pkg_version
    CCL_VERSION = _pkg_version("ccl_chromium_reader")
except Exception:
    CCL_VERSION = getattr(ccl_chromium_reader, "__version__", "?")

EXTRACTOR = ("tools/브라우저백업_분석.py %s + ccl_chromium_reader %s (raw leveldb records: latest sequence number "
             "per key, MANIFEST live-file set by (level, file) with deletes-before-adds per edit, deletions honoured; "
             "IndexedDB blob path fix, kReplaceWithBlob unwrap, Latin-1 strings, Map/Set/TypedArray/Date markers, "
             "FileSystemHandle target path; CacheStorage index.txt + SimpleCache + CacheMetadata protobuf; "
             "HTTP disk cache double-keyed entries of ERP top-frame sites); Python %s"
             % (PARSER_VERSION, CCL_VERSION, sys.version.split()[0]))

# ================================================================ ERP 주소 판별
# GitHub Pages 주소 (ERP 사이트). 다른 github.io 사이트는 ERP 가 아니므로 제외.
GITHUB_ORIGIN = "https://jachungu29.github.io"
# 옛 클라우드(Supabase) 응답으로 볼 URL (data-backup.html 의 DATA_URL 과 같음)
DATA_URL_RE = re.compile(r"supabase\.co|/rest/v1/|/storage/v1/|/functions/v1/", re.I)
TEXT_CT_RE = re.compile(r"^text/|json|javascript|ecmascript|xml|svg|x-www-form-urlencoded", re.I)
# 사내 LAN / NAS 주소 (사설 IP, *.local, 시놀로지 QuickConnect·DDNS). 공개 저장소이므로 실제 주소는 적지 않고
# 일반 규칙만 둔다. ERP 를 NAS 나 사내 서버 주소로 열었던 경우의 데이터를 놓치지 않기 위함.
LAN_HOST_RE = re.compile(
    r"(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:local|lan|home\.arpa|quickconnect\.to|synology\.me|myds\.me"
    r"|diskstation\.me|i234\.me))", re.I)


def normalize_origin(origin):
    """'file:///' → 'file://', 'https://a.com/' → 'https://a.com'"""
    if origin.startswith("file:"):
        return "file://"
    return origin.rstrip("/")


def split_storage_key(sk):
    """Chromium storage key → (origin, 분할(partition) 꼬리 또는 None).
    1st-party: 'https://a.com' / 'file://' / 'https://a.com/'
    3rd-party(분할): 'https://a.com/^0https://b.com'"""
    if "^" in sk:
        i = sk.index("^")
        return normalize_origin(sk[:i]), sk[i:]
    return normalize_origin(sk), None


def erp_tag(origin, site=False):
    """ERP 주소면 파일 이름용 구분(tag), 아니면 None.
    site=True : HTTP 캐시 키의 '사이트' (포트 없음) - 포트 자리에 'site' 를 넣는다."""
    o = normalize_origin(origin)
    if o == "file://":
        return "file"
    if o.lower() == GITHUB_ORIGIN:
        return "github"
    m = re.fullmatch(r"(https?)://([^/:?#\s]+)(?::(\d+))?", o, re.I)
    if not m:
        return None
    scheme, host, port = m.group(1).lower(), m.group(2).lower(), m.group(3)
    if not port:
        port = "site" if site else ("443" if scheme == "https" else "80")
    https = "-https" if scheme == "https" else ""
    if host in ("localhost", "127.0.0.1"):
        return ("localhost-" if host == "localhost" else "127-") + port + https
    if LAN_HOST_RE.fullmatch(host):
        return "lan-%s-%s%s" % (re.sub(r"[^a-z0-9.-]", "-", host), port, https)
    return None


_LAN_SUFFIXES = ("home.arpa", "quickconnect.to", "synology.me", "myds.me", "diskstation.me", "i234.me", "local", "lan")


def mask_host(host):
    """화면 출력용: 192.168.a.b → 192.168.*.*, 10.a.b.c → 10.*.*.*,
    a-b.my-id.direct.quickconnect.to → a***.quickconnect.to (공용 꼬리만 남기고 이름·ID 는 가림)"""
    h = (host or "").lower()
    m = re.fullmatch(r"(\d+)\.(\d+)\.\d+\.\d+", h)
    if m:
        return "10.*.*.*" if m.group(1) == "10" else "%s.%s.*.*" % (m.group(1), m.group(2))
    for sfx in _LAN_SUFFIXES:
        if h.endswith("." + sfx):
            return h[:1] + "***." + sfx
    i = h.rfind(".")
    return (h[:1] + "***" + h[i:]) if i > 0 else "***"


def mask_origin(origin):
    m = re.fullmatch(r"(https?://)([^/:]+)(:\d+)?", normalize_origin(origin or ""), re.I)
    if not m:
        return origin
    return m.group(1) + mask_host(m.group(2)) + (m.group(3) or "")


def mask_path(p):
    """화면 출력용: 사용자 폴더와 OneDrive 조직 이름을 가림"""
    s = re.sub(r"(?i)^[a-z]:\\users\\[^\\]+", "%USERPROFILE%", p or "")
    return re.sub(r"(?i)(OneDrive - )[^\\]+", r"\1…", s)


def is_lan_origin(origin):
    t = erp_tag(origin) or ""
    return t.startswith("lan-")


_DISP_URL_RE = re.compile(r"(https?://|https?_)(" + LAN_HOST_RE.pattern + r")", re.I)
_DISP_TAG_RE = re.compile(r"(lan-)(" + LAN_HOST_RE.pattern + r")(?=-)", re.I)


def disp(s):
    """화면 출력용: 문자열 안의 LAN/NAS 주소(주소·파일 이름 구분)를 가림"""
    s = _DISP_URL_RE.sub(lambda m: m.group(1) + mask_host(m.group(2)), s or "")
    return _DISP_TAG_RE.sub(lambda m: m.group(1) + mask_host(m.group(2)), s)


def partition_suffix(extra):
    """분할 저장소 꼬리 '^0https://b.com' → 파일 이름용 '-in-b.com'"""
    s = re.sub(r"^\^\d", "", extra or "")
    s = re.sub(r"^[a-z]+://", "", s)
    s = re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-.")[:40]
    return "-in-" + (s or "partition")


def is_erp_storage_key(sk):
    o, _ = split_storage_key(sk)
    return erp_tag(o) is not None


# ================================================================ 공통 도우미
def safe_name(s, empty="PC"):
    s = re.sub(r"[\\/]+", "-", str(s))
    s = re.sub(r"\s+", "", s)
    s = re.sub(r'[:*?"<>|\x00-\x1f]+', "-", s).strip(" .-")
    return s or empty


def now_local_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def dt_local_iso(dt):
    """aware/naive(UTC) datetime → 현지 시각 ISO 문자열"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone().isoformat(timespec="seconds")


def epoch_local_iso(ts):
    if ts is None:
        return None
    return datetime.datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


_CHROME_EPOCH = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)


def chrome_time(us):
    """Chromium 시각(1601-01-01 부터 마이크로초) → aware UTC datetime"""
    try:
        if not us or us <= 0:
            return None
        return _CHROME_EPOCH + datetime.timedelta(microseconds=int(us))
    except (OverflowError, ValueError):
        return None


KO_NAMES = {"Edge": "엣지", "Chrome": "크롬", "Whale": "웨일", "Brave": "브레이브", "Claude": "클로드 앱",
            "Claude-Store": "클로드 앱(스토어)", "Firefox": "파이어폭스", "Default": "기본 프로필"}


def ko(name):
    """화면에 보이는 브라우저·프로필 이름을 한국어로 (파일 이름·JSON 값은 그대로)."""
    name = str(name or "")
    if name in KO_NAMES:
        return KO_NAMES[name]
    if name.startswith("Profile "):
        return "프로필 " + name[8:]
    return name


def fmt_bytes(n):
    if n is None:
        return "-"
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024)
    if n < 1024 * 1024 * 1024:
        return "%.1f MB" % (n / 1048576)
    return "%.2f GB" % (n / 1073741824)


def short_time(iso):
    return iso[:16].replace("T", " ") if iso else "-"


def dir_stats(p):
    """폴더(또는 파일) 의 파일 수, 바이트 수, 가장 늦은 수정 시각(epoch)"""
    p = pathlib.Path(p)
    n = b = 0
    mt = None
    if p.is_file():
        st = p.stat()
        return 1, st.st_size, st.st_mtime
    if not p.is_dir():
        return 0, 0, None
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try:
                st = os.stat(os.path.join(dp, f))
            except OSError:
                continue
            n += 1
            b += st.st_size
            mt = st.st_mtime if mt is None else max(mt, st.st_mtime)
    return n, b, mt


def varint(b, pos=0):
    result = 0
    shift = 0
    while True:
        if pos >= len(b):
            raise ValueError("varint past end")
        c = b[pos]
        pos += 1
        result |= (c & 0x7F) << shift
        shift += 7
        if not c & 0x80:
            return result, pos


def pb_fields(b):
    """아주 단순한 protobuf 해석기: {필드번호: [값...]} (varint=int, 길이지정=bytes)"""
    out = collections.defaultdict(list)
    p = 0
    b = bytes(b)
    while p < len(b):
        key, p = varint(b, p)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, p = varint(b, p)
        elif wt == 2:
            n, p = varint(b, p)
            if p + n > len(b):
                raise ValueError("protobuf length past end")
            v = b[p:p + n]
            p += n
        elif wt == 1:
            v = b[p:p + 8]
            p += 8
        elif wt == 5:
            v = b[p:p + 4]
            p += 4
        else:
            raise ValueError("protobuf wire type %d" % wt)
        out[f].append(v)
    return out


def pb_str(fields, n, default=None):
    v = fields.get(n)
    if not v or not isinstance(v[0], (bytes, bytearray)):
        return default
    return bytes(v[0]).decode("utf-8", "replace")


def pb_int(fields, n, default=None):
    v = fields.get(n)
    if not v or not isinstance(v[0], int):
        return default
    return v[0]


def write_json(path, doc, compact=False):
    """UTF-8(BOM 없음) JSON 저장. 짝 없는 서러게이트가 있으면 \\u 이스케이프(ensure_ascii)로 저장 → 값 그대로 보존"""
    kw = dict(allow_nan=False)
    if compact:
        kw["separators"] = (",", ":")
    else:
        kw["indent"] = 1
    try:
        data = json.dumps(doc, ensure_ascii=False, **kw).encode("utf-8")
    except UnicodeEncodeError:
        data = json.dumps(doc, ensure_ascii=True, **kw).encode("ascii")
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    json.loads(path.read_bytes().decode("utf-8"))  # 다시 읽어 검증
    return len(data)


def unique_path(out_dir, name):
    """이미 있으면 덮어쓰지 않고 _2, _3 … 을 붙인다"""
    p = out_dir / name
    if not p.exists():
        return p
    stem, ext = os.path.splitext(name)
    for i in range(2, 10000):
        q = out_dir / ("%s_%d%s" % (stem, i, ext))
        if not q.exists():
            return q
    raise RuntimeError("too many files named " + name)


# ================================================================ LevelDB (최신 값만)
def _make_crc32c_table():
    tbl = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0x82F63B78 if c & 1 else c >> 1
        tbl.append(c)
    return tbl


_CRC32C_TABLE = _make_crc32c_table()


def crc32c(data):
    crc = 0xFFFFFFFF
    tbl = _CRC32C_TABLE
    for b in data:
        crc = tbl[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


def _leveldb_masked_crc(c):
    return ((((c >> 15) | (c << 17)) & 0xFFFFFFFF) + 0xA282EAD8) & 0xFFFFFFFF


class SafeLogFile(ccl_leveldb.LogFile):
    """.log 파일을 LevelDB 와 같은 규칙으로 읽는다: 조각마다 CRC32C 확인, 잘리거나 깨진 조각과
    끝나지 않은 기록은 버린다 (ccl 원본은 CRC 를 안 봐서, 브라우저가 쓰던 중 복사된 마지막 값이
    잘린 채로 '최신 값' 이 될 수 있음)."""

    dropped = 0

    def _get_batches(self):
        self.dropped = 0
        bs = ccl_leveldb.LogFile.LOG_BLOCK_SIZE
        in_record = False
        start = 0
        parts = []
        for bi, chunk in enumerate(self._get_raw_blocks()):
            p = 0
            while p + 7 <= len(chunk):
                crc, length, btype = struct.unpack_from("<IHB", chunk, p)
                if btype == 0 and length == 0:
                    break  # 블록 끝 0 채움
                if p + 7 + length > len(chunk):
                    self.dropped += 1  # 잘린 조각
                    in_record, parts = False, []
                    break
                data = chunk[p + 7:p + 7 + length]
                if _leveldb_masked_crc(crc32c(bytes([btype]) + data)) != crc:
                    self.dropped += 1  # 깨진 조각 → 이 블록 나머지 버림 (LevelDB 와 같음)
                    in_record, parts = False, []
                    break
                off = bi * bs + p + 7
                p += 7 + length
                if btype == 1:  # Full
                    if in_record:
                        self.dropped += 1
                    in_record, parts = False, []
                    yield off, data
                elif btype == 2:  # First
                    if in_record:
                        self.dropped += 1
                    in_record, start, parts = True, off, [data]
                elif btype == 3:  # Middle
                    if not in_record:
                        self.dropped += 1
                        continue
                    parts.append(data)
                elif btype == 4:  # Last
                    if not in_record:
                        self.dropped += 1
                        continue
                    parts.append(data)
                    in_record = False
                    yield start, b"".join(parts)
                    parts = []
                else:
                    self.dropped += 1
                    in_record, parts = False, []
                    break
        if in_record:
            self.dropped += 1  # 파일 끝에서 끝나지 않은 기록


class SafeRawLevelDb:
    """ccl RawLevelDb 대체: 브라우저가 켜진 채 복사해서 파일 하나가 잘리거나 깨져도 나머지는 읽는다.
    (ccl 원본은 .ldb 하나만 깨져도 전체가 실패하고, 파일 번호를 16진수로 잘못 읽는다)"""

    DATA_FILE_RE = re.compile(r"[0-9]{6}\.(ldb|log|sst)", re.I)

    def __init__(self, in_dir):
        self._in_dir = pathlib.Path(in_dir)
        if not self._in_dir.is_dir():
            raise ValueError("in_dir is not a directory")
        self._files = []
        self.open_errors = []
        for p in sorted(self._in_dir.iterdir()):
            if p.is_file() and self.DATA_FILE_RE.fullmatch(p.name):
                try:
                    if p.suffix.lower() == ".log":
                        self._files.append(SafeLogFile(p))
                    else:
                        self._files.append(ccl_leveldb.LdbFile(p))
                except Exception as e:
                    self.open_errors.append((p.name, "%s: %s" % (type(e).__name__, str(e)[:100])))
        self.manifest = None

    @property
    def in_dir_path(self):
        return self._in_dir

    def iterate_records_raw(self, *, reverse=False):
        for f in sorted(self._files, reverse=reverse, key=lambda x: int(x.path.stem, 10)):
            yield from f

    def close(self):
        for f in self._files:
            try:
                f.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# ccl 의 IndexedDb 도 이 안전한 읽기 클래스를 쓰게 한다
idx.ccl_leveldb.RawLevelDb = SafeRawLevelDb


def apply_version_edits(edits):
    """MANIFEST 의 VersionEdit 들 → (살아있는 테이블 파일 번호 집합, log_number, prev_log_number, last_sequence).
    LevelDB VersionSet::Builder::Apply 와 같은 규칙:
      - 파일은 (레벨, 번호) 쌍으로 추적한다.
      - edit 하나 안에서는 '삭제' 를 먼저, '추가' 를 나중에 적용한다.
    압축 없이 파일을 한 단계 아래 레벨로 내리는 'trivial move' 는 delete(L,n) + add(L+1,n) 이 한 edit 에 함께
    들어 있다. 번호만 보고 추가→삭제 순으로 처리하면 아직 살아있는 파일을 버리게 되어 그 안의 키가 사라지거나
    옛 값으로 되돌아간다 (이전 버전의 버그)."""
    live = set()
    log_number = prev_log = last_seq = None
    for edit in edits:
        for df in edit.deleted_files:
            live.discard((df.level, df.file_no))
        for nf in edit.new_files:
            live.add((nf.level, nf.file_no))
        if edit.log_number is not None:
            log_number = edit.log_number
        if edit.prev_log_number is not None:
            prev_log = edit.prev_log_number
        if edit.last_sequence is not None:
            last_seq = edit.last_sequence
    return {n for _lv, n in live}, log_number, prev_log, last_seq


def _manifest_state(ldb_dir):
    cur = (ldb_dir / "CURRENT").read_text(encoding="ascii", errors="replace").strip()
    if not cur:
        raise ValueError("CURRENT 파일이 비어 있음")
    mf = ccl_leveldb.ManifestFile(ldb_dir / cur)
    try:
        return apply_version_edits(mf)
    finally:
        mf.close()


def _scan_latest(files, warnings):
    """파일들을 읽어 키마다 순번(seq)이 가장 큰 기록만 남긴다 → (latest, 읽은 기록 수)"""
    latest = {}
    raw = 0
    for f in files:
        n_f = 0
        try:
            for rec in f:
                n_f += 1
                raw += 1
                uk = rec.user_key
                prev = latest.get(uk)
                if prev is None or rec.seq > prev.seq:
                    latest[uk] = rec
        except Exception as e:
            warnings.append("%s 읽는 중 중단 (%s) - 앞부분 %d건만 사용 (복사할 때 브라우저가 쓰는 중이었을 수 있음)"
                            % (f.path.name, type(e).__name__, n_f))
        if getattr(f, "dropped", 0):
            warnings.append("%s: 잘리거나 깨진 기록 조각 %d개를 버림 (LevelDB 규칙과 같음, 복사 중 쓰기 의심)"
                            % (f.path.name, f.dropped))
    return latest, raw


def _newer_in_skipped(skipped, latest):
    """MANIFEST 기준으로 버린 파일에 '살아있는 파일의 같은 키보다 새 기록' 이 있는지 센다.
    정상이면 0 이어야 한다 (압축은 최신 기록을 새 파일로 옮기고 나서야 옛 파일을 버리므로).
    0 이 아니면 MANIFEST 해석이 틀렸다는 뜻 → 호출한 쪽에서 모든 파일을 쓰도록 되돌린다."""
    total = 0
    names = []
    for f in skipped:
        c = 0
        try:
            for rec in f:
                cur = latest.get(rec.user_key)
                if cur is not None and rec.seq > cur.seq:
                    c += 1
        except Exception:
            pass
        if c:
            total += c
            names.append(f.path.name)
    return total, names


def read_leveldb_latest(ldb_dir):
    """복사한 LevelDB 폴더에서 키마다 '가장 큰 순번(sequence)' 의 기록 하나만 남긴다 (삭제 기록 포함).
    MANIFEST 가 가리키는 살아있는 파일만 사용(압축 뒤 남은 옛 파일 때문에 지운 키가 되살아나는 것 방지).
    MANIFEST 의 파일이 복사본에 빠져 있으면 데이터 손실을 막기 위해 모든 파일을 사용하고 경고를 남긴다."""
    ldb_dir = pathlib.Path(ldb_dir)
    warnings = []
    manifest_ok = False
    live = set()
    log_no = prev_log = last_seq = None
    try:
        live, log_no, prev_log, last_seq = _manifest_state(ldb_dir)
        manifest_ok = True
    except Exception as e:
        warnings.append("MANIFEST 를 읽지 못해 모든 데이터 파일 사용 (%s: %s)" % (type(e).__name__, str(e)[:120]))
    db = SafeRawLevelDb(ldb_dir)
    try:
        for name, err in db.open_errors:
            warnings.append("%s 열기 실패 - 건너뜀 (%s)" % (name, err))
        files = sorted(db._files, key=lambda f: int(f.path.stem, 10))  # 파일 번호는 10진수
        use = files
        skipped = []
        used_manifest = False
        if manifest_ok:
            present = {int(f.path.stem, 10) for f in files if not isinstance(f, ccl_leveldb.LogFile)}
            missing = sorted(live - present)
            if missing:
                warnings.append("MANIFEST 에 있는 테이블 파일 %d개가 없거나 열리지 않음 (복사 실패 의심) → 모든 파일 사용"
                                % len(missing))
            else:
                used_manifest = True
                use = []
                for f in files:
                    fno = int(f.path.stem, 10)
                    if isinstance(f, ccl_leveldb.LogFile):
                        ok = fno >= (log_no or 0) or (prev_log and fno == prev_log)
                    else:
                        ok = fno in live
                    (use if ok else skipped).append(f)
        scan_warn = []
        latest, raw = _scan_latest(use, scan_warn)
        if used_manifest and skipped:
            newer, where = _newer_in_skipped(skipped, latest)
            if newer:
                warnings.append("MANIFEST 기준으로 버린 파일(%s)에 살아있는 파일보다 새 기록 %d건 → MANIFEST 해석을 "
                                "믿지 않고 모든 파일 사용 (지운 키가 되살아날 수는 있어도 최신 값은 잃지 않음)"
                                % (", ".join(where[:5]), newer))
                used_manifest = False
                use, skipped = files, []
                scan_warn = []
                latest, raw = _scan_latest(use, scan_warn)
        warnings += scan_warn
        info = {
            "filesUsed": [f.path.name for f in use],
            "filesSkippedObsolete": [f.path.name for f in skipped],
            "manifestUsed": used_manifest,
            "manifestLastSeq": last_seq,
            "maxSeq": max((r.seq for r in latest.values()), default=None),
            "rawRecords": raw,
            "distinctKeys": len(latest),
            "liveKeys": sum(1 for r in latest.values() if r.state == ccl_leveldb.KeyState.Live),
            "warnings": warnings,
        }
        return latest, info
    finally:
        db.close()


# ================================================================ localStorage
def decode_prefixed(raw):
    """Chromium localStorage 문자열: 첫 바이트 0 = UTF-16LE, 1 = Latin-1"""
    if not raw:
        return ""
    p = raw[0]
    if p == 0:
        return bytes(raw[1:]).decode("utf-16-le", "surrogatepass")
    if p == 1:
        return bytes(raw[1:]).decode("iso-8859-1")
    raise ValueError("bad string prefix %r" % p)


def parse_localstorage(ldb_dir):
    """→ {storage_key: {...}} (ERP 주소만 값 포함), 비-ERP 주소 수, leveldb 정보"""
    latest, info = read_leveldb_latest(ldb_dir)
    origins = collections.defaultdict(lambda: {"data": {}, "deleted": 0, "storedBytes": 0, "maxSeq": 0,
                                               "metaTime": None, "metaSize": None, "problems": []})
    other = set()
    for uk, rec in latest.items():
        if uk.startswith(b"_"):
            try:
                sk_raw, key_raw = uk[1:].split(b"\x00", 1)
            except ValueError:
                continue
            sk = sk_raw.decode("iso-8859-1")
            if not is_erp_storage_key(sk):
                if rec.state == ccl_leveldb.KeyState.Live:
                    other.add(sk)
                continue
            o = origins[sk]
            o["maxSeq"] = max(o["maxSeq"], rec.seq)
            try:
                k = decode_prefixed(key_raw)
            except Exception as e:
                o["problems"].append("키 해석 실패 seq=%d (%s)" % (rec.seq, type(e).__name__))
                continue
            if rec.state == ccl_leveldb.KeyState.Live:
                try:
                    o["data"][k] = decode_prefixed(rec.value)
                except Exception as e:
                    o["problems"].append("값 해석 실패 key=%s seq=%d (%s)" % (k[:60], rec.seq, type(e).__name__))
                    continue
                o["storedBytes"] += max(len(key_raw) - 1, 0) + max(len(rec.value) - 1, 0)
            else:
                o["deleted"] += 1
        elif uk.startswith(b"META:"):
            sk = uk[5:].decode("iso-8859-1")
            if not is_erp_storage_key(sk) or rec.state != ccl_leveldb.KeyState.Live:
                continue
            try:
                f = pb_fields(rec.value)
                origins[sk]["metaTime"] = chrome_time(pb_int(f, 1))
                origins[sk]["metaSize"] = pb_int(f, 2)
            except Exception:
                pass
    return dict(origins), len(other), info


# ================================================================ IndexedDB (ccl 보정 패치)
_IDB_LDB_INFO = {}


def _cache_records_latest_live(self):
    # 1) 키마다 가장 최신(순번 최대)이면서 살아있는 기록만 사용 (MANIFEST 기준 파일, 삭제 반영)
    latest, info = read_leveldb_latest(self._db.in_dir_path)
    self._fetched_records = [r for r in latest.values() if r.state == ccl_leveldb.KeyState.Live]
    self._ldb_info = info


idx.IndexedDb._cache_records = _cache_records_latest_live


def _blob_file_path(blob_dir, db_id, blob_number):
    # 2) Chromium 실제 경로: <blob폴더>/<db_id hex>/<(n & 0xff00) >> 8 을 2자리 hex>/<n hex>
    return pathlib.Path(blob_dir, "%x" % db_id, "%02x" % ((blob_number & 0xFF00) >> 8), "%x" % blob_number)


def _get_blob_fixed(self, db_id, store_id, raw_key, file_index):
    info = self.get_blob_info(db_id, store_id, raw_key, file_index)
    if self._blob_dir is None:
        raise FileNotFoundError("blob folder not present in copy")
    path = _blob_file_path(self._blob_dir, db_id, info.blob_number)
    if path.exists():
        return path.open("rb")
    raise FileNotFoundError(path)


idx.IndexedDb.get_blob = _get_blob_fixed

# 2b) 외부 객체 종류 2 = File System Access 핸들: varint 길이 + 토큰 바이트 (blob 파일 없음)
_orig_from_stream = idx.IndexedDBExternalObject.from_stream.__func__


@classmethod
def _from_stream(cls, stream):
    pos = stream.tell()
    t = stream.read(1)[0]
    if t == 2:
        n = idx.read_le_varint(stream)
        token = stream.read(n)
        return cls(idx.IndexedDBExternalObjectType.NativeFileSystemHandle, None, None, None, None, None, token)
    stream.seek(pos)
    return _orig_from_stream(cls, stream)


idx.IndexedDBExternalObject.from_stream = _from_stream


# 3) V8 one-byte 문자열은 Latin-1 (ccl 은 ASCII 가 아니면 bytes 를 돌려줌)
def _read_one_byte_string(self):
    length = self._read_le_varint()[0]
    return self._read_raw(length).decode("latin-1")


v8.Deserializer._read_one_byte_string = _read_one_byte_string


# 4) Map / Set / ArrayBuffer / TypedArray / Date / RegExp / BigInt 표시용 클래스
class JSMap:
    def __init__(self):
        self.entries = []


class JSSet:
    def __init__(self):
        self.values = []


class JSArrayBuffer:
    def __init__(self, raw):
        self.raw = raw


class JSTypedArray:
    def __init__(self, name, raw):
        self.name = name
        self.raw = raw


class JSRegExp:
    def __init__(self, source, flags):
        self.source = source
        self.flags = flags


class JSBigInt:
    def __init__(self, v):
        self.v = v


class JSDate:
    def __init__(self, ms):
        self.ms = ms


def _read_js_map(self):
    result = JSMap()
    self._objects.append(result)
    while True:
        if self._peek_tag() == v8.Constants.token_kEndJSMap:
            break
        k = self._read_object()
        val = self._read_object()
        result.entries.append((k, val))
    assert self._read_tag() == v8.Constants.token_kEndJSMap
    expected = self._read_le_varint()[0]
    if expected != len(result.entries) * 2:
        raise ValueError("Map count mismatch")
    return result


v8.Deserializer._read_js_map = _read_js_map


def _read_js_set(self):
    result = JSSet()
    self._objects.append(result)
    while True:
        if self._peek_tag() == v8.Constants.token_kEndJSSet:
            break
        result.values.append(self._read_object())
    assert self._read_tag() == v8.Constants.token_kEndJSSet
    expected = self._read_le_varint()[0]
    if expected != len(result.values):
        raise ValueError("Set count mismatch")
    return result


v8.Deserializer._read_js_set = _read_js_set


def _read_js_arraybuffer(self):
    length = self._read_le_varint()[0]
    raw = self._read_raw(length)
    ab = JSArrayBuffer(raw)
    self._objects.append(ab)
    return ab


v8.Deserializer._read_js_arraybuffer = _read_js_arraybuffer

_VIEW_NAMES = {"b": "Int8Array", "B": "Uint8Array", "C": "Uint8ClampedArray", "w": "Int16Array",
               "W": "Uint16Array", "d": "Int32Array", "D": "Uint32Array", "f": "Float32Array",
               "F": "Float64Array", "q": "BigInt64Array", "Q": "BigUint64Array", "?": "DataView",
               "h": "Float16Array"}


def _wrap_view(self, ab):
    raw = ab.raw if isinstance(ab, JSArrayBuffer) else ab
    tag = chr(self._read_le_varint()[0])
    off = self._read_le_varint()[0]
    ln = self._read_le_varint()[0]
    if self.version >= 14:
        self._read_le_varint()
    view = JSTypedArray(_VIEW_NAMES.get(tag, "TypedArray_" + tag), raw[off:off + ln])
    self._objects.append(view)
    return view


v8.Deserializer._wrap_js_array_buffer_view = _wrap_view


def _read_date(self):
    d = JSDate(self._read_double())
    self._objects.append(d)
    return d


v8.Deserializer._read_date = _read_date


def _read_js_regex(self):
    pattern = self._read_string()
    flags = self._read_le_varint()[0]
    r = JSRegExp(pattern, flags)
    self._objects.append(r)
    return r


v8.Deserializer._read_js_regex = _read_js_regex

_orig_bigint = v8.Deserializer._read_bigint


def _read_bigint(self):
    return JSBigInt(_orig_bigint(self))


v8.Deserializer._read_bigint = _read_bigint


def str_with_len(b, pos):
    n, pos = varint(b, pos)
    return bytes(b[pos:pos + n * 2]).decode("utf-16-be"), pos + n * 2


def decode_keypath(b):
    if b is None:
        return None
    if len(b) < 3 or b[0] != 0 or b[1] != 0:
        return bytes(b).decode("utf-16-be")  # 옛 문자열 keyPath
    t = b[2]
    if t == 0:
        return None
    if t == 1:
        return str_with_len(b, 3)[0]
    if t == 2:
        n, pos = varint(b, 3)
        out = []
        for _ in range(n):
            s, pos = str_with_len(b, pos)
            out.append(s)
        return out
    raise ValueError("unknown keypath type %d" % t)


def js_number(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        if x.is_integer() and abs(x) <= 2 ** 53:
            return int(x)
        return x
    return x


def ms_to_iso(ms):
    if ms is None or math.isnan(ms) or math.isinf(ms):
        return None
    try:
        dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=ms)
    except OverflowError:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (dt.microsecond // 1000)


def data_url(mime, raw):
    return "data:%s;base64," % (mime or "application/octet-stream") + base64.b64encode(raw).decode("ascii")


def js_key_str(k):
    if isinstance(k, str):
        return k
    if isinstance(k, (int, float)) and not isinstance(k, bool):
        k2 = js_number(k)
        return str(k2) if k2 is not None else "NaN"
    return str(k)


_FSA_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|\\\\[^\\\x00-\x1f]{1,80}\\)[^\x00-\x1f�\"*?<>|]{2,400}")


def _pb_len_before(buf, pos):
    """buf[pos] 바로 앞이 'protobuf 태그(길이지정형) + 길이 varint' 이면 그 길이, 아니면 None"""
    for n in (2, 1, 3):
        s = pos - n
        if s < 1:
            continue
        if buf[s - 1] & 7 != 2:  # 앞 바이트가 길이지정형(wire type 2) 태그여야 함
            continue
        try:
            v, e = varint(buf, s)
        except ValueError:
            continue
        if e == pos and 0 < v <= len(buf) - pos:
            return v
    return None


def fsa_token_paths(token):
    """File System Access 핸들 토큰(바이트) 안에 들어 있는 대상 파일/폴더 경로를 꺼낸다.
    토큰은 protobuf 이고 경로는 보통 UTF-16LE(판에 따라 UTF-8) 이므로 둘 다 보고, 경로 앞의 길이 값이
    있으면 그 길이로 정확히 자른다 (없으면 경로처럼 보이는 글자까지)."""
    if not token:
        return []
    buf = bytes(token)
    found = []

    def add(p):
        p = (p or "").rstrip(" .")
        if len(p) >= 4 and p not in found:
            found.append(p)

    for off in (0, 1):  # UTF-16LE (짝수/홀수 위치)
        b = buf[off:]
        t = b[:len(b) // 2 * 2].decode("utf-16-le", "replace")
        for m in _FSA_PATH_RE.finditer(t):
            pos = off + 2 * m.start()
            n = _pb_len_before(buf, pos)
            if n and n % 2 == 0:
                add(buf[pos:pos + n].decode("utf-16-le", "replace"))
            else:
                add(m.group(0))
    t = buf.decode("latin-1")  # UTF-8 (바이트 위치를 그대로 쓰려고 latin-1 로 훑음)
    for m in _FSA_PATH_RE.finditer(t):
        pos = m.start()
        n = _pb_len_before(buf, pos)
        raw = buf[pos:pos + n] if n else m.group(0).encode("latin-1")
        try:
            add(raw.decode("utf-8"))
        except UnicodeDecodeError:
            pass
    return found


class IdbEncoder:
    """IndexedDB 값 → data-backup.html ser() 와 같은 JSON 표현"""

    def __init__(self, record, db_id, blob_dir, stats, blob_refs, handles=None, where=None):
        self.record = record
        self.db_id = db_id
        self.blob_dir = blob_dir
        self.stats = stats
        self.blob_refs = blob_refs
        self.handles = handles
        self.where = where or {}
        self.stack = set()

    def enc(self, v):
        if v is None:
            return None
        if isinstance(v, v8._Undefined):
            return None  # 배열 안 undefined → null (객체 속성은 호출한 쪽에서 생략)
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return js_number(v)
        if isinstance(v, str):
            return v
        if isinstance(v, (bytes, bytearray)):
            self.stats["bytes_fallback"] += 1
            return {"__type": "ArrayBuffer", "base64": base64.b64encode(bytes(v)).decode("ascii")}
        if isinstance(v, JSDate):
            return {"__type": "Date", "iso": ms_to_iso(v.ms)}
        if isinstance(v, datetime.datetime):
            return {"__type": "Date", "iso": v.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (v.microsecond // 1000)}
        if isinstance(v, JSBigInt):
            self.stats["bigint"] += 1
            return {"__type": "BigInt", "value": str(v.v)}
        if isinstance(v, JSArrayBuffer):
            self.stats["arraybuffer"] += 1
            return {"__type": "ArrayBuffer", "base64": base64.b64encode(v.raw).decode("ascii")}
        if isinstance(v, JSTypedArray):
            self.stats["typedarray"] += 1
            return {"__type": v.name, "base64": base64.b64encode(v.raw).decode("ascii")}
        if isinstance(v, JSRegExp):
            return {"__type": "RegExp", "source": v.source, "flags": v.flags}
        if isinstance(v, tuple):
            return [self.enc(x) for x in v]
        if isinstance(v, blink.BlobIndex):
            return self.enc_blob(v)
        if isinstance(v, blink.NativeFileHandle):
            self.stats["filesystem_handles"] += 1
            out = {"__type": "FileSystemHandle", "kind": "directory" if v.is_dir else "file", "name": v.name,
                   "note": "File System Access handle; browser-internal permission token, cannot be recreated "
                           "by a restore - the user has to pick the folder/file again"}
            try:
                info = self.record.owner.get_blob_info(self.db_id, self.record.obj_store_id,
                                                       self.record.key.raw_key, v.token_index)
                if info.native_file_token is not None:
                    out["tokenBase64"] = base64.b64encode(info.native_file_token).decode("ascii")
                    paths = fsa_token_paths(info.native_file_token)
                    if paths:
                        out["targetPath"] = paths[0]  # 이 핸들이 가리키던 실제 파일/폴더 (ERP 데이터 파일일 수 있음)
                        if len(paths) > 1:
                            out["targetPathCandidates"] = paths
            except Exception as e:
                out["tokenError"] = type(e).__name__
            if self.handles is not None:
                h = dict(self.where)
                h.update({"kind": out["kind"], "name": out.get("name"), "targetPath": out.get("targetPath")})
                self.handles.append(h)
            return out
        if isinstance(v, (dict, list, JSMap, JSSet)):
            oid = id(v)
            if oid in self.stack:
                self.stats["cycles"] += 1
                return {"__type": "CircularRef"}
            self.stack.add(oid)
            try:
                if isinstance(v, dict):
                    out = {}
                    for k, val in v.items():
                        if isinstance(val, v8._Undefined):
                            continue  # JSON.stringify 처럼 undefined 속성은 생략
                        out[js_key_str(k)] = self.enc(val)
                    return out
                if isinstance(v, list):
                    return [self.enc(x) for x in v]
                if isinstance(v, JSMap):
                    return {"__type": "Map", "entries": [[self.enc(a), self.enc(b)] for a, b in v.entries]}
                return {"__type": "Set", "values": [self.enc(x) for x in v.values]}
            finally:
                self.stack.discard(oid)
        self.stats["unknown_type:" + type(v).__name__] += 1
        return {"__type": "Unsupported", "pyType": type(v).__name__, "repr": None}

    def enc_blob(self, bi):
        info = self.record.resolve_blob_index(bi)
        raw = None
        if self.blob_dir is not None:
            p = _blob_file_path(self.blob_dir, self.db_id, info.blob_number)
            if p.exists():
                raw = p.read_bytes()
        self.blob_refs.append((info.blob_number, raw is not None))
        self.stats["blob_objects"] += 1
        is_file = info.object_type == idx.IndexedDBExternalObjectType.File
        out = {"__type": "Blob", "mime": info.mime_type or "", "name": info.file_name if is_file else None}
        if is_file and info.last_modified is not None:
            out["lastModified"] = int((info.last_modified - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
        if raw is not None:
            out["dataURL"] = data_url(info.mime_type, raw)
            out["size"] = len(raw)
        else:
            out["dataURL"] = None
            out["missing"] = True
            out["size"] = info.size
        return out


def count_data_urls(v):
    """값 안의 'data:…' 문자열(사진 등) 개수 - Blob 객체는 따로 센다"""
    n = 0
    stack = [v]
    while stack:
        x = stack.pop()
        if isinstance(x, str):
            if x.startswith("data:"):
                n += 1
        elif isinstance(x, dict):
            if x.get("__type") != "Blob":
                stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)
    return n


def enc_idb_key(k):
    t = k.key_type
    if t == idx.IdbKeyType.String:
        return k.value
    if t == idx.IdbKeyType.Number:
        return js_number(k.value)
    if t == idx.IdbKeyType.Date:
        return {"__type": "Date", "iso": ms_to_iso(struct.unpack("<d", k.raw_key[1:9])[0])}
    if t == idx.IdbKeyType.Array:
        return [enc_idb_key(x) for x in k.value]
    if t == idx.IdbKeyType.Binary:
        return {"__type": "ArrayBuffer", "base64": base64.b64encode(bytes(k.value)).decode("ascii")}
    return None


def key_sort_tuple(k):
    # IndexedDB 키 순서: Number < Date < String < Binary < Array
    t = k.key_type
    if t == idx.IdbKeyType.Number:
        return (1, k.value)
    if t == idx.IdbKeyType.Date:
        return (2, struct.unpack("<d", k.raw_key[1:9])[0])
    if t == idx.IdbKeyType.String:
        return (3, k.value.encode("utf-16-be", "surrogatepass"))
    if t == idx.IdbKeyType.Binary:
        return (4, bytes(k.value))
    if t == idx.IdbKeyType.Array:
        return (5, tuple(key_sort_tuple(x) for x in k.value))
    return (0, 0)


def parse_indexeddb(ldb_dir, blob_dir):
    """IndexedDB leveldb(+blob) 복사본 → (indexedDB dict, 요약)"""
    blob_dir = pathlib.Path(blob_dir) if blob_dir and pathlib.Path(blob_dir).is_dir() else None
    stats = collections.Counter()
    blob_refs = []
    handles = []
    db = idx.IndexedDb(str(ldb_dir), str(blob_dir) if blob_dir else None)
    try:
        ldb_info = getattr(db, "_ldb_info", {})
        live = db._fetched_records

        def rec_by_prefix(prefix):
            return [r for r in live if r.user_key.startswith(prefix)]

        result = {}
        report = {}
        referenced = set()
        missing_blob_files = 0
        origin_ids = sorted({d.origin for d in db.global_metadata.db_ids})
        for dbid in sorted(db.global_metadata.db_ids, key=lambda d: d.name):
            db_no = dbid.dbid_no
            meta_prefix = idx.IndexedDb.make_prefix(db_no, 0, 0)
            version = None
            for r in rec_by_prefix(meta_prefix):
                rest = r.user_key[len(meta_prefix):]
                if len(rest) == 1 and rest[0] == 4:
                    version = varint(r.value)[0] if r.value else None
                    if version is not None and version >= 2 ** 63:
                        version -= 2 ** 64
            stores_meta = collections.defaultdict(dict)
            osp = meta_prefix + bytes([50])
            for r in rec_by_prefix(osp):
                rest = r.user_key[len(osp):]
                sid, pos = varint(rest)
                if pos >= len(rest):
                    continue
                stores_meta[sid][rest[pos]] = r.value
            idx_meta = collections.defaultdict(lambda: collections.defaultdict(dict))
            ixp = meta_prefix + bytes([100])
            for r in rec_by_prefix(ixp):
                rest = r.user_key[len(ixp):]
                sid, pos = varint(rest)
                iid, pos = varint(rest, pos)
                if pos >= len(rest):
                    continue
                idx_meta[sid][iid][rest[pos]] = r.value

            db_out = {"version": version, "stores": {}}
            db_rep = {"version": version, "stores": {}}
            for sid in sorted(stores_meta):
                sm = stores_meta[sid]
                if 0 not in sm:
                    continue
                sname = bytes(sm[0]).decode("utf-16-be")
                keypath = decode_keypath(sm.get(1))
                autoinc = bool(sm.get(2) and sm[2][0])
                indexes = []
                for iid in sorted(idx_meta.get(sid, {})):
                    im = idx_meta[sid][iid]
                    if 0 not in im:
                        continue
                    indexes.append({"name": bytes(im[0]).decode("utf-16-be"), "keyPath": decode_keypath(im.get(2)),
                                    "unique": bool(im.get(1) and im[1][0]),
                                    "multiEntry": bool(im.get(3) and im[3][0])})
                # blob 목록 (index id 3)
                bprefix = idx.IndexedDb.make_prefix(db_no, sid, 3)
                store_blobs = []
                for r in rec_by_prefix(bprefix):
                    buff = io.BytesIO(r.value)
                    while buff.tell() < len(r.value):
                        o = idx.IndexedDBExternalObject.from_stream(buff)
                        if o.blob_number is None:
                            continue
                        found = False
                        size_ok = False
                        if blob_dir is not None:
                            p = _blob_file_path(blob_dir, db_no, o.blob_number)
                            found = p.exists()
                            size_ok = found and (o.size is None or p.stat().st_size == o.size)
                        referenced.add((db_no, o.blob_number))
                        store_blobs.append((found, size_ok))
                        if not found:
                            missing_blob_files += 1
                # 레코드 (index id 1)
                dprefix = idx.IndexedDb.make_prefix(db_no, sid, 1)
                items = []
                errors = []
                n_external = 0
                for r in rec_by_prefix(dprefix):
                    key = idx.IdbKey(r.user_key[len(dprefix):])
                    k_enc = enc_idb_key(key)
                    try:
                        _vv, vr = idx._le_varint_from_bytes(r.value)
                        body = r.value[len(vr):]
                        external = len(body) > 3 and body[0] == 0xFF and body[1] == 0x11 and body[2] == 0x01
                        pre = db.read_record_precursor(key, db_no, sid, body, None)
                        if pre is None:
                            raise ValueError("external value info missing")
                        _bver, obj_raw, _trailer, ext = pre
                        val = v8.Deserializer(obj_raw, host_object_delegate=blink.BlinkV8Deserializer().read).read()
                        wrapped = idx.IndexedDbRecord(db, db_no, sid, key, val, True, r.seq, r.origin_file, ext)
                        where = {"database": dbid.name, "store": sname, "key": k_enc}
                        v_enc = IdbEncoder(wrapped, db_no, blob_dir, stats, blob_refs, handles, where).enc(val)
                        stats["dataUrlStrings"] += count_data_urls(v_enc)
                        if external:
                            n_external += 1
                        items.append((key_sort_tuple(key), {"key": k_enc, "value": v_enc}))
                    except Exception as e:
                        errors.append("%s: %s" % (type(e).__name__, str(e)[:160]))
                        items.append((key_sort_tuple(key), {"key": k_enc, "value": None, "__error": type(e).__name__,
                                                            "__rawBase64": base64.b64encode(r.value).decode("ascii")}))
                items.sort(key=lambda t: t[0])
                records = [x[1] for x in items]
                db_out["stores"][sname] = {"keyPath": keypath, "autoIncrement": autoinc, "indexes": indexes,
                                           "records": records}
                db_rep["stores"][sname] = {"records": len(records), "externallyStoredValues": n_external,
                                           "decodeErrors": len(errors), "errorSamples": sorted(set(errors))[:3],
                                           "blobEntries": len(store_blobs),
                                           "blobFilesFound": sum(1 for b in store_blobs if b[0]),
                                           "blobSizeMatches": sum(1 for b in store_blobs if b[1])}
            result[dbid.name] = db_out
            report[dbid.name] = db_rep

        disk_blobs = [f for f in blob_dir.rglob("*") if f.is_file()] if blob_dir else []
        orphans = 0
        for f in disk_blobs:
            try:
                key = (int(f.parent.parent.name, 16), int(f.name, 16))
            except ValueError:
                orphans += 1
                continue
            if key not in referenced:
                orphans += 1
        summary = {
            "databases": report,
            "records": sum(s["records"] for d in report.values() for s in d["stores"].values()),
            "decodeErrors": sum(s["decodeErrors"] for d in report.values() for s in d["stores"].values()),
            "blobObjectsInValues": len(blob_refs),
            "dataUrlStringsInValues": stats.get("dataUrlStrings", 0),
            "blobObjectsMissingFile": sum(1 for b in blob_refs if not b[1]),
            "blobFilesOnDisk": len(disk_blobs),
            "blobBytesOnDisk": sum(f.stat().st_size for f in disk_blobs),
            "blobFilesReferencedByLiveRecords": len(referenced),
            "missingBlobFiles": missing_blob_files,
            "orphanBlobFiles": orphans,
            "fileSystemHandles": handles,
            "valueTypeStats": dict(stats),
            "leveldbRawRecords": ldb_info.get("rawRecords"),
            "leveldbLiveKeysUsed": ldb_info.get("liveKeys"),
            "leveldbDeletedKeysSkipped": (ldb_info.get("distinctKeys") or 0) - (ldb_info.get("liveKeys") or 0),
            "leveldbMaxSeq": ldb_info.get("maxSeq"),
            "leveldbFilesUsed": len(ldb_info.get("filesUsed") or []),
            "leveldbObsoleteFilesSkipped": len(ldb_info.get("filesSkippedObsolete") or []),
            "warnings": list(ldb_info.get("warnings") or []),
            "chromiumOriginIds": origin_ids,
        }
        return result, summary
    finally:
        try:
            db.close()
        except Exception:
            pass


def idb_dirname_to_origin(name):
    """'https_jachungu29.github.io_0.indexeddb.leveldb' → 'https://jachungu29.github.io'
       'file__0.indexeddb.leveldb' → 'file://', 'http_localhost_8791…' → 'http://localhost:8791'"""
    base = re.sub(r"\.indexeddb\.leveldb$", "", name)
    base = re.sub(r"@\d+$", "", base)
    m = re.fullmatch(r"([a-z][a-z0-9+.-]*)_(.*)_(\d+)", base)
    if not m:
        return None
    scheme, host, port = m.groups()
    if scheme == "file":
        return "file://"
    return "%s://%s" % (scheme, host) + ("" if port == "0" else ":" + port)


# ================================================================ QuotaManager (버킷 → 주소)
def read_bucket_map(profile_dir, warnings):
    """WebStorage/QuotaManager(SQLite) → {bucket_id(str): {storageKey, name, lastModifiedLocal}}.
    원본을 건드리지 않도록 임시 폴더에 복사해서 연다."""
    qm = profile_dir / "WebStorage" / "QuotaManager"
    if not qm.is_file():
        return {}
    tmpd = tempfile.mkdtemp(prefix="sjerp_qm_")
    try:
        dst = pathlib.Path(tmpd) / "QuotaManager"
        shutil.copyfile(qm, dst)
        for sfx in ("-journal", "-wal"):
            s = qm.with_name(qm.name + sfx)
            if s.is_file():
                shutil.copyfile(s, dst.with_name(dst.name + sfx))
        con = sqlite3.connect(str(dst))
        try:
            out = {}
            for row in con.execute("SELECT id, storage_key, name, last_modified FROM buckets"):
                lm = chrome_time(row[3])
                out[str(row[0])] = {"storageKey": row[1], "name": row[2], "lastModifiedLocal": dt_local_iso(lm)}
            return out
        finally:
            con.close()
    except Exception as e:
        warnings.append("QuotaManager 읽기 실패 (%s: %s)" % (type(e).__name__, str(e)[:120]))
        return {}
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


# ================================================================ CacheStorage
RESPONSE_TYPES = {0: "basic", 1: "cors", 2: "default", 3: "error", 4: "opaque", 5: "opaqueredirect"}


def parse_cs_index(path):
    f = pb_fields(path.read_bytes())
    caches = []
    for c in f.get(1, []):
        cf = pb_fields(c)
        caches.append({"name": pb_str(cf, 1, ""), "dir": pb_str(cf, 2), "size": pb_int(cf, 3)})
    return {"caches": caches, "origin": pb_str(f, 2), "storageKey": pb_str(f, 3)}


def is_text_type(ct):
    return bool(ct) and bool(TEXT_CT_RE.search(ct))


def parse_cache_entries(cache_dir):
    """CacheStorage 캐시 폴더(SimpleCache 형식) → data-backup.html 과 같은 항목 목록"""
    entries = []
    pat = re.compile(r"^[0-9a-f]{16}_0$")
    files = sorted(f for f in pathlib.Path(cache_dir).iterdir() if f.is_file() and pat.match(f.name))
    for f in files:
        e = {}
        try:
            with ccache.SimpleCacheFile(f) as cf:
                url = cf.key
                s0 = cf.get_stream_0()
                s1 = cf.get_stream_1()
        except Exception as ex:
            entries.append({"url": None, "file": f.name, "error": "%s: %s" % (type(ex).__name__, str(ex)[:120])})
            continue
        e["url"] = url
        try:
            md = pb_fields(s0) if s0 else {}
            req = pb_fields(md[1][0]) if md.get(1) else {}
            resp = pb_fields(md[2][0]) if md.get(2) else {}
            headers = {}
            for h in resp.get(4, []):
                hf = pb_fields(h)
                headers[(pb_str(hf, 1, "") or "").lower()] = pb_str(hf, 2, "")
            e["method"] = pb_str(req, 1, "GET")
            e["status"] = pb_int(resp, 1)
            e["type"] = RESPONSE_TYPES.get(pb_int(resp, 3), pb_int(resp, 3))
            e["contentType"] = headers.get("content-type", "") or pb_str(resp, 13, "") or ""
            try:
                e["contentLength"] = int(headers.get("content-length")) or None
            except (TypeError, ValueError):
                e["contentLength"] = None
            e["dateHeader"] = headers.get("date")
            rt = chrome_time(pb_int(resp, 6))
            et = chrome_time(pb_int(md, 3))
            e["responseTimeLocal"] = dt_local_iso(rt)
            e["entryTimeLocal"] = dt_local_iso(et)
        except Exception as ex:
            e["metadataError"] = "%s: %s" % (type(ex).__name__, str(ex)[:120])
        is_data = bool(DATA_URL_RE.search(url or "")) or bool(re.search("json", e.get("contentType") or "", re.I))
        e["isData"] = is_data
        e["bodySize"] = len(s1)
        if is_data or is_text_type(e.get("contentType")):
            try:
                e["body"] = s1.decode("utf-8")
            except UnicodeDecodeError:
                e["bodyBase64"] = base64.b64encode(s1).decode("ascii")
            e["bodyIncluded"] = True
        else:
            e["bodyIncluded"] = False
        entries.append(e)
    return entries


def guess_cache_origin(base):
    """index.txt 가 아직 없을 때(브라우저가 늦게 씀): 항목 URL 중 ERP 주소가 있으면 그 주소로 추정"""
    cnt = collections.Counter()
    pat = re.compile(r"^[0-9a-f]{16}_0$")
    for d in base.iterdir():
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if not (f.is_file() and pat.match(f.name)):
                continue
            try:
                with ccache.SimpleCacheFile(f) as cf:
                    url = cf.key
            except Exception:
                continue
            m = re.match(r"^([a-z][a-z0-9+.-]*://[^/?#]*)", url or "", re.I)
            if m and erp_tag(m.group(1)):
                cnt[normalize_origin(m.group(1))] += 1
    return cnt.most_common(1)[0][0] if cnt else None


def list_cache_origin_dirs(profile_dir, bucket_map, warnings):
    """→ [(storage_key, 캐시기준폴더(index.txt 있는 곳), 출처설명)]"""
    out = []
    legacy = profile_dir / "Service Worker" / "CacheStorage"
    if legacy.is_dir():
        for d in sorted(legacy.iterdir()):
            if d.is_dir():
                out.append((d, "Service Worker/CacheStorage/" + d.name, None))
    ws = profile_dir / "WebStorage"
    if ws.is_dir():
        for d in sorted(ws.iterdir()):
            if d.is_dir() and (d / "CacheStorage").is_dir():
                out.append((d / "CacheStorage", "WebStorage/%s/CacheStorage" % d.name, d.name))
    res = []
    for base, rel, bucket in out:
        sk = None
        idx_info = None
        ip = base / "index.txt"
        if ip.is_file():
            try:
                idx_info = parse_cs_index(ip)
                sk = idx_info.get("storageKey") or idx_info.get("origin")
            except Exception as e:
                warnings.append("%s/index.txt 해석 실패 (%s)" % (rel, type(e).__name__))
        if not sk and bucket and bucket in bucket_map:
            sk = bucket_map[bucket]["storageKey"]
        if not sk:
            try:
                sk = guess_cache_origin(base)
            except Exception:
                sk = None
            if sk:
                warnings.append("%s: index.txt 가 없어 항목 URL 로 주소를 %s 로 추정" % (rel, sk))
        res.append((sk, base, rel, idx_info))
    return res


def parse_cache_origin(base, idx_info):
    """한 주소의 CacheStorage → ({캐시이름: [항목]}, 요약)"""
    caches = collections.OrderedDict()
    listed_dirs = set()
    notes = []
    for c in (idx_info or {}).get("caches", []):
        d = c.get("dir")
        if d:
            listed_dirs.add(d)
        name = c.get("name") or "(이름없음)"
        if name in caches:
            name = "%s (%s)" % (name, d)
        cd = base / d if d else None
        if cd is not None and cd.is_dir():
            caches[name] = parse_cache_entries(cd)
        else:
            caches[name] = []
            notes.append("캐시 '%s' 폴더가 복사본에 없음" % c.get("name"))
    for d in sorted(base.iterdir()):
        if d.is_dir() and d.name not in listed_dirs and re.fullmatch(r"[0-9a-fA-F-]{36}", d.name):
            caches["(index.txt 에 없는 캐시 폴더) " + d.name] = parse_cache_entries(d)
            notes.append("index.txt 에 없는 캐시 폴더 %s 도 읽음" % d.name)
    return caches, notes


def summarize_cache(caches):
    ents = [e for v in caches.values() for e in v]
    supa = [e for e in ents if e.get("url") and DATA_URL_RE.search(e["url"])]
    tables = sorted({m.group(1) for e in supa for m in [re.search(r"/rest/v1/([^/?#]+)", e["url"])] if m})
    times = [e.get("entryTimeLocal") or e.get("responseTimeLocal") for e in ents]
    times = [t for t in times if t]
    return {"caches": len(caches), "cacheNames": list(caches.keys()), "entries": len(ents),
            "dataEntries": sum(1 for e in ents if e.get("isData")),
            "bodiesIncluded": sum(1 for e in ents if e.get("bodyIncluded")),
            "bodyBytes": sum(e.get("bodySize") or 0 for e in ents),
            "supabaseEntries": len(supa), "supabaseTablesSeen": tables,
            "entryErrors": sum(1 for e in ents if e.get("error") or e.get("metadataError")),
            "lastEntryLocal": max(times) if times else None}


# ================================================================ HTTP 디스크 캐시 (Cache/Cache_Data)
# fetch() 로 받은 응답이 서비스워커와 상관없이 남는 곳. file:// 로 연 ERP 는 서비스워커를 쓸 수 없으므로
# 옛 Supabase 응답이 남아 있다면 여기가 유일한 후보다. 캐시 키는 '1/0/_dk_<최상위 사이트> <프레임 사이트> <URL>'
# (이중 키) 이므로, 최상위 사이트가 ERP 주소인 항목만 내보낸다 (다른 사이트 캐시는 개수만 셈).
HTTP_CACHE_NAME = "(HTTP 디스크 캐시)"
_SITE_MARK_RE = re.compile(r"^(?:[a-z]{1,3}_)+(?=[a-z][a-z0-9+.-]*:)")


def split_http_cache_key(raw):
    """HTTP 캐시 키 → (최상위 사이트, 프레임 사이트, URL). 이중 키가 아니면 (None, None, URL)"""
    k = re.sub(r"^\d+/(?:\d+/)?", "", raw or "", count=1)
    if k.startswith("_dk_"):
        parts = k[4:].split(" ", 2)
        if len(parts) == 3:
            top, frame, url = parts
            return _SITE_MARK_RE.sub("", top), _SITE_MARK_RE.sub("", frame), url
    return None, None, k


def decode_content(raw, encoding):
    """Content-Encoding 풀기 → (bytes 또는 None, 설명 또는 None). HTTP 캐시는 받은 그대로(압축된 채) 저장함"""
    encs = [x.strip() for x in (encoding or "").lower().split(",")]
    encs = [x for x in encs if x and x != "identity"]
    data = raw
    try:
        for e in reversed(encs):
            if e in ("gzip", "x-gzip"):
                data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
            elif e == "deflate":
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    data = zlib.decompress(data, -zlib.MAX_WBITS)
            elif e == "br":
                try:
                    import brotli
                except ImportError:
                    return None, "br(브로틀리) 압축 - 'pip install brotli' 후 다시 실행하면 풀림"
                data = brotli.decompress(data)
            elif e == "zstd":
                try:
                    import zstandard
                except ImportError:
                    return None, "zstd 압축 - 'pip install zstandard' 후 다시 실행하면 풀림"
                data = zstandard.ZstdDecompressor().decompressobj().decompress(data)
            else:
                return None, "알 수 없는 압축 방식 %s" % e
    except Exception as ex:
        return None, "압축 풀기 실패 (%s)" % type(ex).__name__
    return data, None


def _http_entry(url, top, frame, md, body):
    e = {"url": url, "method": "GET", "topFrameSite": top, "frameSite": frame}
    if md is not None:
        status_line = next((d for d in md.http_header_declarations if d.upper().startswith("HTTP/")), None)
        m = re.match(r"HTTP/\S+\s+(\d{3})", status_line or "")
        e["status"] = int(m.group(1)) if m else None
        e["statusLine"] = status_line

        def first(name):
            v = md.get_attribute(name)
            return v[0] if v else None
        e["contentType"] = first("content-type") or ""
        e["contentEncoding"] = ",".join(md.get_attribute("content-encoding")) or None
        cl = first("content-length")
        e["contentLength"] = int(cl) if cl and cl.isdigit() else None
        e["dateHeader"] = first("date")
        e["cacheControl"] = first("cache-control")
        e["contentRange"] = first("content-range")
        e["responseTimeLocal"] = dt_local_iso(md.response_time)
        e["requestTimeLocal"] = dt_local_iso(md.request_time)
    else:
        e["metadataMissing"] = True
    is_data = bool(DATA_URL_RE.search(url or "")) or bool(re.search("json", e.get("contentType") or "", re.I))
    e["isData"] = is_data
    e["bodySize"] = len(body) if body is not None else 0
    if body is None:
        e["bodyIncluded"] = False
        e["bodyMissing"] = True
        return e
    if not is_data:
        e["bodyIncluded"] = False
        return e
    dec, note = decode_content(body, e.get("contentEncoding"))
    if dec is None:
        e["bodyBase64"] = base64.b64encode(body).decode("ascii")
        e["bodyNote"] = note + " (bodyBase64 = 압축된 원본 그대로)"
    else:
        e["bodyDecodedSize"] = len(dec)
        try:
            e["body"] = dec.decode("utf-8")
        except UnicodeDecodeError:
            e["bodyBase64"] = base64.b64encode(dec).decode("ascii")
    if e.get("contentRange") or (e.get("status") == 206):
        e["bodyNote"] = (e.get("bodyNote", "") + " 부분 응답(206) - 본문 일부만 있을 수 있음").strip()
    e["bodyIncluded"] = True
    return e


def parse_http_cache(pdir, warnings):
    """<프로필>/Cache/Cache_Data 복사본 → ({최상위사이트: [항목]}, 요약). 없으면 (None, None)"""
    d = pdir / "Cache" / "Cache_Data"
    if not d.is_dir():
        return None, None
    cls = ccache.guess_cache_class(d)
    if cls is None:
        warnings.append("Cache/Cache_Data: 캐시 형식을 알 수 없음 (index/data_* 파일 없음) - 건너뜀")
        return None, None
    # ccl 은 깨진 항목을 만나면 원본 바이트를 stderr 로 찍으므로(다른 사이트 데이터일 수 있음) 화면에 내보내지 않음
    err = io.StringIO()
    per_site = collections.OrderedDict()
    summ = {"source": "Cache/Cache_Data", "format": cls.__name__, "keys": 0, "erpKeys": 0, "nonErpKeys": 0,
            "undecoratedDataKeys": 0, "entryErrors": 0, "loaderMessages": 0}
    with contextlib.redirect_stderr(err):
        cache = cls(d)
    try:
        for raw in sorted(cache.keys()):
            summ["keys"] += 1
            top, frame, url = split_http_cache_key(raw)
            if not top or erp_tag(top, site=True) is None:
                if top is None and DATA_URL_RE.search(url or ""):
                    summ["undecoratedDataKeys"] += 1  # 옛 형식(사이트 구분 없는) Supabase 키 - 주인 불명이라 내보내지 않음
                else:
                    summ["nonErpKeys"] += 1
                continue
            summ["erpKeys"] += 1
            metas, bodies = [None], [None]
            try:
                with contextlib.redirect_stderr(err):
                    metas = cache.get_metadata(raw) or [None]
            except Exception:
                summ["entryErrors"] += 1
            try:
                with contextlib.redirect_stderr(err):
                    bodies = cache.get_cachefile(raw) or [None]
            except Exception:
                summ["entryErrors"] += 1
            for i in range(max(len(metas), len(bodies))):
                md = metas[i] if i < len(metas) else None
                body = bodies[i] if i < len(bodies) else None
                per_site.setdefault(normalize_origin(top), []).append(_http_entry(url, top, frame, md, body))
    finally:
        try:
            cache.close()
        except Exception:
            pass
    summ["loaderMessages"] = len([ln for ln in err.getvalue().splitlines() if ln.strip()])
    return per_site, summ


# ================================================================ 서비스워커 등록
def parse_sw_registrations(profile_dir):
    """Service Worker/Database → {origin: [{scope, script, lastUpdateCheckLocal}]} (ERP 주소만), 비-ERP 등록 수"""
    d = profile_dir / "Service Worker" / "Database"
    if not d.is_dir():
        return None, 0
    latest, _info = read_leveldb_latest(d)
    out = collections.defaultdict(list)
    other = 0
    for uk, rec in latest.items():
        if not uk.startswith(b"REG:") or rec.state != ccl_leveldb.KeyState.Live:
            continue
        sk = uk[4:].split(b"\x00", 1)[0].decode("utf-8", "replace")
        o, _ = split_storage_key(sk)
        if erp_tag(o) is None:
            other += 1
            continue
        try:
            f = pb_fields(rec.value)
            out[o].append({"scope": pb_str(f, 2), "script": pb_str(f, 3),
                           "lastUpdateCheckLocal": dt_local_iso(chrome_time(pb_int(f, 7)))})
        except Exception as e:
            out[o].append({"error": type(e).__name__})
    return dict(out), other


# ================================================================ 원본 폴더 탐색
CHROMIUM_MARKERS = ("Local Storage", "IndexedDB", "Service Worker", "WebStorage", "Cache")


def find_chromium_profiles(run):
    """원본 폴더 안에서 Chromium 프로필 폴더(= Local Storage/IndexedDB/… 를 바로 품은 폴더) 찾기
    → [(브라우저, 프로필, 경로)]"""
    found = []
    for dp, dn, fn in os.walk(run):
        p = pathlib.Path(dp)
        if any(m in dn for m in CHROMIUM_MARKERS):
            rel = p.relative_to(run).parts
            if not rel:
                continue
            browser = rel[0]
            profile = "/".join(rel[1:]) or "Default"
            found.append((browser, profile, p))
            dn[:] = [x for x in dn if x not in CHROMIUM_MARKERS]  # 프로필 안쪽은 더 내려가지 않음
    return found


def find_firefox(run):
    """Firefox 원본(storage/default/…, webappsstore.sqlite) → 크기만 보고"""
    res = {}
    for dp, dn, fn in os.walk(run):
        p = pathlib.Path(dp)
        if p.name == "default" and p.parent.name == "storage":
            prof = p.parent.parent
            ent = res.setdefault(str(prof.relative_to(run)), {"originDirs": [], "webappsstore": []})
            for d in sorted(p.iterdir()):
                if d.is_dir():
                    n, b, mt = dir_stats(d)
                    ent["originDirs"].append({"name": d.name, "files": n, "bytes": b, "lastModifiedLocal": epoch_local_iso(mt)})
        for f in fn:
            if f.startswith("webappsstore.sqlite"):
                prof = p
                ent = res.setdefault(str(prof.relative_to(run)), {"originDirs": [], "webappsstore": []})
                st = (p / f).stat()
                ent["webappsstore"].append({"name": f, "bytes": st.st_size, "lastModifiedLocal": epoch_local_iso(st.st_mtime)})
    return [{"profile": k, **v, "note": "수동 분석 필요 (Firefox 형식은 이 도구가 자동 변환하지 않음)"}
            for k, v in sorted(res.items())]


def verify_sums(run):
    """SHA256SUMS.txt 가 있으면 무결성 확인 (읽기만)"""
    sums = run / "SHA256SUMS.txt"
    if not sums.is_file():
        return None
    res = {"checked": 0, "mismatch": [], "missing": [], "unparsed": 0}
    raw = sums.read_bytes()
    if raw[:2] in (bytes([0xFF, 0xFE]), bytes([0xFE, 0xFF])):  # UTF-16 BOM (PowerShell 5.1 Out-File 기본)
        encs = ("utf-16",)
    else:
        encs = ("utf-8-sig", "cp949", "latin-1")
    text = ""
    for enc in encs:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.search(r"(?<![0-9A-Fa-f])([0-9A-Fa-f]{64})(?![0-9A-Fa-f])", line)
        if not m:
            res["unparsed"] += 1
            continue
        h = m.group(1).lower()
        rel = (line[:m.start()] + line[m.end():]).strip(" \t*,;|\"'")
        rel = rel.replace("\\", "/")
        if re.match(r"^[A-Za-z]:/", rel) or rel.startswith("/"):
            i = rel.find("/" + run.name + "/")  # 절대 경로로 적혀 있으면 원본 폴더 이름 뒤만 사용
            rel = rel[i + len(run.name) + 2:] if i >= 0 else rel
        while rel.startswith("./"):
            rel = rel[2:]
        if not rel:
            res["unparsed"] += 1
            continue
        p = run / rel
        if not p.is_file():
            res["missing"].append(rel)
            continue
        hh = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                hh.update(chunk)
        res["checked"] += 1
        if hh.hexdigest() != h:
            res["mismatch"].append(rel)
    return res


def as_list(x):
    """PowerShell 5.1 ConvertTo-Json 은 원소 1개짜리 배열을 객체로 풀어 버리므로 다시 목록으로"""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def manifest_digest(man):
    """manifest.json 요약 (필드가 없거나 모양이 달라도 멈추지 않게)"""
    browsers = []
    failed = 0
    for b in as_list(man.get("browsers")):
        if not isinstance(b, dict):
            continue
        profs = []
        for p in as_list(b.get("profiles")):
            if isinstance(p, dict):
                nf = len(as_list(p.get("failed")))
                failed += nf
                profs.append({"name": p.get("name"), "copied": len(as_list(p.get("copied"))),
                              "skipped": len(as_list(p.get("skipped"))), "failed": nf, "hints": p.get("hints")})
            else:
                profs.append({"name": str(p)})
        browsers.append({"name": b.get("name"), "profiles": profs})
    totals = man.get("totals") if isinstance(man.get("totals"), dict) else None
    if totals and isinstance(totals.get("failed"), int):
        failed = max(failed, totals["failed"])
    return {"browsers": browsers, "firefoxProfiles": len(as_list(man.get("firefox"))), "totals": totals,
            "psVersion": man.get("psVersion"), "copyFailures": failed}


# ================================================================ 문서 만들기
def base_meta(ctx, browser, profile, origin, section, last_local):
    return {
        "pcName": ctx["label"],
        "browser": browser,
        "profile": profile,
        "origin": origin,
        "source": "raw-copy",
        "createdLocal": ctx["now"],
        "storageLastModifiedLocal": last_local,
        "sectionsIncluded": [section],
        "extractor": EXTRACTOR,
        "rawCopy": {"folder": ctx["run"].name, "computerName": ctx["computerName"],
                    "createdLocal": ctx["rawCreated"]},
    }


def doc_of(meta, ls=None, idb=None, cs=None):
    return {"format": "SEUNGJEONG_ERP_BROWSER_BACKUP", "version": 1, "meta": meta,
            "localStorage": ls or {}, "indexedDB": idb or {}, "cacheStorage": cs or {}}


SECTION_NOTE = ("이 파일에는 %s 만 들어 있습니다. 같은 주소의 다른 저장소는 별도 파일이며, 여기서 비어 있는 항목은 "
                "'지우라'는 뜻이 아닙니다 (복원 도구는 clear()/deleteDatabase 금지, 합치기만).")


def out_name(ctx, browser, profile, tag, storage):
    parts = ["승정ERP_디스크추출", safe_name(ctx["label"]), safe_name(browser, "Browser")]
    if profile != "Default":
        parts.append(safe_name(profile, "Profile"))
    parts += [tag, storage]
    return "_".join(parts) + ".json"


def emit(ctx, name, doc, compact=False):
    p = unique_path(ctx["out"], name)
    size = write_json(p, doc, compact=compact)
    ctx["outputs"].append({"file": p.name, "bytes": size, "renamed": p.name != name})
    return p


# ================================================================ 프로필 하나 처리
def process_profile(ctx, browser, profile, pdir):
    rep = {"browser": browser, "profile": profile, "path": str(pdir.relative_to(ctx["run"])),
           "localStorage": {}, "indexedDB": {}, "cacheStorage": {}, "httpCache": {}, "serviceWorkers": {},
           "nonErpOrigins": {}, "fileSystemHandles": [], "warnings": [], "incomplete": [], "errors": []}
    hints = {"fileIdb": False, "githubIdb": False, "localhostIdb": [], "lanIdb": [], "erpSwCache": False,
             "httpCacheSupabase": False}

    # ---- localStorage
    lsdir = pdir / "Local Storage" / "leveldb"
    if lsdir.is_dir():
        try:
            origins, n_other, info = parse_localstorage(lsdir)
            rep["nonErpOrigins"]["localStorage"] = n_other
            rep["warnings"] += ["localStorage: " + w for w in info["warnings"]]
            for sk in sorted(origins):
                o = origins[sk]
                origin, extra = split_storage_key(sk)
                tag = erp_tag(origin) + (partition_suffix(extra) if extra else "")
                data = dict(sorted(o["data"].items()))
                last_utc = o["metaTime"]
                r = {"storageKey": sk, "keys": len(data), "deletedKeys": o["deleted"], "storedBytes": o["storedBytes"],
                     "lastModifiedLocal": dt_local_iso(last_utc), "originMaxSeq": o["maxSeq"],
                     "problems": o["problems"], "file": None}
                sb = sorted(k for k in data if re.match(r"^sb-.+-auth-token", k) or "supabase" in k.lower())
                sv = sorted(k for k, v in data.items() if "supabase.co" in v)
                if sb or sv:
                    r["supabaseKeyNames"] = sb
                    r["keysMentioningSupabase"] = sv
                if data:
                    meta = base_meta(ctx, browser, profile, origin, "localStorage", dt_local_iso(last_utc))
                    meta.update({
                        "storageLastModifiedUTC": (last_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if last_utc else None),
                        "keyCount": len(data),
                        "totalChars": sum(len(k) + len(v) for k, v in data.items()),
                        "storedBytes": o["storedBytes"],
                        "chromiumMetaSizeBytes": o["metaSize"],
                        "deletedKeysWhoseLatestRecordIsDeletion": o["deleted"],
                        "flagKeysPresent": sorted(k for k, v in data.items() if len(v) <= 1),
                        "leveldbMaxSeq": info["maxSeq"],
                        "originMaxSeq": o["maxSeq"],
                        "leveldbFilesUsed": info["filesUsed"],
                        "leveldbObsoleteFilesSkipped": info["filesSkippedObsolete"],
                        "warnings": info["warnings"] + o["problems"],
                        "notes": ("'%s/%s/Local Storage/leveldb' 원본 복사본에서 추출. 값은 원래 문자열 그대로이며 "
                                  "1글자 플래그 키까지 모두 포함 (복원 때 그대로 넣어야 ERP 가 첫 실행 초기화로 "
                                  "데이터를 지우지 않음). 키마다 가장 최신 기록만 사용, 마지막 기록이 삭제인 키 %d개는 "
                                  "제외. flagKeysPresent = 값이 1글자 이하인 키(보호 플래그 후보). "
                                  % (browser, profile, o["deleted"])) + (SECTION_NOTE % "localStorage"),
                    })
                    if extra:
                        meta["partitionedStorageKey"] = sk
                    if origin == "file://":
                        meta["notes"] += (" file:// 은 PC 에서 더블클릭으로 연 모든 HTML 이 함께 쓰는 하나의 주소입니다."
                                          " 크롬/엣지 한도(주소당 약 10MB) 대비 사용량 %.0f%%."
                                          % (100.0 * o["storedBytes"] / (10 * 1024 * 1024)))
                    p = emit(ctx, out_name(ctx, browser, profile, tag, "localStorage"), doc_of(meta, ls=data))
                    r["file"] = p.name
                rep["localStorage"][sk] = r
        except Exception as e:
            rep["errors"].append("localStorage 분석 실패: %s: %s" % (type(e).__name__, str(e)[:200]))

    bucket_map = read_bucket_map(pdir, rep["warnings"])

    # ---- IndexedDB (옛 방식 IndexedDB/<주소>.indexeddb.leveldb + 새 방식 WebStorage/<버킷>/IndexedDB)
    idb_sources = []
    other_idb = set()
    idb_root = pdir / "IndexedDB"
    if idb_root.is_dir():
        for d in sorted(idb_root.iterdir()):
            if d.is_dir() and d.name.endswith(".indexeddb.leveldb"):
                o = idb_dirname_to_origin(d.name)
                blob = d.with_name(d.name[:-len(".leveldb")] + ".blob")
                if o and erp_tag(o):
                    idb_sources.append((o, None, d, blob, "IndexedDB/" + d.name))
                else:
                    other_idb.add(d.name)
    ws = pdir / "WebStorage"
    if ws.is_dir():
        for d in sorted(ws.iterdir()):
            ldb = d / "IndexedDB" / "indexeddb.leveldb"
            if d.is_dir() and ldb.is_dir():
                sk = (bucket_map.get(d.name) or {}).get("storageKey")
                if not sk:
                    rep["warnings"].append("WebStorage/%s IndexedDB: 버킷 주소를 알 수 없음 (QuotaManager 없음) - 건너뜀"
                                           % d.name)
                    continue
                o, extra = split_storage_key(sk)
                if erp_tag(o):
                    idb_sources.append((o, extra, ldb, d / "IndexedDB" / "indexeddb.blob",
                                        "WebStorage/%s/IndexedDB" % d.name))
                else:
                    other_idb.add("bucket:" + d.name)
    rep["nonErpOrigins"]["indexedDB"] = len(other_idb)
    used_tags = set()
    for origin, extra, ldb, blob, rel in idb_sources:
        tag = erp_tag(origin) + (partition_suffix(extra) if extra else "")
        if tag in used_tags:
            tag += "-" + safe_name(rel.split("/")[1] if rel.startswith("WebStorage") else "legacy")
        used_tags.add(tag)
        r = {"source": rel, "databases": 0, "records": 0, "file": None}
        try:
            n1, b1, m1 = dir_stats(ldb)
            n2, b2, m2 = dir_stats(blob)
            last = max([m for m in (m1, m2) if m is not None], default=None)
            result, summ = parse_indexeddb(ldb, blob)
            r.update({"databases": len(result), "records": summ["records"], "decodeErrors": summ["decodeErrors"],
                      "blobObjects": summ["blobObjectsInValues"], "blobMissing": summ["blobObjectsMissingFile"],
                      "dataUrlStrings": summ["dataUrlStringsInValues"],
                      "leveldbBytes": b1, "blobBytes": b2, "lastModifiedLocal": epoch_local_iso(last),
                      "databaseNames": sorted(result)})
            if result:
                meta = base_meta(ctx, browser, profile, origin, "indexedDB", epoch_local_iso(last))
                meta["storageLastModifiedNote"] = "복사된 leveldb/blob 파일의 마지막 수정 시각 기준"
                meta["summary"] = summ
                meta["sourceFolder"] = rel
                if extra:
                    meta["partitionStorageKeyTail"] = extra
                meta["notes"] = ("'%s' 원본 복사본에서 추출. 키마다 가장 최신 기록만 사용(삭제 반영). 브라우저가 "
                                 "leveldb 밖(.blob 폴더)에 따로 저장한 큰 값은 풀어서 원래 값으로 넣음. 사진 등 "
                                 "Blob/File 은 {__type:'Blob',mime,name,dataURL} 로 저장. undefined 속성은 생략 "
                                 "(JSON.stringify 와 같음). " % rel) + (SECTION_NOTE % "IndexedDB")
                p = emit(ctx, out_name(ctx, browser, profile, tag, "indexedDB"), doc_of(meta, idb=result),
                         compact=True)
                r["file"] = p.name
                t = erp_tag(origin)
                if t == "file":
                    hints["fileIdb"] = True
                elif t == "github":
                    hints["githubIdb"] = True
                elif t.startswith("lan-"):
                    hints["lanIdb"].append(origin)
                else:
                    hints["localhostIdb"].append(origin)
            if summ["warnings"]:
                rep["warnings"] += ["IndexedDB %s: %s" % (rel, w) for w in summ["warnings"]]
            # 풀지 못한 레코드 / 없는 blob 파일 = 그 값은 결과 파일에 비어 있음 → 눈에 띄게 알리고 종료 코드 2
            n_bad = summ["decodeErrors"]
            n_miss = max(summ["missingBlobFiles"], summ["blobObjectsMissingFile"])
            r["missingBlobFiles"] = summ["missingBlobFiles"]
            if n_bad or n_miss:
                msg = ("%s: 풀지 못한 레코드 %d건 / 없는 첨부 조각 파일 %d개 - 이 값들은 결과 파일에서 비어 있음 "
                       "(value:null + __error, 또는 Blob missing). 복사 도중 ERP 를 쓰고 있었을 수 있으니 브라우저를 "
                       "모두 닫고 백업을 다시 하세요." % (rel, n_bad, n_miss))
                rep["warnings"].append(msg)
                rep["incomplete"].append(msg)
            for h in summ.get("fileSystemHandles") or []:
                hh = dict(h)
                hh["origin"] = origin
                rep["fileSystemHandles"].append(hh)
        except Exception as e:
            rep["errors"].append("IndexedDB %s 분석 실패: %s: %s" % (rel, type(e).__name__, str(e)[:200]))
        rkey = origin + (extra or "") + (" [%s]" % rel if rel.startswith("WebStorage") else "")
        rep["indexedDB"][rkey] = r

    # ---- CacheStorage
    try:
        cs_dirs = list_cache_origin_dirs(pdir, bucket_map, rep["warnings"])
    except Exception as e:
        cs_dirs = []
        rep["errors"].append("CacheStorage 목록 실패: %s: %s" % (type(e).__name__, str(e)[:200]))
    per_origin = collections.OrderedDict()
    n_other_cs = 0
    for sk, base, rel, idx_info in cs_dirs:
        if not sk:
            rep["warnings"].append("%s: 주소를 알 수 없음 (index.txt 없고 ERP 주소 항목도 없음) - 건너뜀" % rel)
            continue
        origin, extra = split_storage_key(sk)
        if erp_tag(origin) is None:
            n_other_cs += 1
            continue
        per_origin.setdefault((origin, extra), []).append((base, rel, idx_info))
    rep["nonErpOrigins"]["cacheStorage"] = n_other_cs
    for (origin, extra), items in per_origin.items():
        tag = erp_tag(origin) + (partition_suffix(extra) if extra else "")
        merged = collections.OrderedDict()
        notes = []
        rels = []
        try:
            for base, rel, idx_info in items:
                caches, nts = parse_cache_origin(base, idx_info)
                rels.append(rel)
                notes += nts
                for name, ents in caches.items():
                    nm = name if name not in merged else "%s (%s)" % (name, rel)
                    merged[nm] = ents
            summ = summarize_cache(merged)
            summ["sources"] = rels
            summ["notes"] = notes
            if merged:
                hints["erpSwCache"] = True  # ERP 주소의 서비스워커 캐시 (보통 'sj-erp-shell-v1')
            r = dict(summ)
            r["file"] = None
            if merged:
                meta = base_meta(ctx, browser, profile, origin, "cacheStorage", summ["lastEntryLocal"])
                meta["scanSummary"] = summ
                meta["notes"] = ("CacheStorage(서비스워커 캐시) 원본 복사본에서 추출. 항목마다 url·상태·content-type·"
                                 "날짜를 기록하고, JSON/텍스트 응답과 Supabase(supabase.co, /rest/v1/, /storage/v1/) "
                                 "응답은 본문(body, 글자가 아니면 bodyBase64)까지 포함. "
                                 + (SECTION_NOTE % "cacheStorage"))
                p = emit(ctx, out_name(ctx, browser, profile, tag, "cacheStorage"), doc_of(meta, cs=merged))
                r["file"] = p.name
            rep["cacheStorage"][origin + (extra or "")] = r
        except Exception as e:
            rep["errors"].append("CacheStorage %s 분석 실패: %s: %s" % (origin, type(e).__name__, str(e)[:200]))

    # ---- HTTP 디스크 캐시 (백업 도구가 Supabase 흔적을 찾았을 때만 복사되어 있음)
    try:
        per_site, hsum = parse_http_cache(pdir, rep["warnings"])
    except Exception as e:
        per_site, hsum = None, None
        rep["errors"].append("HTTP 디스크 캐시 분석 실패: %s: %s" % (type(e).__name__, str(e)[:200]))
    if hsum is not None:
        rep["nonErpOrigins"]["httpCacheKeys"] = hsum["nonErpKeys"]
        if hsum["undecoratedDataKeys"]:
            rep["warnings"].append("HTTP 캐시: 사이트 구분이 없는 옛 형식의 Supabase/REST 항목 %d개 - 어느 사이트 것인지 "
                                   "알 수 없어 내보내지 않음 (원본 복사본에는 남아 있음)" % hsum["undecoratedDataKeys"])
        for site, ents in per_site.items():
            tag = erp_tag(site, site=True)
            summ = summarize_cache({HTTP_CACHE_NAME: ents})
            summ.update({"sources": [hsum["source"]], "cacheFormat": hsum["format"], "allKeysInCache": hsum["keys"],
                         "bodiesMissing": sum(1 for e in ents if e.get("bodyMissing")),
                         "bodiesStillCompressed": sum(1 for e in ents if e.get("bodyNote", "").startswith(("br", "zstd"))),
                         "file": None})
            if summ["supabaseEntries"]:
                hints["httpCacheSupabase"] = True
            meta = base_meta(ctx, browser, profile, site, "cacheStorage", summ["lastEntryLocal"])
            meta["cacheKind"] = "httpDiskCache"
            meta["scanSummary"] = summ
            meta["notes"] = ("HTTP 디스크 캐시(Cache/Cache_Data) 원본 복사본에서 추출. 서비스워커 캐시가 아니며 cacheStorage "
                             "모양만 빌려 쓴 것이므로 caches 로 복원하지 마세요. 최상위 사이트(topFrameSite)가 이 주소인 "
                             "항목만 포함. 항목마다 url·상태·content-type·날짜를 기록하고, JSON 과 Supabase(supabase.co, "
                             "/rest/v1/, /storage/v1/) 응답은 본문까지 포함 (gzip/deflate/br 은 풀어서 body, 못 풀면 "
                             "bodyBase64 + bodyNote). " + (SECTION_NOTE % "HTTP 디스크 캐시"))
            p = emit(ctx, out_name(ctx, browser, profile, tag, "httpCache"), doc_of(meta, cs={HTTP_CACHE_NAME: ents}))
            summ["file"] = p.name
            rep["httpCache"][site] = summ
        if hsum["erpKeys"] == 0:
            rep["httpCache"]["(ERP 주소 항목 없음)"] = {"entries": 0, "supabaseEntries": 0, "allKeysInCache": hsum["keys"],
                                                   "file": None}

    # ---- 서비스워커 등록
    try:
        regs, n_other_sw = parse_sw_registrations(pdir)
        if regs is not None:
            rep["serviceWorkers"] = regs
            rep["nonErpOrigins"]["serviceWorkerRegistrations"] = n_other_sw
    except Exception as e:
        rep["warnings"].append("서비스워커 등록 정보 읽기 실패: %s" % type(e).__name__)

    rep["hints"] = hints
    return rep


# ================================================================ 화면 출력
def print_profile(rep):
    print("")
    print("[%s / %s]  (%s)" % (ko(rep["browser"]), ko(rep["profile"]), rep["path"]))
    if rep["localStorage"]:
        for sk, r in rep["localStorage"].items():
            print("  저장값        %-32s %4d키  %9s  마지막 변경 %s%s" % (
                disp(sk), r["keys"], fmt_bytes(r["storedBytes"]), short_time(r["lastModifiedLocal"]),
                "" if r["file"] else "  (살아있는 키 없음 - 파일 안 만듦)"))
            if r.get("supabaseKeyNames") or r.get("keysMentioningSupabase"):
                print("      옛 인터넷 DB 관련 키: %s" % ", ".join((r.get("supabaseKeyNames") or [])
                                                        + (r.get("keysMentioningSupabase") or [])))
    else:
        print("  저장값        ERP 주소 없음")
    if rep["indexedDB"]:
        for o, r in rep["indexedDB"].items():
            print("  사진·자료     %-32s %d개 DB · %d건 · 사진등(그림 %d · 파일 %d)%s%s · %s  마지막 변경 %s" % (
                disp(o), r.get("databases", 0), r.get("records", 0), r.get("dataUrlStrings", 0), r.get("blobObjects", 0),
                (" (파일없음 %d)" % r["blobMissing"]) if r.get("blobMissing") else "",
                (" (풀지 못함 %d)" % r["decodeErrors"]) if r.get("decodeErrors") else "",
                fmt_bytes((r.get("leveldbBytes") or 0) + (r.get("blobBytes") or 0)),
                short_time(r.get("lastModifiedLocal"))))
    else:
        print("  사진·자료     ERP 주소 없음")
    for h in rep.get("fileSystemHandles") or []:
        print("      연결된 파일(파일 핸들 %s/%s): %s" % (h.get("database"), h.get("store"),
                                                 mask_path(h.get("targetPath")) or "(경로를 읽지 못함)"))
    if rep["cacheStorage"]:
        for o, r in rep["cacheStorage"].items():
            print("  앱 저장본     %-32s 보관함 %d개 · 항목 %d개 · 데이터응답 %d개 · 옛 인터넷 DB %d개 · %s" % (
                disp(o), r["caches"], r["entries"], r["dataEntries"], r["supabaseEntries"], fmt_bytes(r["bodyBytes"])))
            print("      보관함 이름: %s" % ", ".join(r["cacheNames"]))
    else:
        print("  앱 저장본     ERP 주소 없음")
    for o, r in (rep.get("httpCache") or {}).items():
        if not r.get("entries"):
            print("  임시인터넷파일 복사본 있음 (전체 %d개 항목) - ERP 주소에서 받은 항목 없음" % r.get("allKeysInCache", 0))
            continue
        print("  임시인터넷파일 %-32s 항목 %d개 · 데이터응답 %d개 · 옛 인터넷 DB %d개 · 본문 %s%s" % (
            disp(o), r["entries"], r["dataEntries"], r["supabaseEntries"], fmt_bytes(r["bodyBytes"]),
            (" (br/zstd 미해제 %d - pip install brotli)" % r["bodiesStillCompressed"])
            if r.get("bodiesStillCompressed") else ""))
    if rep["serviceWorkers"]:
        for o, regs in rep["serviceWorkers"].items():
            print("  앱 저장 기능  %-32s 등록 %d개" % (disp(o), len(regs)))
    no = rep["nonErpOrigins"]
    if no:
        print("  (ERP 외 사이트 - 내보내지 않음: 저장값 %s곳, 사진·자료 %s곳, 앱 저장본 %s곳%s)" % (
            no.get("localStorage", 0), no.get("indexedDB", 0), no.get("cacheStorage", 0),
            (", 임시 인터넷 파일 항목 %s개" % no["httpCacheKeys"]) if "httpCacheKeys" in no else ""))
    for w in rep["warnings"]:
        print("  [주의] " + disp(w))
    for e in rep["errors"]:
        print("  [오류] " + disp(e))


# ================================================================ main
def main(argv=None):
    ap = argparse.ArgumentParser(description="승정ERP 브라우저 원본 복사본 → ERP 백업 JSON 변환")
    ap.add_argument("run_folder", nargs="?", help="브라우저백업.bat 이 만든 '브라우저원본_<PC>_<시각>' 폴더")
    ap.add_argument("--out", help="결과를 둘 폴더 (기본: 원본 폴더의 상위 폴더)")
    ap.add_argument("--label", help="파일 이름에 쓸 PC 이름 (기본: manifest.json 의 computerName)")
    ap.add_argument("--self-test", action="store_true", help="LevelDB MANIFEST 해석 등 내부 점검만 하고 끝냄")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.run_folder:
        ap.print_usage()
        print("[오류] 원본 폴더를 지정하세요.")
        return 1

    run = pathlib.Path(args.run_folder).expanduser()
    if run.is_file() and run.name.lower() == "manifest.json":
        run = run.parent
    run = run.resolve()
    if not run.is_dir():
        print("[오류] 원본 폴더가 없습니다: %s" % run)
        return 1

    warnings = []
    manifest = {}
    mp = run / "manifest.json"
    if mp.is_file():
        try:
            mraw = mp.read_bytes()
            if mraw[:2] in (bytes([0xFF, 0xFE]), bytes([0xFE, 0xFF])):
                manifest = json.loads(mraw.decode("utf-16"))
            else:
                manifest = json.loads(mraw.decode("utf-8-sig"))
            if not isinstance(manifest, dict):
                raise ValueError("manifest 최상위가 객체가 아님")
            if manifest.get("format") != "SEUNGJEONG_ERP_RAW_BROWSER_COPY":
                warnings.append("manifest.json 형식 이름이 다릅니다: %r" % manifest.get("format"))
        except Exception as e:
            warnings.append("manifest.json 을 읽지 못함 (%s)" % type(e).__name__)
            manifest = {}
    else:
        warnings.append("manifest.json 이 없습니다 - 폴더 구조만 보고 분석합니다")

    m = re.match(r"^브라우저원본_(.+)_(\d{8}-\d{6})$", run.name)
    computer = manifest.get("computerName") or (m.group(1) if m else None) or "PC"
    label = args.label or computer
    out = pathlib.Path(args.out).expanduser().resolve() if args.out else run.parent
    try:
        out.relative_to(run)
        print("[오류] 출력 폴더가 원본 폴더 안에 있습니다. 원본은 수정하면 안 되므로 다른 폴더를 지정하세요.")
        return 1
    except ValueError:
        pass
    out.mkdir(parents=True, exist_ok=True)

    ctx = {"run": run, "out": out, "label": label, "computerName": computer,
           "rawCreated": manifest.get("createdLocal"), "now": now_local_iso(), "outputs": []}

    print("=" * 78)
    print(" 승정 ERP - 브라우저 원본 복사본 분석")
    print("=" * 78)
    print(" 원본 폴더 : %s" % run)
    print(" 복사한 PC : %s   복사 시각: %s" % (computer, ctx["rawCreated"] or "-"))
    print(" PC 이름   : %s  (결과 파일 이름에 사용)" % label)
    print(" 출력 폴더 : %s" % out)

    sums = None
    try:
        sums = verify_sums(run)
    except Exception as e:
        warnings.append("SHA256SUMS.txt 확인 실패 (%s)" % type(e).__name__)
    if sums is not None:
        print(" 무결성    : SHA256 %d개 확인, 불일치 %d개, 없음 %d개" % (
            sums["checked"], len(sums["mismatch"]), len(sums["missing"])))
        if sums["missing"]:
            warnings.append("SHA256SUMS.txt 에 있으나 폴더에 없는 파일 %d개 (옮기다 빠졌거나 목록 형식을 못 읽음)"
                            % len(sums["missing"]))
        if sums["mismatch"]:
            warnings.append("SHA256 불일치 파일 %d개 (복사/이동 중 손상 의심): %s"
                            % (len(sums["mismatch"]), ", ".join(sums["mismatch"][:10])))

    md = manifest_digest(manifest)
    if md["copyFailures"]:
        print(" 복사 실패 : %d개 (manifest.json 의 failed 목록 참고 - 해당 파일은 분석에서 빠짐)" % md["copyFailures"])
        warnings.append("원본 복사 때 실패한 파일 %d개 (manifest.json failed)" % md["copyFailures"])
    profiles = find_chromium_profiles(run)
    try:
        firefox = find_firefox(run)
    except Exception as e:
        firefox = []
        warnings.append("Firefox 폴더 확인 실패 (%s)" % type(e).__name__)
    if not profiles and not firefox:
        print("[오류] 이 폴더에서 브라우저 저장소를 찾지 못했습니다. '브라우저원본_…' 폴더를 지정했는지 확인하세요.")
        return 1

    reports = []
    for browser, profile, pdir in profiles:
        try:
            rep = process_profile(ctx, browser, profile, pdir)
        except Exception as e:
            rep = {"browser": browser, "profile": profile, "path": str(pdir.relative_to(run)),
                   "localStorage": {}, "indexedDB": {}, "cacheStorage": {}, "httpCache": {}, "serviceWorkers": {},
                   "nonErpOrigins": {}, "fileSystemHandles": [], "warnings": [], "incomplete": [],
                   "errors": ["프로필 분석 실패: %s: %s" % (type(e).__name__, str(e)[:200])]}
        reports.append(rep)
        print_profile(rep)

    for f in firefox:
        print("")
        print("[파이어폭스 %s]  %s" % (f["profile"], f["note"]))
        for d in f["originDirs"]:
            print("  storage/default/%-40s %9s  마지막 변경 %s" % (d["name"], fmt_bytes(d["bytes"]),
                                                            short_time(d["lastModifiedLocal"])))
        for w in f["webappsstore"]:
            print("  %-56s %9s" % (w["name"], fmt_bytes(w["bytes"])))

    # ---- Supabase 발견 여부 (서비스워커 캐시 / HTTP 디스크 캐시 따로)
    supa = {"sw": {"n": 0, "tables": set(), "where": []}, "http": {"n": 0, "tables": set(), "where": []}}
    supa_ls = []
    http_present = []
    for rep in reports:
        for kind, block in (("sw", rep["cacheStorage"]), ("http", rep.get("httpCache") or {})):
            for o, r in block.items():
                if r.get("supabaseEntries"):
                    supa[kind]["n"] += r["supabaseEntries"]
                    supa[kind]["tables"].update(r.get("supabaseTablesSeen") or [])
                    supa[kind]["where"].append("%s/%s %s (%d개)" % (rep["browser"], rep["profile"], o,
                                                                   r["supabaseEntries"]))
        if rep.get("httpCache"):
            http_present.append("%s/%s" % (ko(rep["browser"]), ko(rep["profile"])))
        for sk, r in rep["localStorage"].items():
            if r.get("supabaseKeyNames") or r.get("keysMentioningSupabase"):
                supa_ls.append("%s/%s %s" % (rep["browser"], rep["profile"], sk))
    supa_total = supa["sw"]["n"] + supa["http"]["n"]

    # ---- 사내 LAN / NAS 주소로 열었던 흔적
    lan = collections.OrderedDict()
    for rep in reports:
        for kind in ("localStorage", "indexedDB", "cacheStorage", "httpCache", "serviceWorkers"):
            for o in (rep.get(kind) or {}):
                origin = split_storage_key(re.sub(r" \[.*\]$", "", o))[0]
                if is_lan_origin(origin):
                    ent = lan.setdefault(origin, {"originMasked": mask_origin(origin), "tag": erp_tag(origin),
                                                  "storages": []})
                    ent["storages"].append("%s/%s %s" % (rep["browser"], rep["profile"], kind))

    # ---- ERP 가 브라우저 밖에 둔 파일 (백업 도구가 '연결파일' 폴더로 복사한 것 + IndexedDB 파일 핸들)
    linked_copied = [x for x in as_list(manifest.get("linkedFiles")) if isinstance(x, dict)]
    linked_skipped = [x for x in as_list(manifest.get("linkedSkipped")) if isinstance(x, dict)]
    copied_src = {str(x.get("source") or "").lower() for x in linked_copied}
    handles = []
    for rep in reports:
        for h in rep.get("fileSystemHandles") or []:
            hh = dict(h)
            hh.update({"browser": rep["browser"], "profile": rep["profile"]})
            tp = str(h.get("targetPath") or "")
            hh["copiedInRawFolder"] = bool(tp) and tp.lower() in copied_src
            if tp and not hh["copiedInRawFolder"] and (run / "연결파일").is_dir():
                hh["note"] = "백업한 PC 에 이 파일이 없었거나 클라우드 전용이라 복사하지 않음 (manifest linkedSkipped 참고)"
            handles.append(hh)
    linked_info = {"copiedByBackupTool": linked_copied, "skippedByBackupTool": linked_skipped,
                   "fileSystemHandles": handles, "folder": "연결파일" if (run / "연결파일").is_dir() else None}

    # ---- 요약 파일
    n_err = sum(len(r["errors"]) for r in reports)
    n_incomplete = sum(len(r.get("incomplete") or []) for r in reports)
    summary = {
        "format": "SEUNGJEONG_ERP_RAW_PARSE_SUMMARY", "version": 1,
        "pcName": label, "computerName": computer, "rawFolder": run.name, "rawCreatedLocal": ctx["rawCreated"],
        "createdLocal": ctx["now"], "parser": EXTRACTOR,
        "manifest": manifest_digest(manifest),
        "integrity": sums,
        "supabase": {"dataFound": supa_total > 0, "cachedResponses": supa_total,
                     "serviceWorkerCache": {"responses": supa["sw"]["n"], "tablesSeen": sorted(supa["sw"]["tables"]),
                                            "where": supa["sw"]["where"]},
                     "httpDiskCache": {"responses": supa["http"]["n"], "tablesSeen": sorted(supa["http"]["tables"]),
                                       "where": supa["http"]["where"], "copiedProfiles": http_present},
                     "tablesSeen": sorted(supa["sw"]["tables"] | supa["http"]["tables"]),
                     "where": supa["sw"]["where"] + supa["http"]["where"],
                     "localStorageOriginsWithSupabaseKeys": supa_ls},
        "lanOrigins": list(lan.values()),
        "linkedFiles": linked_info,
        "profiles": reports,
        "firefox": firefox,
        "outputs": list(ctx["outputs"]),
        "warnings": warnings,
        "incompleteCount": n_incomplete,
        "errorCount": n_err,
    }
    sp = unique_path(out, "%s_분석요약.json" % safe_name(label))
    write_json(sp, summary)

    print("")
    print("-" * 78)
    if supa["sw"]["n"]:
        print(" 옛 인터넷 DB 자료 (앱 저장본): 발견! 응답 %d개 (표: %s)"
              % (supa["sw"]["n"], ", ".join(sorted(supa["sw"]["tables"])) or "-"))
        for w in supa["sw"]["where"]:
            print("   - " + disp(w))
    else:
        print(" 옛 인터넷 DB 자료 (앱 저장본): 발견되지 않음")
    if supa["http"]["n"]:
        print(" 옛 인터넷 DB 자료 (임시 인터넷 파일): 발견! 응답 %d개 (표: %s)"
              % (supa["http"]["n"], ", ".join(sorted(supa["http"]["tables"])) or "-"))
        for w in supa["http"]["where"]:
            print("   - " + disp(w))
    elif http_present:
        print(" 옛 인터넷 DB 자료 (임시 인터넷 파일): 복사본(%s)에서 ERP 주소의 옛 인터넷 DB 응답을 찾지 못함"
              % ", ".join(http_present))
    else:
        print(" 옛 인터넷 DB 자료 (임시 인터넷 파일): 확인 못 함 - 복사본에 없음 "
              "(백업 도구가 옛 인터넷 DB 흔적을 못 찾아 복사하지 않았거나, 옛 백업 도구로 만든 복사본)")
    if supa_ls:
        print(" 옛 인터넷 DB 관련 저장값이 있는 주소: %s" % "; ".join(disp(x) for x in supa_ls))
    if lan:
        print(" 회사 나스 주소로 연 흔적 %d곳: %s" % (len(lan), ", ".join(v["originMasked"] for v in lan.values())))
    if linked_copied or linked_skipped:
        print(" ERP 파일(브라우저 밖) : 복사 %d개 → '연결파일' 폴더%s" % (
            len(linked_copied), (", 못/안 받은 파일 %d개 (목록 파일 manifest.json 참고)" % len(linked_skipped))
            if linked_skipped else ""))
    for h in handles:
        print(" 연결된 파일(ERP 파일 핸들): %s  → %s" % (
            mask_path(h.get("targetPath")) or "(경로 없음)",
            "백업 폴더에 사본 있음" if h["copiedInRawFolder"] else "사본 없음"))
    print("")
    print(" 결과 파일 %d개 (%s):" % (len(ctx["outputs"]), out))
    for o in ctx["outputs"]:
        print("   - %s  (%s)%s" % (disp(o["file"]), fmt_bytes(o["bytes"]),
                                   "  ← 같은 이름이 있어 번호를 붙임" if o["renamed"] else ""))
    print(" 요약 파일: %s" % sp.name)
    for w in warnings:
        print(" [주의] " + disp(w))
    if n_incomplete:
        print(" [주의] 불완전한 데이터 %d곳 - 위의 '풀지 못한 레코드 / 없는 첨부 조각 파일' 줄을 확인하세요 (종료 코드 2)."
              % n_incomplete)
    if n_err:
        print(" [오류] %d건 - 위의 [오류] 줄과 요약 파일의 errors 를 확인하세요." % n_err)
    print(" 원본 폴더는 수정하지 않았습니다.")
    print("-" * 78)
    return 2 if (n_err or n_incomplete) else 0


# ================================================================ 자체 점검 (--self-test)
def self_test():
    """회귀 점검: LevelDB 'trivial move' (delete(L,n) + add(L+1,n) 이 한 edit 에) 에서 살아있는 파일을 버리지 않는지."""
    DF = collections.namedtuple("DF", "level file_no")
    NF = collections.namedtuple("NF", "level file_no")

    class E:
        def __init__(self, new=(), deleted=(), log=None, last=None):
            self.new_files = [NF(*x) for x in new]
            self.deleted_files = [DF(*x) for x in deleted]
            self.log_number, self.prev_log_number, self.last_sequence = log, None, last

    cases = [
        ("trivial move L0→L1", [E(new=[(0, 43)], log=44), E(new=[(1, 43)], deleted=[(0, 43)])], {43}),
        ("압축 후 삭제", [E(new=[(0, 5), (0, 6)]), E(new=[(1, 7)], deleted=[(0, 5), (0, 6)])], {7}),
        ("다른 레벨의 같은 번호 삭제는 무관", [E(new=[(2, 9)]), E(deleted=[(1, 9)])], {9}),
        ("여러 번 내려감", [E(new=[(0, 3)]), E(new=[(1, 3)], deleted=[(0, 3)]), E(new=[(2, 3)], deleted=[(1, 3)])], {3}),
    ]
    ok = True
    for name, edits, want in cases:
        got = apply_version_edits(edits)[0]
        good = got == want
        ok = ok and good
        print("  %-28s %s (결과 %s, 기대 %s)" % (name, "통과" if good else "실패", sorted(got), sorted(want)))
    tok = (b"\x08\x00\x1a\x30\x0a\x2c" + "C:\\Users\\x\\erp_db.json".encode("utf-16-le") + b"\x12\x00")
    paths = fsa_token_paths(tok)
    good = paths[:1] == ["C:\\Users\\x\\erp_db.json"]
    ok = ok and good
    print("  %-28s %s" % ("파일 핸들 경로(UTF-16LE)", "통과" if good else "실패 %r" % paths))
    for raw, want in (("1/0/_dk_file:// file:// https://a.supabase.co/rest/v1/t?x=1",
                       ("file://", "file://", "https://a.supabase.co/rest/v1/t?x=1")),
                      ("1/0/_dk_s_https://jachungu29.github.io https://jachungu29.github.io https://x.test/a b",
                       ("https://jachungu29.github.io", "https://jachungu29.github.io", "https://x.test/a b")),
                      ("https://old.test/x", (None, None, "https://old.test/x"))):
        got = split_http_cache_key(raw)
        good = got == want
        ok = ok and good
        print("  %-28s %s" % ("HTTP 캐시 키 해석", "통과" if good else "실패 %r" % (got,)))
    for o, want in (("http://192.168.250.250:5000", "lan-192.168.250.250-5000"), ("https://nas.local", "lan-nas.local-443-https"),
                    ("https://example.com", None), ("http://localhost:8791", "localhost-8791")):
        good = erp_tag(o) == want
        ok = ok and good
        print("  %-28s %s" % ("ERP 주소 판별 " + o.split("//")[1][:12], "통과" if good else "실패 %r" % erp_tag(o)))
    print(" 자체 점검: %s" % ("모두 통과" if ok else "실패 있음"))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
