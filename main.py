import json
import os
import sys
import urllib.error
import urllib.request


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY 환경변수를 설정해주세요.")

    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.8-flash:generateContent",
        data=json.dumps(
            {"contents": [{"parts": [{"text": "안녕하세요"}]}]}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"Gemini API 요청 실패: HTTP {error.code}")
    except urllib.error.URLError:
        sys.exit("Gemini API에 연결할 수 없습니다.")

    candidates = result.get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = "".join(part.get("text", "") for part in parts)
    if not text:
        sys.exit("Gemini API가 텍스트 응답을 반환하지 않았습니다.")
    print(text)


if __name__ == "__main__":
    main()
