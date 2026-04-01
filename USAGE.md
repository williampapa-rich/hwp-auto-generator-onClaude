# 사용 가이드

## 초기 설정

### 1단계: 의존성 설치

```bash
cd /Users/81070/workspace/hwp-auto-generator-onClaude
pip install -r requirements.txt
```

**검증:**
```bash
python -c "import fitz; import pydantic; print('✓ All dependencies installed')"
```

### 2단계: API 키 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 API 키 입력:
```
GEMINI_API_KEY=your_actual_api_key_here
```

**Gemini API 키 획득:**
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 방문
2. "Create API Key" 클릭
3. 키 복사 → `.env`에 붙여넣기

## 기본 사용법

### 단일 PDF 파싱

```bash
python exam_parser/main.py sample.pdf
```

**출력:**
```
📄 Loading PDF: sample.pdf
📊 Total pages: 5

🔍 Extracting metadata...
  Processing page 0... ✓
  Processing page 1... ✓
  Processing page 2... ✓
  Processing page 3... ✓
  Processing page 4... ✓

📝 Extracting questions...
  Q1: ✓
  Q2: ✓
  ...

✅ Parsed 20 questions

✓ Exam data written to output/result.json

🎉 Success! Results saved to output/
```

**결과 파일:**
- `output/result.json` - 구조화된 시험지 데이터
- `images/page_000_img_00.png` - 추출된 이미지

## 고급 사용법

### 기본 검증 (LLM 없이)

```bash
python test_parser.py sample.pdf
```

LLM을 호출하지 않고 기본 추출만 테스트:
- 블록 추출
- 박스 분류
- 컬럼 경계 감지
- 읽기 순서 정렬
- 문항 그룹화

**출력 예시:**
```
🧪 Testing PDF: sample.pdf

📊 Total pages: 5
📄 Page 0 dimensions: 595x842px

📦 Extracted 45 blocks:
  0: 0 | 1) Read the passage bel... | bbox=(50.0, 50.0, 500.0, 70.0)
  1: 0 | Once upon a time there... | bbox=(60.0, 80.0, 280.0, 200.0)
  2: 0 | She walked slowly throu... | bbox=(320.0, 85.0, 550.0, 205.0)
  ...

🎯 Box classification:
  text: 40
  text_box: 3
  condition_box: 2

📐 Column split at x=300.0:
  Left blocks: 22
  Right blocks: 19
  Spanning blocks: 4

📖 Reading order: 45 blocks
  0: y=50 | 1) Read the passage...
  1: y=80 | Once upon a time...
  ...

❓ Question groups: 20
  Q1: 2 blocks (pages 0-0)
  Q2: 3 blocks (pages 0-1)
  ...

✅ Test completed
```

### 프로그래밍 방식으로 사용

```python
from exam_parser.main import ExamPaperParser

# PDF 파싱
parser = ExamPaperParser("sample.pdf")
exam = parser.parse()

# 결과 접근
for question in exam.questions:
    print(f"Q{question.q_number}: {question.q_type}")
    if question.choices:
        print(f"  선택지: {len(question.choices)}개")
    print(f"  점수: {question.points or 'N/A'}")
```

### 커스텀 설정

`config.py` 수정:

```python
# 헤더/푸터 구간 조정 (px)
HEADER_THRESHOLD = 80  # 기본값: 60
FOOTER_THRESHOLD = 70  # 기본값: 50

# 컬럼 경계 dead-zone 확대 (비대칭 PDF 대응)
DEAD_ZONE = 25  # 기본값: 15

# 이미지 최소 크기 조정
MIN_IMAGE_AREA = 3000  # 기본값: 5000 (더 많은 이미지 포함)

# LLM 재시도 횟수
MAX_RETRIES = 5  # 기본값: 3

# API 타임아웃 증가 (느린 인터넷)
LLM_TIMEOUT = 60  # 기본값: 30
```

## 결과 해석

### JSON 구조

```json
{
  "metadata": {
    "school_name": "서울고등학교",
    "year": 2025,
    "semester": 1,
    "exam_type": "중간",
    "grade": 2,
    "subject": "영어",
    "total_pages": 5
  },
  "questions": [
    {
      "q_number": "1",
      "q_type": "multiple_choice",
      "points": 3.0,
      "instruction": "다음 글의 빈칸에 들어갈 말로 가장 적절한 것을 고르시오.",
      "stimulus": [
        {
          "type": "text",
          "content": "Once upon a time there was a young girl."
        },
        {
          "type": "text_box",
          "content": "She walked slowly through the forest."
        }
      ],
      "choices": [
        "① alone",
        "② quickly",
        "③ happily",
        "④ slowly",
        "⑤ quietly"
      ],
      "sub_questions": []
    }
  ]
}
```

### 각 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `q_number` | str | 문항 번호 ("1", "1-1", "1가" 등) |
| `q_type` | str | "multiple_choice" 또는 "subjective" |
| `points` | float \| null | 배점 (없으면 null) |
| `instruction` | str \| null | 지시문 (없으면 null) |
| `stimulus` | StimulusItem[] | 지문, 이미지, 박스 배열 |
| `choices` | str[] | 선택지 배열 (객관식만) |
| `sub_questions` | str[] | 하위 문항 (가), (나) 등 |

### Stimulus Type

| 타입 | 설명 |
|------|------|
| `text` | 일반 문단 텍스트 |
| `text_box` | 흰 테두리 사각형 내부 텍스트 |
| `condition_box` | 회색/음영 사각형 (조건, 보기) |
| `image` | 이미지 (경로: `images/page_XXX_img_YY.png`) |

## 일반적인 문제 해결

### 1. API 키 오류

```
Error: GEMINI_API_KEY not set
```

**해결:**
```bash
# .env 파일 확인
cat .env | grep GEMINI_API_KEY

# 유효한 API 키 있는지 확인
# https://aistudio.google.com/app/apikey
```

### 2. PDF 로드 실패

```
FileNotFoundError: PDF not found: sample.pdf
```

**해결:**
```bash
# 절대 경로 사용
python exam_parser/main.py /full/path/to/sample.pdf

# 또는 현재 디렉토리 확인
ls -la *.pdf
```

### 3. 블록 추출 문제 (이미지가 없거나 텍스트가 누락)

**디버깅:**
```bash
# test_parser.py로 기본 추출 확인
python test_parser.py sample.pdf

# 출력에서:
# - 추출된 블록 수
# - 박스 분류 결과
# - 컬럼 경계 감지 결과
# - 문항 그룹화 결과
```

**예상 원인:**
- PDF가 이미지 기반 (OCR 필요)
- 비표준 레이아웃 (컬럼 경계 감지 실패)
- 특수 문자 인코딩 문제

### 4. LLM 응답 파싱 실패

```
⚠️  Q1: LLM extraction failed
```

**디버깅:**
1. gemini_client.py에서 response.text 출력 추가
2. JSON 형식 확인
3. 프롬프트 조정

**해결:**
```python
# exam_parser/llm/gemini_client.py
print(f"Raw response: {response_text}")  # 추가
```

### 5. 컬럼 경계 오감지

이미지나 텍스트가 중복되거나 누락되는 경우:

```python
# config.py
DEAD_ZONE = 25  # 기본 15px에서 증대
```

또는 `test_parser.py` 결과에서:
```
📐 Column split at x=???:
  Left blocks: ???
  Right blocks: ???
  Spanning blocks: ???
```

을 확인하여 레이아웃 패턴 파악.

### 6. 메모리 부족

대용량 PDF (>100 페이지)의 경우:

```python
# 한 번에 1페이지씩만 처리하도록 수정
# (현재 메인 파이프라인은 이미 페이지 단위 처리)
```

## 성능 최적화

### 1. 병렬 처리 (여러 PDF)

```bash
# 간단한 배치 처리
for pdf in pdfs/*.pdf; do
  python exam_parser/main.py "$pdf"
done
```

### 2. 캐싱

현재 미지원. Phase 2에서 추가 예정:
- LLM 응답 캐싱
- 이미지 중복 제거

### 3. LLM 호출 최소화

불필요한 문항 스킵:
```python
# main.py에서 커스터마이징
if group.q_number in skip_questions:
    continue
```

## 검증 체크리스트

새로운 PDF로 파싱 후 확인:

- [ ] `output/result.json` 생성됨
- [ ] 메타데이터 정확도 (학교명, 학년, 과목)
- [ ] 문항 순서 정확 (좌/우단 섞임 없음)
- [ ] 모든 q_number 감지됨
- [ ] 선택지 개수 정확
- [ ] 점수 표기 올바르게 추출됨
- [ ] 이미지가 `images/` 폴더에 저장됨
- [ ] 박스 텍스트가 text_box로 분류됨
- [ ] 조건/보기 텍스트가 condition_box로 분류됨

## 다음 단계

- **Phase 2**: HWP 파일 자동 생성
- **Phase 3**: UI/웹 인터페이스
- **Phase 4**: 배치 처리 및 API 서버

자세한 내용은 [README.md](README.md)와 [ARCHITECTURE.md](ARCHITECTURE.md) 참조.
