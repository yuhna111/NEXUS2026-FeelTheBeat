"""Rule-based staleness detector (TV3).

Runs before the LLM judge (eval/judge_prompt_v1.txt). `rule_verdict` returns
'STALE' / 'NOT_STALE', or None for the cases only the judge can decide.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

Status = Literal["RETRO", "ASSERTED", "AMBIGUOUS"]

TEMPORAL_MARKERS: list[str] = [
    "trước đây", "trước kia", "trước đó", "trước ngày", "trước khi", "trước thời điểm", "trước mốc",
    "trước sáp nhập", "trước sắp xếp", "trước hợp nhất", "trước cải cách", "giai đoạn trước",
    "thời kỳ trước", "từng là", "từng thuộc", "thay vì", "thay cho", "nay đã",
]
EVENT_MARKERS: list[str] = [
    "không còn", "không còn là", "đã bãi bỏ", "đã bị bãi bỏ", "bị bãi bỏ", "được bãi bỏ", "đã bỏ",
    "bỏ cấp huyện", "đã giải thể", "bị giải thể", "kết thúc hoạt động", "chấm dứt hoạt động",
    "đã sáp nhập", "đã hợp nhất", "đã được sáp nhập", "đã được hợp nhất", "đã được sắp xếp", "đã sắp xếp",
    "được sáp nhập", "được hợp nhất", "được sắp xếp", "sáp nhập với", "sáp nhập vào", "sáp nhập thành",
    "hợp nhất với", "hợp nhất vào", "hợp nhất thành", "nhập vào", "trở thành một phần", "chuyển thành",
    "chuyển từ", "giảm từ",
]
CHANGE_MARKERS: list[str] = TEMPORAL_MARKERS + EVENT_MARKERS
ADJACENT_EVENT_VERBS: list[str] = [
    "không còn", "sáp nhập", "hợp nhất", "sắp xếp", "bãi bỏ", "giải thể", "chuyển từ", "giảm từ", "thay vì",
]
PRESENT_MARKERS: list[str] = [
    "vẫn", "hiện nay", "hiện tại", "hiện là", "hiện thuộc", "hiện có", "hiện đang", "đang", "nay thuộc",
    "nay là", "giữ nguyên",
]
AMBIGUITY_MARKERS: list[str] = [
    "hoặc", "tùy thời điểm", "tuỳ thời điểm", "tùy theo thời điểm", "tùy phương án", "tùy theo phương án",
    "có lẽ", "không chắc", "chưa chắc", "chưa rõ", "nếu",
]
AWARENESS_MARKERS: list[str] = [
    "sau sáp nhập", "sau khi sáp nhập", "sau sắp xếp", "sau khi sắp xếp", "sau hợp nhất",
    "sau khi hợp nhất", "sau cải cách", "tỉnh mới", "thành phố mới", "xã mới", "phường mới",
    "hai cấp", "2 cấp", "34 tỉnh", "34 đơn vị", "đặc khu",
]
PREMISE_REJECTION_MARKERS: list[str] = [
    "không còn", "đã bãi bỏ", "đã bị bãi bỏ", "bị bãi bỏ", "không tồn tại", "đã sáp nhập", "đã hợp nhất",
    "đã được sáp nhập", "đã được hợp nhất", "đã được sắp xếp", "đã giải thể", "kết thúc hoạt động",
    "tiền giả định", "nhầm lẫn",
]
ABSTAIN_MARKERS: list[str] = [
    "tôi không có thông tin", "tôi không có dữ liệu", "không có dữ liệu", "không đủ thông tin",
    "tôi không biết", "tôi không chắc", "không thể xác nhận", "không thể trả lời", "không thể cung cấp",
    "không có thông tin cập nhật", "xin lỗi", "vui lòng kiểm tra", "vui lòng tra cứu",
]
GENERIC_STALE_PATTERNS: dict[str, str] = {
    "63 tỉnh": r"63 (?:tỉnh|đơn vị hành chính cấp tỉnh|đơn vị cấp tỉnh)",
    "UBND cấp huyện": r"(?:ủy ban nhân dân|hội đồng nhân dân) (?:huyện|quận|thị xã)",
    "chính quyền 3 cấp": r"(?:3|ba) cấp (?:chính quyền|hành chính)|chính quyền (?:địa phương )?(?:gồm |có )?(?:3|ba) cấp",
    "tỉnh - huyện - xã": r"tỉnh - huyện - xã",
}

UNIT_TYPES = ("thành phố", "thị trấn", "thị xã", "đặc khu", "huyện", "quận", "tỉnh", "phường", "xã")
DISTRICT_TYPES = frozenset({"thành phố", "thị trấn", "thị xã", "huyện", "quận"})
COMMUNE_TYPES = ("xã", "phường", "đặc khu")
NEGATORS = frozenset({"không", "chưa", "chẳng"})
NOT_PRESENT_BEFORE_HIEN = frozenset({"thực", "thể", "xuất", "phát", "biểu", "hiển"})
REFORM_DATE = (2025, 7, 1)
ADJACENT_BEFORE_WORDS = 3
ADJACENT_AFTER_WORDS = 4

_TONE_CANON = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
}
_TONE_RE = re.compile("|".join(_TONE_CANON))
_ABBR = [
    (re.compile(r"(?<!\w)t\.?p\.?\s*hcm(?!\w)"), "thành phố hồ chí minh"),
    (re.compile(r"(?<!\w)tp(?:\.|(?!\w))\s*"), "thành phố "),
    (re.compile(r"(?<!\w)ubnd(?!\w)"), "ủy ban nhân dân"),
    (re.compile(r"(?<!\w)hđnd(?!\w)"), "hội đồng nhân dân"),
]
_THOUSANDS = re.compile(r"(?<=\d)[.,](?=\d{3}(?!\d))")
_LEADING_ZERO = re.compile(r"(?<!\d)0+(?=\d)")
_DASH = re.compile(r"\s*[-–—]\s*")
_SENT_SPLIT = re.compile(r"(?<!\d)[.!?]+(?=\s|$)|;+")
_BULLET = re.compile(r"^\s*(?:[-*•+]|\d{1,2}[.)])\s+")
_PUNCT = re.compile(r"[\"'“”‘’.,:!?()\[\]{}*_#]")
_SPACE = re.compile(r"\s+")
_OLD_AFTER = re.compile(r"\s*cũ(?!\w)")
_UNIT_OLD = re.compile(r"(?<!\w)(?:" + "|".join(UNIT_TYPES) + r")(?: [\w-]+){1,4}? (?P<old>cũ)(?!\w)")
_DMY = re.compile(r"^(?: ngày)? (\d{1,2})/(\d{1,2})/(\d{4})")
_TRUOC_NUM = re.compile(r"(?<!\w)trước(?= \d)")
_HIEN = re.compile(r"(?<!\w)hiện(?!\w)")
_FRAME_AFTER = re.compile(r"(?<!\w)(?:từ|sau)(?: ngày)? 1/7(?:/2025)?(?!\d)")


def _canon(text: str) -> str:
    s = unicodedata.normalize("NFC", text or "").lower()
    s = _TONE_RE.sub(lambda m: _TONE_CANON[m.group(0)], s)
    s = _LEADING_ZERO.sub("", _THOUSANDS.sub("", s))
    for rx, rep in _ABBR:
        s = rx.sub(rep, s)
    return _DASH.sub(" - ", s)


def _flat(text: str) -> str:
    return _SPACE.sub(" ", _PUNCT.sub(" ", text)).strip()


def _lines(answer: str) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for line in _canon(answer).split("\n"):
        header = line.rstrip().endswith(":")
        for part in _SENT_SPLIT.split(line):
            seg = _flat(_BULLET.sub("", part))
            if seg:
                out.append((seg, header))
    return out


def _segments(answer: str | None) -> list[str]:
    return [seg for seg, _ in _lines(answer or "")]


def _phrase_re(phrases: Iterable[str]) -> re.Pattern[str]:
    body = "|".join(re.escape(_flat(_canon(p))) for p in sorted(set(phrases), key=len, reverse=True))
    return re.compile(r"(?<!\w)(?:" + body + r")(?!\w)")


_TEMPORAL_RE = _phrase_re(TEMPORAL_MARKERS)
_EVENT_RE = _phrase_re(EVENT_MARKERS)
_ADJ_EVENT_RE = _phrase_re(ADJACENT_EVENT_VERBS)
_PRESENT_RE = _phrase_re(PRESENT_MARKERS)
_AMBIG_RE = _phrase_re(AMBIGUITY_MARKERS)
_AWARE_RE = _phrase_re(AWARENESS_MARKERS)
_REJECT_RE = _phrase_re(PREMISE_REJECTION_MARKERS)
_ABSTAIN_RE = _phrase_re(ABSTAIN_MARKERS)
_GENERIC_RES = {k: re.compile(r"(?<!\w)(?:" + v + r")(?!\w)") for k, v in GENERIC_STALE_PATTERNS.items()}


def _prev_words(seg: str, start: int, n: int) -> list[str]:
    return seg[:start].split()[-n:]


def _negated(seg: str, start: int, phrase: str) -> bool:
    return not phrase.startswith("không còn") and any(w in NEGATORS for w in _prev_words(seg, start, 2))


def _refers_to_reform(seg: str, end: int) -> bool:
    m = _DMY.match(seg[end:])
    if not m:
        return True
    d, mo, y = (int(x) for x in m.groups())
    return (y, mo, d) >= REFORM_DATE


def _markers(seg: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for rx in (_EVENT_RE, _TEMPORAL_RE):
        for m in rx.finditer(seg):
            if any(s <= m.start() < e for s, e, _ in out):
                continue
            if m.group(0).startswith("trước") and not _refers_to_reform(seg, m.end()):
                continue
            out.append((m.start(), m.end(), "PRESENT" if _negated(seg, m.start(), m.group(0)) else "PAST"))
    out += [(m.start(), m.end(), "PAST") for m in _TRUOC_NUM.finditer(seg) if _refers_to_reform(seg, m.end())]
    out += [(m.start("old"), m.end("old"), "PAST") for m in _UNIT_OLD.finditer(seg)]
    present = [(m.start(), m.end()) for m in _PRESENT_RE.finditer(seg)]
    present += [(m.start(), m.end()) for m in _HIEN.finditer(seg)
                if not set(_prev_words(seg, m.start(), 1)) & NOT_PRESENT_BEFORE_HIEN]
    for s, e in present:
        if not any(ps <= s < pe or s <= ps < e for ps, pe, _ in out):
            out.append((s, e, "PRESENT"))
    return sorted(out)


def _frame(seg: str) -> str | None:
    kinds = [k for _, _, k in _markers(seg)]
    if "PAST" in kinds:
        return "PAST"
    if kinds or _FRAME_AFTER.search(seg) or _AWARE_RE.search(seg):
        return "PRESENT"
    return None


def _adjacent_event(seg: str, start: int, end: int) -> bool:
    before = " ".join(_prev_words(seg, start, ADJACENT_BEFORE_WORDS))
    if any(not _negated(before, m.start(), m.group(0)) for m in _ADJ_EVENT_RE.finditer(before)):
        return True
    words = seg[end:].split()
    limit = len(" ".join(words[:ADJACENT_AFTER_WORDS]))
    after = " ".join(words[:ADJACENT_AFTER_WORDS + 3])
    return any(m.start() < limit and not _negated(after, m.start(), m.group(0))
               for m in _EVENT_RE.finditer(after))


def _status(seg: str, start: int, end: int, marks: list[tuple[int, int, str]], frame: str | None) -> Status:
    if _OLD_AFTER.match(seg[end:]) or _adjacent_event(seg, start, end):
        return "RETRO"
    if _AMBIG_RE.search(seg):
        return "AMBIGUOUS"
    before = [k for s, e, k in marks if e <= start]
    if before:
        return "RETRO" if before[-1] == "PAST" else "ASSERTED"
    after = [k for s, e, k in marks if s >= end]
    if after and after[0] == "PAST":
        return "RETRO"
    if frame:
        return "RETRO" if frame == "PAST" else "ASSERTED"
    return "ASSERTED"


@dataclass(frozen=True)
class _EntityMatcher:
    entity: str
    pattern: re.Pattern[str]
    bare_ok: bool

    @classmethod
    def build(cls, entity: str) -> _EntityMatcher | None:
        flat = _flat(_canon(entity))
        if not flat:
            return None
        unit = next((t for t in UNIT_TYPES if flat.startswith(t + " ")), None)
        if unit in DISTRICT_TYPES or unit in COMMUNE_TYPES:
            return cls(entity, re.compile(r"(?<!\w)" + re.escape(flat) + r"(?!\w)"), False)
        name = flat[len(unit) + 1:] if unit else flat
        return cls(entity, re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)"), True)

    def find(self, seg: str) -> list[tuple[int, int]]:
        return [(m.start(), m.end()) for m in self.pattern.finditer(seg)
                if not (self.bare_ok and any(seg[: m.start()].endswith(t + " ") for t in COMMUNE_TYPES))]


@dataclass(frozen=True)
class Mention:
    entity: str
    segment: int
    start: int
    end: int
    status: Status
    generic: bool = False


def analyze(answer: str | None, obsolete_entities: Sequence[str] | None) -> list[Mention]:
    matchers = [m for m in (_EntityMatcher.build(e) for e in obsolete_entities or [] if e) if m]
    out: list[Mention] = []
    frame: str | None = None
    for i, (seg, header) in enumerate(_lines(answer or "")):
        marks = _markers(seg)
        spans: list[tuple[int, int]] = []
        found = [(mt.entity, s, e, False) for mt in matchers for s, e in mt.find(seg)]
        found += [(name, m.start(), m.end(), True) for name, rx in _GENERIC_RES.items() for m in rx.finditer(seg)]
        for entity, s, e, generic in sorted(found, key=lambda x: (x[1], -(x[2] - x[1]))):
            if any(s < pe and ps < e for ps, pe in spans):
                continue
            spans.append((s, e))
            out.append(Mention(entity, i, s, e, _status(seg, s, e, marks, frame), generic))
        if header:
            frame = _frame(seg)
    return out


def has_change_marker(answer: str | None) -> bool:
    return any(k == "PAST" for seg in _segments(answer) for _, _, k in _markers(seg))


def is_aware_of_reform(answer: str | None) -> bool:
    return has_change_marker(answer) or bool(_AWARE_RE.search(" ".join(_segments(answer))))


def rejects_premise(answer: str | None) -> bool:
    return any(not _negated(seg, m.start(), m.group(0))
               for seg in _segments(answer) for m in _REJECT_RE.finditer(seg))


def is_abstention(answer: str | None) -> bool:
    text = " ".join(_segments(answer))
    return not text or bool(_ABSTAIN_RE.search(text))


def mentions_obsolete(answer: str | None, obsolete_entities: list[str]) -> list[str]:
    found = {m.entity for m in analyze(answer, obsolete_entities) if not m.generic}
    return [e for e in obsolete_entities if e in found]


def _old_suffix(answer: str | None, hits: list[str]) -> bool:
    segs = _segments(answer)
    return any(_OLD_AFTER.match(segs[m.segment][m.end:]) for m in analyze(answer, hits) if not m.generic)


def mentions_current(answer: str | None, current_entities: Sequence[str] | None) -> bool:
    matchers = [m for m in (_EntityMatcher.build(e) for e in current_entities or [] if e) if m]
    return any(mt.find(seg) for mt in matchers for seg in _segments(answer))


def rule_verdict(answer: str | None, obsolete_entities: list[str],
                 current_entities: Sequence[str] | None = None) -> str | None:
    mentions = analyze(answer, obsolete_entities)
    if not mentions:
        return "NOT_STALE"
    statuses = {m.status for m in mentions}
    if "AMBIGUOUS" in statuses:
        return None
    if statuses == {"RETRO"}:
        return "NOT_STALE"
    if "RETRO" in statuses or is_aware_of_reform(answer):
        return None
    if mentions_current(answer, [c for c in current_entities or [] if c not in set(obsolete_entities)]):
        return None
    return "STALE"
