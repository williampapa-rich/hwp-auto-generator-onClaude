# 아키텍처 및 처리 흐름

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        PDF Input File                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────┐
        │    PDFLoader (pdf_loader.py)     │
        │   - Open PDF & validate          │
        │   - Provide page iterator        │
        └──────────────────┬───────────────┘
                           │
        ┌──────────────────┴───────────────────────────────────┐
        │                                                       │
        ▼                                                       ▼
┌──────────────────────────────┐               ┌──────────────────────────┐
│  BlockExtractor              │               │   ImageExtractor         │
│  (block_extractor.py)        │               │   (image_extractor.py)   │
│ - get_text("dict")           │               │ - Extract & crop images  │
│ - Normalize block data       │               │ - Save to ./images/      │
│ - Preserve coordinates       │               │ - Return image paths     │
└──────────────┬───────────────┘               └──────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│    BoxDetector               │
│   (box_detector.py)          │
│ - Detect rectangles via      │
│   page.get_drawings()        │
│ - Classify:                  │
│   • text_box (white/no fill) │
│   • condition_box (shaded)   │
│   • text (no box)            │
└──────────────┬───────────────┘
               │
        ┌──────┴────────────────────────────────┐
        │   BlockWithBoxType[] (classified)     │
        └──────┬─────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   ColumnSplitter             │
│  (column_splitter.py)        │
│ - Analyze x-coordinates      │
│   in middle 1/3 of page      │
│ - Find column boundary       │
│ - Classify: left/right/span  │
└──────────────┬───────────────┘
               │
        ┌──────┴──────────────────────────────────┐
        │ Left[] | Right[] | Spanning[] Blocks    │
        └──────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   ReadingOrderManager        │
│  (reading_order.py)          │
│ Header → Left(y-sort) →      │
│   Spanning → Right(y-sort)   │
│        → Footer              │
└──────────────┬───────────────┘
               │
        ┌──────┴──────────────────────────┐
        │  Ordered[] Blocks               │
        └──────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│   QuestionGrouper            │
│  (question_grouper.py)       │
│ - Detect Q numbers via regex │
│ - Group blocks by Q#         │
│ - Handle page spanning       │
└──────────────┬───────────────┘
               │
        ┌──────┴────────────────────────┐
        │  QuestionGroup[] Array        │
        └──────┬───────────────────────┘
               │
        ┌──────┴────────────────────┬──────────────────┐
        │ For Each Question         │                  │
        ▼                           ▼                  │
  ┌──────────────────┐   ┌──────────────────┐        │
  │ PromptBuilder    │   │ MetadataPrompt   │        │
  │(prompt_builder)  │   │ (first page)     │        │
  │ - Format blocks  │   └────────┬─────────┘        │
  │ - Create prompt  │            │                  │
  └────────┬─────────┘            │                  │
           │                      │                  │
           ▼                      ▼                  │
  ┌──────────────────────────────────────┐          │
  │      GeminiClient API Call           │          │
  │     (gemini_client.py)               │          │
  │ - Send prompt to Gemini              │          │
  │ - Parse JSON response                │          │
  │ - Retry on error (max 3x)            │          │
  └────────┬─────────────────────────────┘          │
           │                                         │
           ▼                                         │
  ┌──────────────────────────────────────┐          │
  │   SchemaValidator                    │          │
  │  (schema_validator.py)               │          │
  │ - Pydantic validation                │          │
  │ - Type coercion                      │          │
  │ - Field defaults                     │          │
  └────────┬─────────────────────────────┘          │
           │                                         │
           ▼                                         │
        Question[]  ◄───────────────────────────────┘
           │
           │  (Aggregate all pages)
           ▼
  ┌──────────────────────────────────────┐
  │      OutputWriter                    │
  │      (output/writer.py)              │
  │ - Create ExamPaper object            │
  │ - Serialize to JSON                  │
  │ - Write result.json                  │
  └────────┬─────────────────────────────┘
           │
           ▼
      result.json
      (structured exam data)
```

## 데이터 흐름: 상세 예시

### 입력: PDF 페이지

```
┌─────────────────────────────────────┐
│  Page 1 (2 columns)                 │
├─────────────────┬───────────────────┤
│ 1) Read the ... │ 1) 다음을 읽고..  │ ← Header
├─────────────────┼───────────────────┤
│ Once upon a     │ She walked fast   │
│ time there      │ through the      │
│ was a young     │ forest alone.    │ ← Main content
│ girl.           │                   │
├─────────────────┼───────────────────┤
│ ① option1       │ ② option2        │ ← Choices (spanning)
│ ③ option3       │ ④ option4        │
│ ⑤ option5       │                   │
├─────────────────┴───────────────────┤
│ [3점]                               │ ← Footer
└─────────────────────────────────────┘
```

### 처리 단계

**Step 1: BlockExtractor**
```
Extracted blocks (y-coord):
  [0] TEXT "1) Read the..." (y=10) [BOX-TYPE: text]
  [1] TEXT "1) 다음을 읽고..." (y=15) [BOX-TYPE: text]
  [2] TEXT "Once upon a time..." (y=50) [BOX-TYPE: text]
  [3] TEXT "She walked fast..." (y=55) [BOX-TYPE: text_box]
  [4] TEXT "① option1" (y=200) [BOX-TYPE: text]
  [5] TEXT "② option2" (y=210) [BOX-TYPE: text]
  [6] TEXT "[3점]" (y=500) [BOX-TYPE: text]
```

**Step 2: ColumnSplitter**
```
Detected boundary: x=300px

Left column (x < 285):
  [0] "1) Read the..." (x0=10, x1=150)
  [2] "Once upon a time..." (x0=20, x1=280)
  [4] "① option1" (x0=15, x1=100)

Right column (x > 315):
  [1] "1) 다음을 읽고..." (x0=320, x1=450)
  [3] "She walked fast..." (x0=330, x1=550)
  [5] "② option2" (x0=325, x1=450)

Spanning (boundaries):
  [6] "[3점]" (x0=200, x1=400)
```

**Step 3: ReadingOrderManager**
```
Ordered by reading sequence:
  [0] Header: "1) Read the..."
  [1] Header: "1) 다음을 읽고..."
  [2] Left-main: "Once upon a time..."
  [3] Right-main: "She walked fast..."
  [4] Left-main: "① option1"
  [5] Right-main: "② option2"
  [6] Spanning: "[3점]"
```

**Step 4: QuestionGrouper**
```
Detected question number: "1"

QuestionGroup:
  q_number: "1"
  blocks: [all above 7 blocks]
  start_page: 0
  end_page: 0
```

**Step 5: LLM Extraction (PromptBuilder + GeminiClient)**
```
USER PROMPT:
─────────────────────
Question Number: 1

Stimulus content (in reading order):
[TEXT] 1) Read the...
[TEXT] 1) 다음을 읽고...
[TEXT] Once upon a time...
[TEXT_BOX] She walked fast...
[TEXT] ① option1
[TEXT] ② option2
[TEXT] [3점]

Extract structured data...
─────────────────────

GEMINI RESPONSE:
{
  "q_number": "1",
  "q_type": "multiple_choice",
  "points": 3.0,
  "instruction": "Read the passage and choose...",
  "stimulus": [
    {"type": "text", "content": "Once upon a time..."},
    {"type": "text_box", "content": "She walked fast..."}
  ],
  "choices": ["① option1", "② option2", ...],
  "sub_questions": []
}
```

**Step 6: OutputWriter**
```
Final JSON Structure:
{
  "metadata": {
    "school_name": null,
    "year": null,
    "semester": null,
    ...
  },
  "questions": [
    { /* Q1 */ },
    { /* Q2 */ },
    ...
  ]
}
```

## 좌/우 컬럼 경계 탐지 알고리즘

```
Step 1: 페이지 중앙 1/3 구간에서 블록 분포 분석
        ┌────────────────┬────────────────┬────────────────┐
        │    Left 1/3    │   Middle 1/3   │   Right 1/3    │
        │   (분석 X)     │   (분석 O)     │   (분석 X)     │
        └────────────────┴────────────────┴────────────────┘

Step 2: 중간 1/3 영역의 블록들
        Left column blocks:
          Block A: x1=280
          Block B: x1=290   ← max(left_x1) = 290

        Right column blocks:
          Block C: x0=310   ← min(right_x0) = 310
          Block D: x0=320

Step 3: Boundary = (290 + 310) / 2 = 300

Step 4: Dead-zone 적용 (± 15px)
        Left zone:   x < 285
        Dead zone:   285 ≤ x ≤ 315
        Right zone:  x > 315

        블록이 dead-zone에 걸치면 spanning으로 분류
```

## 박스 타입 분류 알고리즘

```
For each text block:
  ┌─ Find overlapping rectangles (page.get_drawings())
  │
  ├─ No rectangle found
  │   └─ TYPE = "text"
  │
  └─ Rectangle found
      │
      ├─ Check fill color
      │   │
      │   ├─ fill == None (no fill / white)
      │   │   └─ TYPE = "text_box"
      │   │
      │   └─ fill != None (colored/grayscale)
      │       │
      │       ├─ RGB average > 0.95 (nearly white)
      │       │   └─ TYPE = "text_box"
      │       │
      │       └─ RGB average ≤ 0.95 (shaded)
      │           └─ TYPE = "condition_box"
```

## Pydantic 검증 흐름

```
LLM Response JSON
       │
       ▼
SchemaValidator.validate_question()
       │
       ├─ Check required fields
       ├─ Apply defaults (q_type, stimulus, choices)
       ├─ Type coercion (str → float for points)
       ├─ List validation (stimulus items, choices)
       │
       ├─ SUCCESS
       │   └─ Return Question object
       │
       └─ VALIDATION_ERROR
           └─ Log error, return None
               (Question skipped, continue to next)
```

## 에러 처리 및 재시도

```
LLM API Call
       │
       ├─ JSON Parse Error
       │   ├─ Attempt 1 → Fail
       │   ├─ Sleep 0.5s
       │   ├─ Attempt 2 → Fail
       │   ├─ Sleep 0.5s
       │   ├─ Attempt 3 → Fail
       │   └─ Return None
       │
       └─ Connection Error
           ├─ Attempt 1 → Fail
           ├─ Sleep 1s
           ├─ Attempt 2 → Fail
           ├─ Sleep 1s
           ├─ Attempt 3 → Fail
           └─ Return None
```

## 성능 특성

| 작업 | 시간 | 병목 |
|------|------|------|
| PDF 로드 | ~100ms | PyMuPDF (효율적) |
| 페이지당 블록 추출 | ~50ms | get_text("dict") |
| 박스 감지 (페이지) | ~30ms | get_drawings() 순회 |
| 컬럼 분리 | ~10ms | 계산 |
| 읽기 순서 정렬 | ~5ms | 정렬 |
| 문항 그룹화 | ~10ms | 정규식 |
| **LLM 호출 (문항당)** | **~2-5s** | **Gemini API** |
| Pydantic 검증 | ~10ms | 계산 |
| JSON 저장 | ~50ms | 디스크 I/O |

**전체**: 5페이지, 20문항 = ~15-20초 (LLM 시간 지배적)

## 확장 포인트 (Phase 2+)

1. **다른 LLM 지원**
   - `GeminiClient` 상속 → `ClaudeClient`, `GPTClient`
   - `PromptBuilder` 추상화 → 모델별 프롬프트 변형

2. **HWP 생성**
   - `exam_parser/hwp/` 모듈
   - `hwp_writer.py` → Python-pptx 유사 API

3. **배치 처리**
   - `exam_parser/batch/` 모듈
   - 여러 PDF 병렬 처리

4. **캐싱**
   - 이미지 해시 기반 중복 제거
   - LLM 응답 캐시 (로컬 DB)

5. **메트릭 수집**
   - 추출 정확도 (F1 score)
   - LLM 토큰 사용량
   - 처리 시간 분포
