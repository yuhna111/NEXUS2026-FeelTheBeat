"""Điền cột old_province của data/processed/commune_lineage.csv (TV1, tuần 3).

Nghị quyết cấp xã của tỉnh hợp nhất không ghi tỉnh cũ, nên đối chiếu tên xã cũ với
danh mục ĐVHC ngày 01/03/2025 (Tổng cục Thống kê) qua bộ dữ liệu dvhcvn
(https://github.com/daohoangson/dvhcvn, GPL-3.0; không chép dữ liệu vào repo).

Thứ tự: khớp đúng tên + loại (+ huyện nếu nghị quyết ghi) trong các tỉnh cũ của tỉnh mới
-> khớp bỏ dấu thanh -> suy từ các đơn vị cùng xã mới -> ghi tay (MANUAL) -> theo đa số.
Mọi dòng được điền ghi cách điền vào file audit.

Chạy:
  git clone --depth 1 https://github.com/daohoangson/dvhcvn /tmp/dvhcvn
  python scripts/fill_old_province.py data/processed/commune_lineage.csv \
      data/processed/entity_map_63_34_v1.csv /tmp/dvhcvn/data/dvhcvn.json \
      data/processed/commune_lineage_old_province_audit.csv
"""
import csv, json, re, sys, unicodedata, collections
lin_path, em_path, dv_path = sys.argv[1:4]
audit_path = sys.argv[4] if len(sys.argv) > 4 else 'old_province_audit.csv'
N = lambda s: unicodedata.normalize('NFC', s).strip()
def norm_prov(n):
    n = N(n); return re.sub(r'^(Thành phố|Tỉnh)\s+', '', n)
def split_unit(s):
    s = N(s); m = re.match(r'^(xã|phường|thị trấn|đặc khu)\s+(.*)$', s, re.I)
    return (m.group(1).lower(), m.group(2).strip()) if m else (None, s)
def low(s): return N(s).lower()
TONES = {'\u0300','\u0301','\u0303','\u0309','\u0323'}
def toneless(s): return unicodedata.normalize('NFC', ''.join(ch for ch in unicodedata.normalize('NFD', low(s)) if ch not in TONES))
em = list(csv.DictReader(open(em_path, encoding='utf-8')))
canon = {toneless(r['old_province']): r['old_province'] for r in em}
dv = json.load(open(dv_path, encoding='utf-8'))['data']
idx = collections.defaultdict(list); tidx = collections.defaultdict(list); didx = collections.defaultdict(list)
for p in dv:
    pn = canon.get(toneless(norm_prov(p['name'])), norm_prov(p['name']))
    for d in p['level2s']:
        dn = N(d['name'])
        for c in d['level3s']:
            t, nm = split_unit(c['name'])
            idx[(pn, low(nm))].append((t, dn)); tidx[(pn, toneless(nm))].append((t, dn))
        dnn = re.sub(r'^(huyện|quận|thị xã|thành phố)\s+', '', low(dn)); didx[(pn, dnn)].append(dn)
em = list(csv.DictReader(open(em_path, encoding='utf-8')))
olds = collections.defaultdict(list)
for r in em: olds[r['new_province']].append(r['old_province'])
rows = list(csv.DictReader(open(lin_path, encoding='utf-8')))
stat = collections.Counter(); amb = []; method = {}
def find(r, table, key):
    t, nm = split_unit(r['old_commune']); hits = []
    for o in olds[r['new_province']]:
        for (ct, dn) in table.get((o, key(nm)), []):
            if t and ct and t != ct: continue
            if r['old_district'] and low(r['old_district']).startswith(('huyện','quận','thị xã','thành phố')) and toneless(low(r['old_district'])) != toneless(low(dn)): continue
            hits.append(o)
    return sorted(set(hits))
pending = []
for i, r in enumerate(rows):
    if r['old_province']: stat['had'] += 1; method[i] = 'có sẵn'; continue
    m = re.match(r'^(huyện|quận|thị xã|thành phố)\s+(.*)$', N(r['old_commune']), re.I)
    if m:
        hs = sorted({o for o in olds[r['new_province']] if didx.get((o, low(m.group(2))))})
    else:
        hs = find(r, idx, low)
        if not hs: hs = find(r, tidx, toneless); tag = 'dvhcvn, bỏ dấu thanh'
        else: tag = 'dvhcvn'
    if m: tag = 'dvhcvn, cấp huyện'
    if len(hs) == 1: r['old_province'] = hs[0]; stat['filled'] += 1; method[i] = tag
    else: pending.append((i, hs))
# ambiguous: use the other old units merged into the same new commune
by_new = collections.defaultdict(set)
for i, r in enumerate(rows):
    if r['old_province']: by_new[r['new_commune_code']].add(r['old_province'])
for i, hs in pending:
    r = rows[i]; sib = by_new[r['new_commune_code']]
    pick = sorted(sib & set(hs)) if hs else sorted(sib)
    if len(pick) == 1:
        r['old_province'] = pick[0]; stat['filled_by_sibling'] += 1; method[i] = 'suy từ đơn vị cùng xã mới' + ('' if hs else ' (không có trong dvhcvn)')
    else:
        stat['unresolved'] += 1; method[i] = 'chưa xác định'; amb.append((r['new_commune_code'], r['old_commune'], r['old_district'], hs, sorted(sib)))
# Ghi tay (TV1, 25/11/2026): tên viết khác nhau giữa nghị quyết và danh mục 01/03/2025
MANUAL = {
    ('1659-081', 'xã Bhalêê'): ('Quảng Nam', 'tay: danh mục ghi "Xã Bha Lê" (huyện Tây Giang)'),
    ('1659-081', 'xã Avương'): ('Quảng Nam', 'tay: danh mục ghi "Xã A Vương" (huyện Tây Giang)'),
    ('1660-011', 'xã Ea Drơng'): ('Đắk Lắk', 'tay: danh mục ghi "Xã Ea D\'Rơng" (huyện Cư M\'gar)'),
    ('1660-011', 'xã Cuôr Đăng'): ('Đắk Lắk', 'tay: danh mục ghi "Xã Cuor Đăng" (huyện Cư M\'gar)'),
    ('1662-U04', 'xã Đak Lua'): ('Đồng Nai', 'tay: danh mục ghi "Xã Dak Lua" (huyện Tân Phú)'),
    ('1662-U07', 'xã Đăk Ơ'): ('Bình Phước', 'tay: danh mục ghi "Xã Đak Ơ" (huyện Bù Gia Mập)'),
    ('1673-U06', 'xã Tà Xi Láng'): ('Yên Bái', 'tay: danh mục ghi "Xã Tà Si Láng" (huyện Trạm Tấu)'),
    ('1668-U03', 'xã Thạnh Phú'): ('Cần Thơ', 'tay: xã Thạnh Phú (Mỹ Xuyên, Sóc Trăng) đã nhập vào xã Nhu Gia, NQ 1668 khoản 67; còn lại xã Thạnh Phú (Cờ Đỏ, Cần Thơ)'),
}
for i, r in enumerate(rows):
    k = (r['new_commune_code'], r['old_commune'])
    if k in MANUAL and not r['old_province']:
        r['old_province'], method[i] = MANUAL[k]; stat['manual'] += 1; stat['unresolved'] -= 1
# Một xã mới chỉ gồm đơn vị của một tỉnh cũ: đơn vị thiểu số lệch tỉnh là do trùng tên -> theo đa số
grp = collections.defaultdict(list)
for i, r in enumerate(rows): grp[r['new_commune_code']].append(i)
for code, ids in grp.items():
    c = collections.Counter(rows[i]['old_province'] for i in ids if rows[i]['old_province'])
    if len(c) > 1:
        top, n = c.most_common(1)[0]
        for i in ids:
            if rows[i]['old_province'] != top and method[i] != 'có sẵn':
                method[i] = f'theo đa số cùng xã mới (khớp tên ban đầu: {rows[i]["old_province"]}), cần kiểm tay'
                rows[i]['old_province'] = top; stat['majority_fix'] += 1
print(dict(stat))
w = csv.DictWriter(open(lin_path, 'w', encoding='utf-8', newline=''), fieldnames=list(rows[0].keys()))
w.writeheader(); w.writerows(rows)
a = csv.writer(open(audit_path, 'w', encoding='utf-8', newline=''))
a.writerow(['new_commune_code','new_commune','old_commune','old_province','method'])
for i, r in enumerate(rows):
    if method[i] != 'có sẵn': a.writerow([r['new_commune_code'], r['new_commune'], r['old_commune'], r['old_province'], method[i]])
