# 체랑봇 서버 운영 & 유지보수 전용 README

> ❗ 개인 서버(1개 길드 전용) 체랑봇 관리 문서  
> Ubuntu 22.04 Minimal 기준  
> Python3(venv 미확인), PM2 사용

---

## 📁 기본 정보 & 경로

| 항목 | 값 |
|------|------|
| Bot root | `/home/wltn5548/cherang-bot/` |
| Python | 3.10 (Ubuntu 기본) |
| 실행 프로세스 | `cherang` (PM2) |
| 오류 로그 | `~/.pm2/logs/cherang-error.log` |
| 출력 로그 | `~/.pm2/logs/cherang-out.log` |

---

## ⚙️ 환경 변수 (.env)

`.env` 파일은 bot.py 기준 동일 폴더에 위치

```env
DISCORD_TOKEN=
DEEPSEEK_API_KEY=
AI_PROVIDER=deepseek

GUILD_ID=
CLIENT_ID=

WELCOME_CHANNEL_ID=
AI_CHAT_CHANNEL_ID=
OWNER_ID=
DAILY_LIMIT=50
```

> ⚠️ 민감 정보는 Git에 커밋하지 않기!

---

## 🚀 봇 재시작

```bash
cd /home/wltn5548/cherang-bot
pm2 restart cherang
```

로그 확인:

```bash
pm2 logs cherang
tail -f ~/.pm2/logs/cherang-error.log
```

---

## 🔁 라파엘 데이터 업데이트

Slash 명령: `/라파엘업데이트`  
(관리자만 사용 가능)

수동:

```bash
cd /home/wltn5548/cherang-bot/raphael/raphael-rs/raphael-rs
git pull
pm2 restart cherang
```

---

## 🎯 주요 기능

| 기능 | 명령 방식 | 예시 |
|------|------|------|
| FF14 아이템 시세 | Slash | `/시세 황금장어` |
| FF14 날씨 | 자연어 | 울다하 날씨? |
| AI 챗봇 | 자연어 트리거 | 체랑 뭐해 |
| 제작/경제 | Slash | 기능 확장 중 |

---

### 자연어 트리거

| 카테고리 | 키워드 |
|------|------|
| 시세 | 시세, 가격, 얼마 |
| 날씨 | 날씨, 기상, 어때 |
| 대화 | 체랑, 야, 냐, 뭐해, 응 |

AI 응답은 `AI_CHAT_CHANNEL_ID` 채널에서만 동작

---

## 📁 Market / Weather 데이터

경로:

```
cherang-bot/data/
```

| 파일 | 설명 |
|------|------|
| kr_items.json | 아이템 ID |
| kr_detail.json | 설명/카테고리 |
| kr_icons.json | 아이콘 매핑 |

업데이트 필요 시 직접 갱신

---

### 날씨 데이터 업데이트

```
cherang-bot/ffxiv_weather.py
```

데이터 출처:  
https://github.com/Asvel/ffxiv-weather/blob/master/data/out/weathers.txt

KR 지역명 매핑 수동 반영

---

## ⚠️ 문제 & 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| Slash 무한로딩 | followup 처리 | 수정 완료 |
| AI 응답 2번 | 메인에서 직접 호출 | 제거 완료 |
| 그래프 너무 큼 | embed + file 분리 | 해결 |

---

## 📦 Backup

```bash
tar -czvf cherang-bot-backup.tar.gz /home/wltn5548/cherang-bot/
```

`.env` 포함 필수

---

## 🐈 운영 팁

- Slash 명령 추가 시 Sync 필요
- AI 호출 제한: 하루 50회
- Market/Weather 데이터는 정기 업데이트 필요
- 오류 발생 시 PM2 로그 확인

---

### ✨ END OF FILE
