# PotensiaAI Writer API Documentation

## Overview

The PotensiaAI Writer API is a FastAPI-based RESTful service that provides AI-powered blog content generation and validation capabilities.

## Architecture

```
api/
├── main.py          # FastAPI application entry point
├── router.py        # API endpoints and request/response models
└── __init__.py      # Package initialization

ai_tools/writer/
├── topic_refiner.py # Topic refinement module (OpenAI)
├── generator.py     # Content generation module (OpenAI + Claude fallback)
├── validator.py     # Content quality validation module (OpenAI)
└── prompts.py       # System prompts and templates
```

## Key Improvements Applied

### ✅ AsyncOpenAI & AsyncAnthropic Integration
All modules now use async clients for proper async/await support:
- `AsyncOpenAI` in validator.py, generator.py, topic_refiner.py
- `AsyncAnthropic` in generator.py
- Prevents event loop blocking in FastAPI

### ✅ Enhanced JSON Parsing (validator.py)
- Regex-based markdown code block removal
- Handles various formats: ` ```json`, ` ``` `, etc.
- More robust than simple string slicing

### ✅ Smart Model Detection (validator.py)
- Auto-detects reasoning models (o1, o3, gpt-5)
- Uses appropriate parameters:
  - Reasoning models: `max_completion_tokens` (no temperature)
  - Regular models: `max_tokens` + `temperature`

## API Endpoints

### Base URL
```
http://localhost:8000
```

### 1. Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "PotensiaAI Writer API",
  "timestamp": "2025-11-07T23:51:28.276019"
}
```

---

### 2. Topic Refinement
Converts a raw keyword into a natural, SEO/AEO-friendly question-style title.

```http
POST /api/refine
Content-Type: application/json

{
  "topic": "python web scraping"
}
```

**Response:**
```json
{
  "status": "success",
  "input_topic": "python web scraping",
  "refined_topic": "파이썬 웹 스크래핑을 어떤 순서로 배워야 할까?"
}
```

---

### 3. Content Validation
Analyzes blog content for quality, AI detection, and SEO optimization.

```http
POST /api/validate
Content-Type: application/json

{
  "content": "# Your blog content here...",
  "model": "gpt-4o-mini"  // Optional: defaults to settings.MODEL_PRIMARY
}
```

**Response:**
```json
{
  "status": "success",
  "validation": {
    "grammar_score": 9,
    "human_score": 8,
    "seo_score": 7,
    "has_faq": true,
    "suggestions": [
      "서론을 더 자세히 작성하세요.",
      "예제 코드에 주석을 추가하세요.",
      "키워드를 더 자연스럽게 배치하세요."
    ]
  }
}
```

**Validation Criteria:**
- **grammar_score** (0-10): Spelling, punctuation, readability
- **human_score** (0-10): How natural vs AI-generated it sounds
- **seo_score** (0-10): Keyword optimization, header structure, meta info
- **has_faq**: Boolean - presence of FAQ section
- **suggestions**: List of actionable improvements (Korean)

---

### 4. Full Pipeline
Executes the complete workflow: refine → generate → validate

```http
POST /api/write
Content-Type: application/json

{
  "topic": "python web scraping",
  "model": "gpt-4o-mini"  // Optional
}
```

**Response:**
```json
{
  "status": "success",
  "input_topic": "python web scraping",
  "refined_topic": "파이썬 웹 스크래핑을 어떤 순서로 배워야 할까?",
  "content": "# Full blog article content here...",
  "validation": {
    "grammar_score": 9,
    "human_score": 8,
    "seo_score": 7,
    "has_faq": true,
    "suggestions": [...]
  }
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "status": "error",
  "detail": "Error description here"
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (e.g., empty topic/content)
- `500`: Internal Server Error (e.g., OpenAI API failure)

---

## Running the Server

### Method 1: Using main.py
```bash
cd C:\Users\USER\potensia_ai
python api/main.py
```

### Method 2: Using uvicorn directly
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Production (without reload)
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Testing

### Interactive API Documentation
FastAPI provides auto-generated interactive docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Module Tests
Run the test script to verify all modules:
```bash
python test_api.py
```

### Manual Testing with curl

**Test health:**
```bash
curl http://localhost:8000/api/health
```

**Test refine:**
```bash
curl -X POST http://localhost:8000/api/refine \
  -H "Content-Type: application/json" \
  -d @test_refine.json
```

**Test validate:**
```bash
curl -X POST http://localhost:8000/api/validate \
  -H "Content-Type: application/json" \
  -d @test_validate.json
```

---

## Configuration

### Environment Variables (.env)
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MODEL_PRIMARY=gpt-4o-mini
MODEL_FALLBACK=claude-3-5-sonnet-20240620
```

### Model Support
**Primary Models (OpenAI):**
- `gpt-4o-mini` (recommended for cost/performance)
- `gpt-4o`
- `o1-preview`, `o3-mini` (reasoning models)

**Fallback Models (Anthropic):**
- `claude-3-5-sonnet-20241022`
- `claude-3-opus-20240229`

---

## Performance Characteristics

### Topic Refinement
- **Duration**: ~5-15 seconds
- **Tokens**: ~150-300 tokens
- **Model**: settings.MODEL_PRIMARY

### Content Generation
- **Duration**: ~20-60 seconds
- **Tokens**: ~2000-5000 tokens
- **Model**: GPT (primary) → Claude (fallback on error)

### Content Validation
- **Duration**: ~3-10 seconds
- **Tokens**: ~500-800 tokens
- **Model**: settings.MODEL_PRIMARY or custom

---

## Dependencies

```
fastapi>=0.121.0
uvicorn[standard]>=0.38.0
pydantic>=2.12.0
pydantic-settings>=2.11.0
python-dotenv>=1.2.0
openai>=2.7.0
anthropic>=0.72.0
```

Install all:
```bash
pip install fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv openai anthropic
```

---

## Next Steps

### Recommended Improvements
1. **Logging**: Replace `print()` with `logging` or `loguru` for production
2. **Error Response Structure**: Add `status` field for consistency
3. **Rate Limiting**: Implement rate limiting for production use
4. **Caching**: Add Redis caching for frequently requested topics
5. **Authentication**: Add API key authentication for production
6. **Monitoring**: Integrate with monitoring tools (Sentry, DataDog, etc.)

### Production Deployment
```bash
# Using gunicorn + uvicorn workers
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## License

Part of PotensiaAI project.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
