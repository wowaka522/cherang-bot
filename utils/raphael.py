# utils/raphael.py
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# ===== 경로 설정 =====
# 프로젝트 루트에서 python bot.py 실행한다고 가정
RAPHAEL_DIR = Path("raphael")
RAPHAEL_EXE = RAPHAEL_DIR / "raphael-cli.exe"
RAPHAEL_ROOT = RAPHAEL_DIR / "raphael-rs"

# locales.rs 위치가 둘 중 하나일 수 있으니 둘 다 지원
LOCALES_CANDIDATES = [
    RAPHAEL_ROOT / "raphael-data" / "locales.rs",
    RAPHAEL_ROOT / "locales.rs",
]

ITEM_NAMES_RS = RAPHAEL_ROOT / "raphael-data" / "data" / "item_names_kr.rs"
MEALS_RS = RAPHAEL_ROOT / "raphael-data" / "data" / "meals.rs"
POTIONS_RS = RAPHAEL_ROOT / "raphael-data" / "data" / "potions.rs"

ACTION_KR: Dict[str, str] = {}
MEAL_ITEMS: Dict[int, str] = {}
POTION_ITEMS: Dict[int, str] = {}
_initialized: bool = False


# ===== 공통: 라파엘 CLI 호출 =====
def run_raphael(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [RAPHAEL_EXE] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",  # UTF-8 강제
        errors="replace",  # 깨진 문자는 자동 대체
    )



# ===== locales.rs → 스킬 한글 이름 =====
def _find_locales_path() -> Optional[Path]:
    for p in LOCALES_CANDIDATES:
        if p.exists():
            return p
    return None


def load_action_locales() -> None:
    """라파엘 RS 쪽 locales.rs에서 Action 코드 → 한글 이름 맵 로딩"""
    global ACTION_KR
    locales_rs = _find_locales_path()

    if not locales_rs:
        print("⚠ locales.rs 없음 → 스킬명은 영어 코드로 출력")
        ACTION_KR = {}
        return

    text = locales_rs.read_text("utf-8", "ignore")
    mapping: Dict[str, str] = {}
    # Action::BasicSynthesis => "기본 작업"
    for code, name in re.findall(r'Action::([A-Za-z0-9_]+)\s*=>\s*"([^"]+)"', text):
        mapping[code] = name

    ACTION_KR = mapping
    print(f"✨ 한글 스킬명 {len(ACTION_KR)}개 로드 완료")


# ===== item_names_kr + meals/potions =====
def load_item_names() -> Dict[int, str]:
    """item_names_kr.rs에서 아이템 ID → 이름 맵 로드"""
    if not ITEM_NAMES_RS.exists():
        print("⚠ item_names_kr.rs 없음")
        return {}

    text = ITEM_NAMES_RS.read_text("utf-8", "ignore")
    mapping: Dict[int, str] = {}
    # 12345 => "메갈로크랩 커리"
    for sid, name in re.findall(r'(\d+)\s*=>\s*"([^"]+)"', text):
        try:
            mapping[int(sid)] = name
        except ValueError:
            continue
    print(f"✨ 아이템 이름 {len(mapping)}개 로드")
    return mapping


def _load_ids_from(path: Path, label: str) -> set[int]:
    """meals.rs / potions.rs 안의 item_id만 뽑아오는 헬퍼"""
    if not path.exists():
        print(f"⚠ {label} 파일 없음: {path}")
        return set()

    text = path.read_text("utf-8", "ignore")
    ids: set[int] = set()
    for sid in re.findall(r'item_id:\s*(\d+)', text):
        try:
            ids.add(int(sid))
        except ValueError:
            continue
    print(f"✨ {label} item_id {len(ids)}개 로드")
    return ids


def load_meals_and_potions() -> None:
    """음식 / 물약 아이템 목록 로드"""
    global MEAL_ITEMS, POTION_ITEMS

    names = load_item_names()
    meal_ids = _load_ids_from(MEALS_RS, "meals")
    potion_ids = _load_ids_from(POTIONS_RS, "potions")

    MEAL_ITEMS = {iid: names.get(iid, f"#{iid}") for iid in meal_ids}
    POTION_ITEMS = {iid: names.get(iid, f"#{iid}") for iid in potion_ids}

    print(f"🍽 음식 {len(MEAL_ITEMS)}개, 🧪 약 {len(POTION_ITEMS)}개 매핑 완료")


# ===== 초기화 =====
def ensure_raphael_ready() -> None:
    """라파엘 관련 데이터 로딩 1회만 수행"""
    global _initialized
    if _initialized:
        return

    load_action_locales()
    load_meals_and_potions()
    _initialized = True


# ===== 레시피 / 음식 / 비약 검색 =====
def search_recipe(keyword: str) -> List[Dict]:
    """라파엘 search recipe 호출"""
    ensure_raphael_ready()

    proc = run_raphael([
        "search", "recipe",
        "--pattern", keyword,
        "--language", "kr",
    ])
    if proc.returncode != 0:
        print("search_recipe 오류:", proc.stderr)
        return []

    results: List[Dict] = []
    for line in proc.stdout.strip().splitlines():
        parts = line.strip().split(maxsplit=3)
        if len(parts) < 4:
            continue
        try:
            rid = int(parts[0])
        except ValueError:
            continue
        name = parts[3]
        results.append({"id": rid, "name": name})

    return results[:25]


def search_meal_items(keyword: str) -> List[Tuple[int, str]]:
    """음식 아이템 이름 부분검색"""
    ensure_raphael_ready()
    kw = keyword.strip().lower()
    if not kw:
        return []
    res = [(iid, name) for iid, name in MEAL_ITEMS.items() if kw in name.lower()]
    res.sort(key=lambda x: x[1])
    return res[:25]


def search_potion_items(keyword: str) -> List[Tuple[int, str]]:
    """비약 아이템 이름 부분검색"""
    ensure_raphael_ready()
    kw = keyword.strip().lower()
    if not kw:
        return []
    res = [(iid, name) for iid, name in POTION_ITEMS.items() if kw in name.lower()]
    res.sort(key=lambda x: x[1])
    return res[:25]


# ===== 재료 정보 =====
def get_ingredients(recipe_id: int) -> List[Dict]:
    """지정 레시피의 재료 목록 조회"""
    ensure_raphael_ready()

    proc = run_raphael([
        "ingredients",
        "--recipe-id", str(recipe_id),
        "--language", "kr",
    ])
    if proc.returncode != 0:
        print("ingredients 오류:", proc.stderr)
        return []

    res: List[Dict] = []
    for line in proc.stdout.strip().splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) < 3:
            continue
        try:
            amount = int(parts[0])
        except ValueError:
            continue
        name = parts[2]
        res.append({"amount": amount, "name": name})
    return res


def is_hq_candidate(name: str) -> bool:
    """HQ 입력 받을만한 재료인지 필터 (샤드/크리스탈/클러스터 제외)"""
    bad = ["샤드", "크리스탈", "클러스터"]
    return not any(b in name for b in bad)


# ===== solve & 매크로 변환 =====
def solve_macro(
    recipe_id: int,
    stats: Dict,
    food: Optional[str],
    potion: Optional[str],
    hq: Optional[List[int]],
) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    라파엘 solve 호출
    :return: (actions(list[str]) or None, error(str) or None)
    """
    ensure_raphael_ready()

    try:
        craft = int(stats["craft"])
        control = int(stats["control"])
        cp = int(stats["cp"])
        level = int(stats["job_level"])
    except Exception as e:
        return None, f"스탯 파싱 실패: {e}"

    args: List[str] = [
        "solve",
        "--recipe-id", str(recipe_id),
        "--stats", str(craft), str(control), str(cp),
        "--level", str(level),
        "--output-variables", "actions",
    ]

    if food:
        args.extend(["--food", food])
    if potion:
        args.extend(["--potion", potion])
    if hq and any(v > 0 for v in hq):
        args.append("--hq-ingredients")
        args.extend(str(v) for v in hq)

    proc = run_raphael(args)
    if proc.returncode != 0:
        return None, proc.stderr or "solve 실행 실패"

    out = proc.stdout.strip()
    if not out:
        return None, "solve 결과가 비어 있음"

    # 예: ["Action::BasicSynthesis", "Action::BasicTouch", ...]
    cleaned = out.strip().strip('"').strip().strip("[]")
    raw_actions = [x.strip() for x in cleaned.split(",") if x.strip()]
    if not raw_actions:
        return None, "actions 파싱 실패"

    actions_kr: List[str] = []
    for code in raw_actions:
        code = code.replace("Action::", "").replace('"', "").strip()
        actions_kr.append(ACTION_KR.get(code, code))

    return actions_kr, None


def split_macros(actions: List[str]) -> List[str]:
    """
    액션 리스트를 /ac 매크로 여러 개로 분할
    (15줄씩 끊고 마지막에 echo 붙임)
    """
    chunks: List[str] = []
    if not actions:
        return chunks

    total = (len(actions) + 14) // 15

    for i in range(0, len(actions), 15):
        part = actions[i:i + 15]
        lines = [f'/ac "{a}" <wait.3>' for a in part]
        macro_index = (i // 15) + 1
        lines.append(f'/echo Macro finished ({macro_index}/{total}) <se.1>')
        chunks.append("\n".join(lines))

    return chunks

# ==============================
#  DB User Stats Helper
# ==============================
import json
from pathlib import Path

DB_FILE = Path("./data/stats_db.json")

def load_db() -> dict:
    if not DB_FILE.exists():
        save_db({})
    try:
        return json.loads(DB_FILE.read_text("utf-8"))
    except Exception:
        save_db({})
        return {}

def save_db(data: dict):
    DB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=4), "utf-8")

def get_user_stats(uid: str) -> dict:
    db = load_db()
    return db.get(uid, {"jobs": {}, "last_job": None})

def set_user_stats(uid: str, u: dict):
    db = load_db()
    db[uid] = u
    save_db(db)

# ==============================
#  Slash 명령어용 Wrapper 함수
# ==============================

def run_solve(recipe_id: int, stats: dict, food: Optional[str] = None, potion: Optional[str] = None, hq: Optional[List[int]] = None):
    """
    /제작 명령어가 호출하는 solve wrapper
    """
    actions, err = solve_macro(recipe_id, stats, food, potion, hq)
    if err:
        return None, err

    macros = split_macros(actions)
    return macros, None


def get_player_status(uid: str):
    """
    /상태 명령어가 호출하는 스탯 조회 wrapper
    """
    u = get_user_stats(uid)
    # 기본값까지 포함해서 깔끔하게 내보냄
    last = u.get("last_job") or "OM"  # 기본 직업: 만능공(OM)
    jobs = u.get("jobs", {})
    stats = jobs.get(last, {"craft": 0, "control": 0, "cp": 0, "job_level": 1})
    return last, stats