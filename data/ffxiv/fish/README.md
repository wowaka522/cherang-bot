# FFXIV 데이터 파이프라인 메모 (체랑봇)

## 0) 큰 그림
- **RAW**: 원천(csv, data.js) / 패치마다 갱신
- **COMPILED**: 봇이 읽는 최종 JSON (런타임에서 조인/파싱 안 함)

---

## 1) 아이템 인덱스 (시세/아이템 검색)

### 입력 RAW
- `Item.csv` (EN)
  - 사용: 아이템 ID ↔ 영문명(보조 매칭용)
- `Item_ko.csv` (KO)
  - 사용: 아이템 ID ↔ 한글명/아이콘/카테고리/설명(주 인덱스)

### 빌더
- `convert_items_New.py` (외부 폴더/별도 관리)
  - 입력: Item.csv(EN), Item_ko.csv(KO)
  - 출력: `data/ffxiv/market/items.json`

### 출력 COMPILED
- `data/ffxiv/market/items.json`
  - 구조: { "<item_id>": { "name": "...", "icon": "...", "desc": "...", "category": "..." } }

---

## 2) 낚시 DB (터주/낚시터/지역계층/직감/공략 경로)

### 입력 RAW
- `data.js`
  - 사용:
    - bigFish(true) 터주 판별
    - 시간창(startHour/endHour)
    - 입질(tug), 훅셋(hookset)
    - 미끼 경로(bestCatchPath)
    - (가능하면) 날씨 조건(weatherSet/previousWeatherSet)
    - 직감 조건(predators, intuitionLength 등)

- `FishingSpot.csv`
  - 사용:
    - 낚시터 ID(#)
    - 낚시터 이름(PlaceName)
    - 스팟 소속 맵 코드(TerritoryType)
    - 스팟 출현 물고기 목록(Item[0..9])  ※ 이름 기반
    - 직감 문구(BigFish{OnReach}, BigFish{OnEnd})

- `TerritoryType.csv`
  - 사용:
    - 맵 코드(Name) → 지역 계층(대륙/지역/세부지역) 매핑

- `PlaceName.csv`
  - 사용:
    - TerritoryType에서 숫자 ID로 들어온 PlaceName을 실제 이름으로 변환할 때

- `FishParameter.csv`
  - 사용:
    - 물고기 설명(Text) 매핑용 (Item name → description)

- `Item.csv` / `Item_ko.csv`
  - 사용:
    - 물고기 ID → 한글명/아이콘 매핑
    - (bestCatchPath의 미끼 ID → 미끼 이름 변환)

### 빌더(레포 내)
- `data/ffxiv/fish/tools/build_fish_db.py`
  - 입력: 위 RAW 전부
  - 출력: `data/ffxiv/fish/compiled/final_fishing_db.json`

### 출력 COMPILED
- `data/ffxiv/fish/compiled/final_fishing_db.json`
  - 포함:
    - FISH: 터주/조건부 물고기 정보(시간창/입질/미끼/조건/설명/아이콘 등)
    - SPOTS: 낚시터(대륙/지역/세부지역/낚시터명/직감문구/fish_list/teoju_list)
    - (옵션) SPOTS_TREE: 탐색용 트리

---

## 3) 업데이트 루틴 (패치 후)
1) CSV/data.js 최신으로 교체 (RAW 갱신)
2) items.json 재생성 (convert_items_New.py)
3) final_fishing_db.json 재생성 (build_fish_db.py)
4) 봇 테스트 후 커밋/배포

---