# LLM Prompt Benchmark

Gemini API를 이용해 프롬프트 설계에 따른 응답 차이를 비교하는 미니 프로젝트입니다. 동일한 고객 문의 테스트셋에 프롬프트 v1/v2를 적용하고, 응답 내용·응답시간·토큰 사용량을 콘솔과 CSV에 기록합니다.

## 테스트 구성

- 고객 문의 5개: 결제 후 주문 상태 미반영, 중복 결제, 환불 지연, 인증 메일 미수신, 비밀번호 오류로 인한 로그인 불가
- 각 질문에 v1과 v2를 순서대로 적용하는 총 10개 조합
- 조합 간 2초 대기, 현재 사용 모델은 `gemini-3.8-flash`

| 프롬프트 | 특징 |
| --- | --- |
| v1 | “다음 고객 문의에 답변해주세요.”라는 최소한의 답변 지시 |
| v2 | 고객지원 담당자 역할, 문제 요약 → 확인 사항 → 다음 행동의 답변 구조, 확인되지 않은 사실을 단정하지 않는 기준, 간결하고 친절한 문체를 명시 |

각 API 요청의 입력은 `프롬프트 내용 + "\n\n고객 문의:\n" + 질문`으로 구성합니다.

## 파일 구조

| 파일 | 역할 |
| --- | --- |
| [main.py](main.py) | API 호출, 오류 처리, 응답시간·토큰 수 확인, 콘솔 출력과 CSV 저장 |
| [test_cases.json](test_cases.json) | `id`, `question`으로 구성된 고객 문의 5개 |
| [prompt_v1.txt](prompt_v1.txt) | 최소 지시 프롬프트 |
| [prompt_v2.txt](prompt_v2.txt) | 역할·답변 형식·작성 기준을 포함한 프롬프트 |
| [results.csv](results.csv) | 실행 결과. 질문·프롬프트 조합당 한 행이며 실행할 때마다 덮어쓰기 |

## 실행 방법

Python 3와 `GEMINI_API_KEY` 환경변수가 필요합니다. 외부 패키지 설치는 필요하지 않습니다.

프로젝트 루트에서 Bash로 실행합니다. 아래 명령은 키를 화면에 표시하지 않고 입력받습니다. API 키 자체를 README나 코드에 기록하지 마세요.

```bash
read -rs -p "GEMINI_API_KEY: " GEMINI_API_KEY
echo
export GEMINI_API_KEY
python3 main.py
```

결과는 콘솔에 출력되고 프로젝트 루트의 `results.csv`에 저장됩니다. CSV는 Excel에서 한글을 읽을 수 있도록 UTF-8 BOM(`utf-8-sig`)으로 작성합니다.

## 측정 및 저장 항목

| 항목 | 측정·처리 방식 |
| --- | --- |
| 응답 내용 | Gemini 응답에서 추출한 텍스트 |
| 응답시간(ms) | `time.perf_counter()`로 성공한 요청 직전부터 응답 본문 수신 완료까지 측정. 이전 실패 요청, 재시도 대기, 조합 간 대기, JSON 파싱 시간은 제외 |
| 입력·출력·전체 토큰 | `usageMetadata`의 `promptTokenCount`, `candidatesTokenCount`, `totalTokenCount` 사용 |
| 성공/실패·오류 | `status`에 `success` 또는 `failed`, 실패 원인은 `error`에 기록 |

토큰 정보가 없으면 콘솔에는 `정보 없음`, CSV에는 빈 칸으로 표시합니다. 전체 토큰 수는 API 반환값을 그대로 기록합니다. 실패 행의 응답·시간·토큰 칸은 비워 둡니다.

CSV 컬럼은 다음과 같습니다.

```text
case_id,question,prompt_version,response,response_time_ms,prompt_tokens,output_tokens,total_tokens,status,error
```

## 오류 처리

- **HTTP 429:** 재시도 없이 해당 조합을 실패 처리합니다.
- **HTTP 503:** 2초 대기 후 최대 1회 재시도합니다. 조합당 실제 요청은 최대 2회입니다.
- **timeout 및 기타 오류:** 해당 조합을 실패로 기록하고 다음 조합을 계속 실행합니다.

전체 결과를 CSV에 저장한 뒤, 실패한 조합이 있으면 종료 코드 `1`로 종료합니다.

## 현재 실험 상태

현재 `results.csv`는 재시도 정책 수정 전의 초기 실제 실행 결과입니다.

- 총 10개 조합 중 **성공 1개, 실패 9개**
- 실패: **HTTP 503 5개, HTTP 429 3개, timeout 1개**

과도한 재시도를 줄이기 위해 429는 재시도하지 않고, 503은 2초 후 최대 1회 재시도하도록 정책을 개선했습니다.

현재 결과만으로는 v1/v2의 응답 특성을 비교하기 부족합니다. **API 할당량 초기화 후 다시 실행할 예정입니다.**

## 기술 스택

- Python
- Gemini REST API
- Python standard library: `urllib.request`, `json`, `csv`, `time`, `pathlib` 등
