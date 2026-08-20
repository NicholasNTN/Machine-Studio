from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib import request, error
import base64
import json
import time
import uuid

from .models import Scene
from . import gemini_engine as gemini


class AIProviderError(RuntimeError):
    pass


@dataclass
class AIConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 150


PROVIDER_DEFAULTS = {
    "Google Gemini": {
        "base_url": "",
        "model": "gemini-3.7-flash",
    },
    "CKEY": {
        "base_url": "https://api.xah.io/v1",
        "model": "levuphong2909/gemini-3.7-flash-high",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
}


def normalize_provider(value: str) -> str:
    raw = (value or "").strip().lower()
    return {
        "google": "Google Gemini",
        "gemini": "Google Gemini",
        "google gemini": "Google Gemini",
        "ckey": "CKEY",
        "openai": "OpenAI",
        "deepseek": "DeepSeek",
    }.get(raw, value or "CKEY")


def provider_defaults(provider: str) -> dict:
    return dict(
        PROVIDER_DEFAULTS.get(
            normalize_provider(provider),
            PROVIDER_DEFAULTS["CKEY"],
        )
    )


def chat_endpoint(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise AIProviderError("Chưa nhập Base URL.")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _friendly_http(provider: str, status: int, raw: str) -> str:
    low = (raw or "").lower()
    prefix = f"{provider} HTTP {status}"

    if status == 401 or "unauthorized" in low or "invalid api key" in low:
        return f"{prefix}: API key không hợp lệ hoặc chưa được cấp quyền."
    if status == 402 or "payment required" in low or "insufficient balance" in low:
        return f"{prefix}: API key/tài khoản không đủ số dư."
    if status == 403:
        return f"{prefix}: API từ chối quyền truy cập."
    if status == 404:
        return f"{prefix}: không tìm thấy endpoint/model. Kiểm tra Base URL và Model."
    if status == 429 or "quota" in low or "rate limit" in low:
        return (
            f"{prefix}: request đang bị rate-limit/quota/capacity. "
            "Xem Raw response trong Log để biết lỗi upstream thật."
        )
    if status >= 500:
        return f"{prefix}: máy chủ API đang lỗi."
    return f"{prefix}: {raw[:1000]}"


def _extract_text(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except Exception:
        content = response.get("output_text", "") if isinstance(response, dict) else ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item.get("content"), str):
                parts.append(item["content"])
        return "\n".join(parts)

    return str(content or "")


def _call_chat(
    config: AIConfig,
    messages: list[dict],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    log=None,
    retry_429: int = 0,
) -> str:
    provider = normalize_provider(config.provider)
    key = (config.api_key or "").strip()
    model = (config.model or "").strip()

    if not key:
        raise AIProviderError(f"Chưa nhập API key cho {provider}.")
    if not model:
        raise AIProviderError("Chưa nhập Model.")

    endpoint = chat_endpoint(config.base_url)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        payload["max_tokens"] = int(max_tokens)

    body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    client_request_id = str(uuid.uuid4())

    image_count = 0
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, list):
            image_count += sum(
                1
                for item in content
                if isinstance(item, dict)
                and item.get("type") == "image_url"
            )

    if log:
        log("[AI REQUEST]")
        log(f"[AI] Provider: {provider}")
        log(f"[AI] Endpoint: POST {endpoint}")
        log(f"[AI] Model: {model}")
        log(f"[AI] Client Request ID: {client_request_id}")
        log(f"[AI] Payload: {len(body):,} bytes")
        if image_count:
            log(f"[AI] Frames: {image_count}")

    attempts = max(1, int(retry_429) + 1)

    for attempt in range(1, attempts + 1):
        req = request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "MachineScope-Studio/1.0.7",
                "X-Client-Request-Id": client_request_id,
            },
        )

        started = time.perf_counter()

        try:
            with request.urlopen(
                req,
                timeout=max(15, int(config.timeout_seconds)),
            ) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                elapsed = time.perf_counter() - started
                status = int(getattr(resp, "status", 200))
                headers = {
                    str(k).lower(): str(v)
                    for k, v in resp.headers.items()
                }

                try:
                    obj = json.loads(raw)
                except Exception as e:
                    if log:
                        log("[AI RESPONSE]")
                        log(f"[AI] HTTP: {status}")
                        log(f"[AI] Latency: {elapsed:.2f}s")
                        log(f"[AI] Raw success body: {raw[:4000]}")
                    raise AIProviderError(
                        f"{provider} HTTP {status}: response không phải JSON hợp lệ.\n"
                        f"Raw response: {raw[:1800]}"
                    ) from e

                request_id = (
                    headers.get("x-request-id")
                    or headers.get("request-id")
                    or headers.get("cf-ray")
                    or (
                        str(obj.get("id"))
                        if isinstance(obj, dict) and obj.get("id")
                        else ""
                    )
                )

                usage = obj.get("usage", {}) if isinstance(obj, dict) else {}
                if not isinstance(usage, dict):
                    usage = {}

                prompt_tokens = (
                    usage.get("prompt_tokens")
                    or usage.get("input_tokens")
                    or 0
                )
                completion_tokens = (
                    usage.get("completion_tokens")
                    or usage.get("output_tokens")
                    or 0
                )
                total_tokens = (
                    usage.get("total_tokens")
                    or (prompt_tokens + completion_tokens)
                )

                if log:
                    log("[AI RESPONSE]")
                    log(f"[AI] HTTP: {status}")
                    log(f"[AI] Latency: {elapsed:.2f}s")
                    if request_id:
                        log(f"[AI] Request ID: {request_id}")
                    if usage:
                        log(
                            "[AI] Tokens: "
                            f"input={prompt_tokens} "
                            f"output={completion_tokens} "
                            f"total={total_tokens}"
                        )
                    log(f"[AI] Response: {len(raw.encode('utf-8')):,} bytes")

                text = _extract_text(obj).strip()
                if not text:
                    if log:
                        log(f"[AI] Raw success body: {raw[:4000]}")
                    raise AIProviderError(
                        f"{provider} HTTP {status}: API trả về thành công nhưng không có content.\n"
                        f"Raw response: {raw[:1800]}"
                    )

                return text

        except error.HTTPError as e:
            elapsed = time.perf_counter() - started
            raw = e.read().decode("utf-8", errors="replace")
            status = int(e.code)
            headers = {
                str(k).lower(): str(v)
                for k, v in (e.headers.items() if e.headers else [])
            }
            request_id = (
                headers.get("x-request-id")
                or headers.get("request-id")
                or headers.get("cf-ray")
                or ""
            )

            if log:
                log("[AI ERROR]")
                log(f"[AI] HTTP: {status}")
                log(f"[AI] Latency: {elapsed:.2f}s")
                if request_id:
                    log(f"[AI] Request ID: {request_id}")
                log(f"[AI] Raw error: {raw[:4000]}")

            if status == 429 and attempt < attempts:
                retry_after = headers.get("retry-after", "")
                try:
                    wait_seconds = float(retry_after)
                except Exception:
                    wait_seconds = 1.5 * attempt

                wait_seconds = max(0.8, min(8.0, wait_seconds))
                if log:
                    log(
                        f"[AI] {provider} HTTP 429 -> retry "
                        f"{attempt + 1}/{attempts} sau {wait_seconds:.1f}s"
                    )
                time.sleep(wait_seconds)
                continue

            message = _friendly_http(provider, status, raw)
            if request_id:
                message += f"\nRequest ID: {request_id}"
            if raw:
                message += f"\nRaw response: {raw[:1800]}"
            raise AIProviderError(message) from e

        except error.URLError as e:
            raise AIProviderError(
                f"{provider}: không kết nối được API: {getattr(e, 'reason', e)}"
            ) from e
        except TimeoutError as e:
            raise AIProviderError(
                f"{provider}: request quá thời gian chờ."
            ) from e
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(
                f"{provider}: lỗi gọi API: {e}"
            ) from e

    raise AIProviderError(f"{provider}: request thất bại không xác định.")


def _json_payload(text: str):
    raw = (text or "").strip()
    for candidate in (
        raw,
        raw.replace("```json", "").replace("```", "").strip(),
    ):
        try:
            return json.loads(candidate)
        except Exception:
            pass

    clean = raw.replace("```json", "").replace("```", "").strip()
    starts = [(clean.find("{"), clean.rfind("}")), (clean.find("["), clean.rfind("]"))]
    for start, end in starts:
        if start >= 0 and end > start:
            try:
                return json.loads(clean[start:end + 1])
            except Exception:
                pass
    raise AIProviderError("AI không trả JSON hợp lệ.")


def test(config: AIConfig, log=None) -> str:
    provider = normalize_provider(config.provider)
    if provider == "Google Gemini":
        return gemini.test(config.api_key, config.model)

    return _call_chat(
        config,
        [{"role": "user", "content": "Reply with exactly OK"}],
        temperature=0.0,
        max_tokens=16,
        log=log,
        retry_429=1,
    )


def _image_data_url(path: str) -> str:
    p = Path(path)
    mime = {
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(p.suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def fast_analyze_and_script(
    config: AIConfig,
    scenes: list[Scene],
    market: str = "US",
    style: str = "Factory documentary",
    audio_path: str = "",
    log=None,
):
    provider = normalize_provider(config.provider)

    if provider == "Google Gemini":
        return gemini.fast_analyze_and_script(
            api_key=config.api_key,
            model=config.model,
            scenes=scenes,
            market=market,
            style=style,
            audio_path=audio_path,
        )

    if not scenes:
        raise AIProviderError("Không có frame để AI phân tích.")

    prompt = f"""You are the single-pass video analyst and script writer for MachineScope Studio.

TARGET MARKET: {market}
STYLE: {style}

You will receive representative video frames.

Do all tasks in one pass:
1. Understand what the whole video is showing.
2. Identify machines/materials/processes only when reasonably confident.
3. Read useful visible Chinese text when legible. Never invent unreadable text.
4. Write ORIGINAL narration for every supplied time segment.
5. Use natural US English, not literal translation.
6. Scene 0 must be a strong curiosity hook.
7. Keep narration short enough for each scene, about 2.0-2.3 English words/sec.
8. Never fabricate exact specifications/numbers/names unless supported by evidence.
9. Provide Vietnamese translation for verification.

Return ONLY this JSON object shape:
{{
  "topic": "short topic",
  "summary": "2-5 concise sentences",
  "transcript": "",
  "scenes": [
    {{
      "index": 0,
      "visual": "visible action",
      "chinese_text": "legible Chinese or empty",
      "source_meaning": "concise meaning",
      "en_voice": "original US narration",
      "vi_voice": "Vietnamese translation"
    }}
  ]
}}

Return one scene object for EVERY supplied frame index.
"""

    content = [{"type": "text", "text": prompt}]
    for scene in scenes:
        content.append({
            "type": "text",
            "text": (
                f"FRAME index={scene.index}; "
                f"time={scene.start:.2f}-{scene.end:.2f}s; "
                f"duration={scene.duration:.2f}s"
            ),
        })
        content.append({
            "type": "image_url",
            "image_url": {
                "url": _image_data_url(scene.frame_path),
                "detail": "low",
            },
        })

    if audio_path:
        content.append({
            "type": "text",
            "text": (
                "Source audio exists locally but is not attached in this "
                "OpenAI-compatible vision request. Use the supplied frames."
            ),
        })

    try:
        raw = _call_chat(
            config,
            [{"role": "user", "content": content}],
            temperature=0.25,
            log=log,
            retry_429=2,
        )
    except AIProviderError as e:
        low = str(e).lower()
        if provider == "DeepSeek" and (
            "image" in low or "multimodal" in low or "content" in low
        ):
            raise AIProviderError(
                "DeepSeek model đang chọn không hỗ trợ ảnh. "
                "Hãy dùng CKEY/Google/OpenAI model có Vision để AI hiểu video."
            ) from e
        raise

    obj = _json_payload(raw)
    if not isinstance(obj, dict):
        raise AIProviderError("AI phải trả JSON object.")

    by_index = {}
    for item in obj.get("scenes", []) or []:
        try:
            by_index[int(item.get("index"))] = item
        except Exception:
            continue

    for scene in scenes:
        item = by_index.get(scene.index, {})
        scene.visual = str(item.get("visual", "") or "").strip()
        scene.chinese_text = str(item.get("chinese_text", "") or "").strip()
        scene.source_meaning = str(item.get("source_meaning", "") or "").strip()
        scene.en_voice = str(item.get("en_voice", "") or "").strip()
        scene.vi_voice = str(item.get("vi_voice", "") or "").strip()

    return {
        "topic": str(obj.get("topic", "") or "").strip(),
        "summary": str(obj.get("summary", "") or "").strip(),
        "transcript": str(obj.get("transcript", "") or "").strip(),
        "scenes": scenes,
    }


def translate_srt_file(
    config: AIConfig,
    source_path: str,
    output_path: str,
    target_language: str = "English (US)",
    custom_prompt: str = "",
    log=None,
) -> str:
    provider = normalize_provider(config.provider)

    if provider == "Google Gemini":
        return gemini.translate_srt_file(
            config.api_key,
            config.model,
            source_path,
            output_path,
            target_language,
            custom_prompt,
        )

    from .subtitle_engine import parse_srt

    src = Path(source_path)
    if not src.exists():
        raise AIProviderError(f"Không tìm thấy subtitle: {source_path}")

    cues = parse_srt(
        src.read_text(encoding="utf-8-sig", errors="replace")
    )
    if not cues:
        raise AIProviderError("Không đọc được cue SRT nào để dịch.")

    translated = {}
    batch_size = 60

    for pos in range(0, len(cues), batch_size):
        batch = cues[pos:pos + batch_size]
        payload = [
            {"index": pos + i, "text": text}
            for i, (_, _, text) in enumerate(batch)
        ]

        prompt = f"""Translate subtitle lines to {target_language}.
Use natural concise wording for video subtitles.
Preserve names and technical terminology.
Do not add facts.
Do not merge or split indexes.
{custom_prompt.strip()}

Return ONLY JSON array:
[{{"index":0,"text":"translated subtitle"}}]

INPUT:
{json.dumps(payload, ensure_ascii=False)}
"""

        raw = _call_chat(
            config,
            [{"role": "user", "content": prompt}],
            temperature=0.15,
            log=log,
            retry_429=2,
        )
        arr = _json_payload(raw)
        if isinstance(arr, dict):
            arr = (
                arr.get("items")
                or arr.get("results")
                or arr.get("translations")
                or []
            )
        if not isinstance(arr, list):
            raise AIProviderError("AI dịch subtitle không trả JSON array.")

        for item in arr:
            try:
                translated[int(item.get("index"))] = str(
                    item.get("text", "")
                ).strip()
            except Exception:
                continue

    def srt_ts(sec: float) -> str:
        ms = int(round(max(0, sec) * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    blocks = []
    for i, (start, end, original) in enumerate(cues):
        body = translated.get(i, original)
        blocks.append(
            f"{i + 1}\n"
            f"{srt_ts(start)} --> {srt_ts(end)}\n"
            f"{body}\n"
        )

    Path(output_path).write_text(
        "\n".join(blocks),
        encoding="utf-8-sig",
    )
    return output_path
