# Railway 배포 가이드

## 1. Railway 프로젝트 설정

### Railway CLI 설치 (선택사항)
```bash
npm i -g @railway/cli
```

### Railway에 로그인
```bash
railway login
```

## 2. 프로젝트 연결

### 기존 Railway 프로젝트에 연결
```bash
railway link
```

또는 새 프로젝트 생성:
```bash
railway init
```

## 3. 환경 변수 설정

Railway 대시보드 또는 CLI를 통해 다음 환경 변수를 설정해야 합니다:

### 필수 환경 변수
```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# Application Settings
APP_NAME=PotensiaAI
ENV=production
LOG_LEVEL=INFO

# OpenAI Models (선택사항, 기본값 사용 가능)
MODEL_PRIMARY=gpt-4o-mini
MODEL_FALLBACK=gpt-3.5-turbo
DEFAULT_TEMPERATURE=0.7

# Retry Settings (선택사항)
MAX_RETRIES=3
BACKOFF_MIN=1
BACKOFF_MAX=10
```

### Railway CLI로 환경 변수 설정
```bash
railway variables set OPENAI_API_KEY="sk-..."
railway variables set APP_NAME="PotensiaAI"
railway variables set ENV="production"
railway variables set LOG_LEVEL="INFO"
```

### Railway 대시보드에서 설정
1. Railway 프로젝트 대시보드 접속
2. Variables 탭 선택
3. 위 환경 변수들을 하나씩 추가

## 4. 배포

### Git을 통한 자동 배포 (권장)
```bash
git add .
git commit -m "Add Railway deployment configuration"
git push origin main
```

Railway는 자동으로 main 브랜치의 변경사항을 감지하고 배포합니다.

### Railway CLI를 통한 수동 배포
```bash
railway up
```

## 5. 배포 확인

### Health Check
배포가 완료되면 Railway가 제공하는 URL로 헬스 체크:
```bash
curl https://your-project.up.railway.app/api/health
```

예상 응답:
```json
{
  "status": "ok",
  "app": "PotensiaAI",
  "env": "production"
}
```

### API 테스트
```bash
curl -X POST https://your-project.up.railway.app/api/write/refine \
  -H "Content-Type: application/json" \
  -d '{"topic":"테스트 주제"}'
```

## 6. 프론트엔드 연결

Railway 배포가 완료되면 프론트엔드의 `.env` 파일을 업데이트:

```env
VITE_API_BASE_URL="https://your-project.up.railway.app"
```

## 7. 문제 해결

### 로그 확인
```bash
railway logs
```

### 서비스 재시작
```bash
railway restart
```

### 현재 배포 상태 확인
```bash
railway status
```

## 8. 현재 Railway URL 확인

Railway 대시보드에서 실제 배포 URL을 확인하세요:
1. Railway 프로젝트 선택
2. Settings → Domains
3. 생성된 Railway 도메인 확인

현재 설정된 URL이 `https://potensiaai-production.up.railway.app`와 다를 수 있습니다.

## 9. CORS 설정 확인

`main.py`의 CORS 설정이 올바른지 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 참고사항

- Railway는 기본적으로 Python 3.11+을 사용합니다
- `requirements.txt`가 루트 디렉토리에 있어야 합니다
- `main.py`가 애플리케이션의 진입점이어야 합니다
- Railway는 자동으로 포트를 할당하며 `$PORT` 환경 변수로 접근합니다
