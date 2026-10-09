import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def call_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY 환경변수를 설정해주세요.")

    max_retries = 1
    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.8-flash:generateContent",
            data=json.dumps(
                {"contents": [{"parts": [{"text": prompt}]}]}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            started_at = time.perf_counter()
            with urllib.request.urlopen(request, timeout=60) as response:
                response_body = response.read()
                finished_at = time.perf_counter()
            result = json.loads(response_body)
            response_time_ms = (finished_at - started_at) * 1000
            break
        except urllib.error.HTTPError as error:
            error.close()
            if error.code != 503 or attempt == max_retries:
                sys.exit(f"Gemini API 요청 실패: HTTP {error.code}")
            wait_seconds = 2 ** (attempt + 1)
            print(
                f"HTTP {error.code}: {wait_seconds}초 후 재시도 "
                f"({attempt + 1}/{max_retries})"
            )
            time.sleep(wait_seconds)
        except urllib.error.URLError:
            sys.exit("Gemini API에 연결할 수 없습니다.")

    candidates = result.get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = "".join(part.get("text", "") for part in parts)
    if not text:
        sys.exit("Gemini API가 텍스트 응답을 반환하지 않았습니다.")
    usage_metadata = result.get("usageMetadata")
    if not isinstance(usage_metadata, dict):
        usage_metadata = {}
    token_usage = {
        "input_tokens": usage_metadata.get("promptTokenCount"),
        "output_tokens": usage_metadata.get("candidatesTokenCount"),
        "total_tokens": usage_metadata.get("totalTokenCount"),
    }
    return text, response_time_ms, token_usage


def main():
    with open(Path(__file__).with_name("test_cases.json"), encoding="utf-8") as file:
        test_cases = json.load(file)

    prompts = {}
    for version in ("v1", "v2"):
        prompt_path = Path(__file__).with_name(f"prompt_{version}.txt")
        prompts[version] = prompt_path.read_text(encoding="utf-8")

    failed_count = 0
    call_count = 0
    results = []
    for test_case in test_cases:
        case_id = test_case["id"]
        question = test_case["question"]
        print(f"\n{'=' * 40}")
        print(f"테스트 케이스 {case_id}")
        print(f"질문: {question}")
        for version, prompt_content in prompts.items():
            if call_count:
                time.sleep(2)
            call_count += 1
            print(f"\n프롬프트 버전: {version}")
            final_prompt = prompt_content + "\n\n고객 문의:\n" + question
            result = {
                "case_id": case_id,
                "question": question,
                "prompt_version": version,
                "response": "",
                "response_time_ms": "",
                "prompt_tokens": "",
                "output_tokens": "",
                "total_tokens": "",
                "status": "failed",
                "error": "",
            }
            try:
                text, response_time_ms, token_usage = call_gemini(final_prompt)
            except (SystemExit, Exception) as error:
                failed_count += 1
                result["error"] = str(error)
                results.append(result)
                print(f"실패: {error}")
                continue
            result.update(
                response=text,
                response_time_ms=response_time_ms,
                prompt_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"],
                total_tokens=token_usage["total_tokens"],
                status="success",
            )
            results.append(result)
            print(f"Gemini 응답:\n{text}")
            print(f"응답시간: {response_time_ms:.0f} ms")
            for label, key in (
                ("입력", "input_tokens"),
                ("출력", "output_tokens"),
                ("전체", "total_tokens"),
            ):
                value = token_usage[key]
                print(f"{label} 토큰 수: {value if value is not None else '정보 없음'}")

    with open(
        Path(__file__).with_name("results.csv"),
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "case_id",
                "question",
                "prompt_version",
                "response",
                "response_time_ms",
                "prompt_tokens",
                "output_tokens",
                "total_tokens",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    if failed_count:
        total_calls = len(test_cases) * len(prompts)
        sys.exit(f"Gemini 호출 {total_calls}회 중 {failed_count}회 실패했습니다.")


if __name__ == "__main__":
    main()
