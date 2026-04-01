# 범용 내신 시험지 PDF 파싱 및 구조화 자동화 (Phase 1)

한국 중/고등학교 내신 시험지(영어) PDF를 파싱하여 정형화된 JSON으로 변환하는 자동화 파이프라인입니다.

## 🎯 프로젝트 목표

- **PDF 자동 파싱**: PyMuPDF(fitz)를 사용한 안정적인 한국어 문서 처리
- **구조화된 데이터**: 시험 메타데이터, 문항, 선택지를 정형 JSON으로 변환
- **다단계 LLM 추출**: Gemini API를 활용한 의미 기반 자동 추출
- **열단 레이아웃 처리**: 동적 컬럼 경계 탐지 및 읽기 순서 자동화
- **박스 텍스트 분류**: 지문박스(text_box) vs 조건박스(condition_box) 자동 구분

## 📁 프로젝트 구조

```
exam_parser/
├── main.py                   # 파이프라인 진입점
├── config.py                 # 경로, API 키, 상수
├── parser/
│   ├── pdf_loader.py         # PDF 로드 및 페이지 관리
│   ├── block_extractor.py    # get_text("dict") 기반 블록 추출
│   ├── image_extractor.py    # 이미지 크롭 및 저장
│   └── box_detector.py       # 사각형 감지 → text_box/condition_box 분류
├── layout/
│   ├── column_splitter.py    # 동적 컬럼 경계 탐지
│   ├── reading_order.py      # 헤더/좌단/우단/스패닝/푸터 정렬
│   └── question_grouper.py   # 문항 번호 감지 및 그룹화
├── llm/
│   ├── prompt_builder.py     # LLM 프롬프트 생성
│   ├── gemini_client.py      # Gemini API 호출
│   └── schema_validator.py   # Pydantic 검증
├── models/
│   └── schema.py             # Pydantic 모델 정의
├── output/
│   └── writer.py             # JSON 파일 저장
└── images/                   # 추출된 이미지 저장 (런타임 생성)
```

## 🚀 빠른 시작

### 1. 설치

```bash
cd /Users/81070/workspace/hwp-auto-generator-onClaude
pip install -r requirements.txt
```

### 2. API 키 설정

```bash
cp .env.example .env
# .env 파일 편집:
# - ANTHROPIC_API_KEY (Claude Vision - 권장)
# - GEMINI_API_KEY (Gemini - 텍스트 기반 PDF용)
```

### 3. PDF 파싱

#### 방법 1: Claude Vision (권장) ⭐
스캔된 이미지 기반 PDF에 최적화. 95-99% 정확도.

```bash
python3 exam_parser/main_vision.py <pdf_파일_경로>
```

#### 방법 2: 텍스트 기반 PDF
원본 PDF(복사 가능한 텍스트)용.

```bash
python3 exam_parser/main.py <pdf_파일_경로>
```

**결과 파일:**
- `output/result.json` - 구조화된 시험지 데이터
- `images/*.png` - 추출된 이미지 (필요시)

## 📊 출력 JSON 형식

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
          "content": "She walked slowly through..."
        },
        {
          "type": "text_box",
          "content": "지문 박스 내용"
        }
      ],
      "choices": ["① option1", "② option2", "③ option3", "④ option4", "⑤ option5"],
      "sub_questions": []
    }
  ]
}
```

## 🔑 핵심 기능

### 1. 블록 추출 (block_extractor.py)
- PyMuPDF의 `get_text("dict")` 사용
- 텍스트 블록과 이미지 블록 구분
- Bbox 좌표 보존 (y축: 0=상단)

### 2. 박스 분류 (box_detector.py)
- `page.get_drawings()` → 사각형 탐지
- 채움색 분석:
  - 흰색/무채우기 → `text_box` (지문 박스)
  - 회색/음영 → `condition_box` (조건, 보기 박스)
  - 박스 없음 → `text` (일반 텍스트)

### 3. 동적 컬럼 경계 탐지 (column_splitter.py)
- 페이지 중앙 1/3 영역에서 블록 분포 분석
- 좌단 최대 x1과 우단 최소 x0의 중간값을 경계로 사용
- 15px dead-zone으로 경계 근처 오분류 방지

### 4. 읽기 순서 정렬 (reading_order.py)
```
헤더 (y0 < 60px)
  ↓
좌단 블록 (y0 정렬)
  ↓
스패닝 블록 삽입 (중앙 가로 박스)
  ↓
우단 블록 (y0 정렬)
  ↓
푸터 (y0 > page_height - 50px)
```

### 5. 문항 그룹화 (question_grouper.py)
- 정규식: `^[\[\(]?(\d{1,2})[\]\)\.]?\s`
- 페이지 경계에서 문항 번호 상태 유지
- 페이지를 넘는 문항 처리 지원

### 6. LLM 기반 추출 (gemini_client.py)
- Gemini API를 활용한 의미 기반 구조 추출
- 최대 3회 재시도 + JSON 파싱
- 지시문, 지문, 선택지, 점수 자동 분류

## ⚙️ 설정값 (config.py)

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `HEADER_THRESHOLD` | 60px | 헤더 구간 상단 경계 |
| `FOOTER_THRESHOLD` | 50px | 푸터 구간 하단 경계 |
| `DEAD_ZONE` | 15px | 컬럼 경계 근처 오분류 방지 범위 |
| `MIN_IMAGE_AREA` | 5000px² | 무시할 최소 이미지 면적 |
| `MAX_RETRIES` | 3 | LLM 추출 재시도 횟수 |
| `LLM_TIMEOUT` | 30s | API 호출 타임아웃 |

## 🐛 알려진 함정 및 대응

| 함정 | 대응 방법 |
|------|---------|
| 페이지 회전 | `page.derotation_matrix` 적용 |
| 선택지 블록 분리 | ①②③④⑤ 연속 블록 병합 |
| 장식용 이미지 | 5000px² 미만 제외 |
| LLM JSON 파싱 실패 | Pydantic 검증 + 3회 재시도 |
| 점수 표기 다양성 | `[\[\(\〔](\d+\.?\d*)점[\]\)\〕]` 정규식 |
| 컬럼 경계 오분류 | 15px dead-zone 적용 |

## 📋 검증 체크리스트

- [ ] 실제 내신 시험지 PDF 1~2개로 `main.py` 실행
- [ ] `result.json` 확인: 문항 순서, q_number 정확도
- [ ] `./images/` 폴더: 이미지 크롭 품질 확인
- [ ] 박스 텍스트: `text_box` / `condition_box` 분류 정확도 (수동 검증)
- [ ] LLM 응답: Pydantic 검증 통과율 >95%

## 🔄 다음 단계 (Phase 2)

- HWP 파일 자동 생성 (Windows 환경)
- 한글 문서 템플릿 적용
- 이미지 임베딩 및 레이아웃 자동화

## 📚 의존성

- **PyMuPDF (fitz)**: PDF 처리 (C 기반, 빠른 성능)
- **Pillow**: 이미지 처리
- **pydantic**: 데이터 스키마 검증
- **google-generativeai**: Gemini API
- **python-dotenv**: 환경변수 관리

## 📝 라이선스

프로젝트별 정의
