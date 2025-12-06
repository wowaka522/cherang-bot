# utils/search_improved.py
import difflib
from utils.market_data import KR_ITEMS  # {"아이템ID(str)": "아이템 이름(str)", ...}


def _normalize(s: str) -> str:
    """검색용 정규화: 소문자 + 공백 제거"""
    return "".join(ch for ch in s.lower() if not ch.isspace())


def search_item(query: str, multiple=False):
    """
    아이템 이름 검색
    return: (item_id:int | None, real_name:str | None, similar:list[str])
    검색 우선순위:
    1️⃣ 띄어쓰기 유지한 정확 이름 → (최우선!!)
    2️⃣ 전체 정규화 완전 일치
    3️⃣ 단어 모두 포함 (복합어 대응)
    4️⃣ 부분 포함 (길이 & 위치 기반)
    5️⃣ 유사도 기반
    """

    if not query:
        return None, None, []

    original = query.strip()
    q_norm = _normalize(original)

    items = [(item_id, name, _normalize(name)) for item_id, name in KR_ITEMS.items()]

    # ------------------------------------------------------
    # 1️⃣ 띄어쓰기 포함 “정확 이름” 일치 (로네크 아교 문제 해결!)
    # ------------------------------------------------------
    exact_original = [(iid, name) for iid, name, _ in items if name == original]
    if exact_original:
        iid, name = exact_original[0]
        return int(iid), name, []

    # ------------------------------------------------------
    # 2️⃣ 완전 일치 (정규화 후)
    # ------------------------------------------------------
    exact = [(iid, name) for iid, name, n in items if n == q_norm]
    if exact:
        chosen_id, chosen_name = min(exact, key=lambda x: len(_normalize(x[1])))
        similar = [name for iid, name, n in items if q_norm in n and name != chosen_name][:10]
        return int(chosen_id), chosen_name, similar

    # ------------------------------------------------------
    # 3️⃣ 단어 모두 포함 검색 (복합어 처리: “로네크” + “아교”)
    # ------------------------------------------------------
    if " " in original:
        parts = original.split()
        match_all = []
        for iid, name, _ in items:
            if all(p in name for p in parts):
                match_all.append((iid, name))

        if match_all:
            chosen_id, chosen_name = match_all[0]
            similar = [n for _, n in match_all[1:10]]
            return int(chosen_id), chosen_name, similar

    # ------------------------------------------------------
    # 4️⃣ 부분 포함 검색 (정규화 기준)
    # ------------------------------------------------------
    contains = [(iid, name, n) for iid, name, n in items if q_norm in n]
    if contains:
        contains.sort(key=lambda t: (t[2].find(q_norm), len(t[2])))
        chosen_id, chosen_name, _ = contains[0]
        similar = [name for iid, name, n in contains[1:11]]
        return int(chosen_id), chosen_name, similar

    # ------------------------------------------------------
    # 5️⃣ 유사도 기반 (difflib)
    # ------------------------------------------------------
    norm_to_item = {}
    for iid, name, n in items:
        norm_to_item.setdefault(n, (iid, name))

    norm_names = list(norm_to_item.keys())
    matches = difflib.get_close_matches(q_norm, norm_names, n=6, cutoff=0.58)

    if matches:
        first = matches[0]
        chosen_id, chosen_name = norm_to_item[first]
        similar = [norm_to_item[n][1] for n in matches[1:]]
        return int(chosen_id), chosen_name, similar

    # ------------------------------------------------------
    return None, None, []
