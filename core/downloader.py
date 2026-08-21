from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from html import unescape
import importlib.util
import subprocess
import sys
import os
import re


class DownloadError(RuntimeError):
    pass


def safe_output_filename(value: str) -> str:
    """Return a portable yt-dlp/file-system safe display filename."""
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip()).rstrip(". ")
    clean = re.sub(r"\s+", " ", clean)
    return (clean or "video")[:180]


# Ordered by priority when a copied share message contains more than one URL.
PLATFORM_HOSTS = {
    "Douyin": (
        "douyin.com",
        "v.douyin.com",
        "iesdouyin.com",
    ),
    "Bilibili": (
        "bilibili.com",
        "b23.tv",
        "bilibili.tv",
    ),
    "Youku": (
        "youku.com",
        "youku.tv",
    ),
    "Xiaohongshu": (
        "xiaohongshu.com",
        "xhslink.com",
    ),
    "TikTok": (
        "tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
    ),
    "YouTube": (
        "youtube.com",
        "youtu.be",
    ),
    "Facebook": (
        "facebook.com",
        "fb.watch",
    ),
    "Instagram": (
        "instagram.com",
    ),
    "X / Twitter": (
        "twitter.com",
        "x.com",
    ),
    "Vimeo": (
        "vimeo.com",
    ),
}

KNOWN_SUFFIXES = tuple(
    host
    for hosts in PLATFORM_HOSTS.values()
    for host in hosts
)

# Characters that often immediately follow URLs inside Chinese/Vietnamese share text.
TRAILING_URL_CHARS = (
    '.,;:!?)]}>\'"'
    '，。；：！？）】》、'
    '…'
)

HTTP_URL_RE = re.compile(
    r'https?://[^\s<>"\']+',
    flags=re.IGNORECASE,
)

# Also accept a copied short link with the scheme omitted.
BARE_KNOWN_URL_RE = re.compile(
    r'(?<![\w@])(?:'
    r'(?:v\.)?douyin\.com|'
    r'b23\.tv|'
    r'(?:www\.)?bilibili\.com|'
    r'(?:www\.)?youku\.com|'
    r'v\.youku\.com|'
    r'xhslink\.com|'
    r'(?:www\.)?xiaohongshu\.com|'
    r'(?:www\.)?tiktok\.com|'
    r'vm\.tiktok\.com|'
    r'youtu\.be|'
    r'(?:www\.)?youtube\.com'
    r')[^\s<>"\']*',
    flags=re.IGNORECASE,
)


def _clean_candidate_url(value: str) -> str:
    value = unescape(str(value or "")).strip()
    value = value.strip(TRAILING_URL_CHARS)

    # Copied text occasionally includes zero-width spaces.
    value = value.replace("\u200b", "").replace("\ufeff", "")

    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value

    # Normalize only the scheme/netloc; leave query/path intact.
    try:
        parts = urlsplit(value)
        if not parts.netloc:
            return value
        value = urlunsplit(
            (
                parts.scheme.lower() or "https",
                parts.netloc.lower(),
                parts.path,
                parts.query,
                parts.fragment,
            )
        )
    except Exception:
        pass

    return value.strip(TRAILING_URL_CHARS)


def detect_platform(url: str) -> str:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except Exception:
        host = ""

    for platform, hosts in PLATFORM_HOSTS.items():
        for item in hosts:
            if host == item or host.endswith("." + item):
                return platform

    return "Generic / yt-dlp"


def extract_video_url(text: str) -> str:
    """Extract the actual video URL from either a URL or a full share message.

    Examples accepted:
      - https://v.douyin.com/xxxx/
      - "0.07 复制... https://v.douyin.com/xxxx/ 复制此链接..."
      - Bilibili/B23 share text
      - Youku share text
    """
    raw = unescape(str(text or "")).strip()
    if not raw:
        raise DownloadError("Chưa nhập URL hoặc nội dung chia sẻ.")

    candidates = [_clean_candidate_url(x) for x in HTTP_URL_RE.findall(raw)]

    if not candidates:
        candidates = [_clean_candidate_url(x) for x in BARE_KNOWN_URL_RE.findall(raw)]

    # If the entire field is a clean URL but regex somehow missed it.
    if not candidates and re.match(r"^(?:https?://)?[\w.-]+\.[a-z]{2,}", raw, re.I):
        candidates = [_clean_candidate_url(raw)]

    if not candidates:
        raise DownloadError(
            "Không tìm thấy URL trong nội dung đã dán.\n\n"
            "Bạn có thể dán nguyên đoạn chia sẻ từ Douyin/Bilibili/Youku; "
            "app sẽ tự lấy link http/https bên trong."
        )

    # Prefer a known video platform if the text happens to contain several URLs.
    for candidate in candidates:
        try:
            host = (urlsplit(candidate).hostname or "").lower()
        except Exception:
            host = ""
        if any(host == h or host.endswith("." + h) for h in KNOWN_SUFFIXES):
            return candidate

    return candidates[0]


def _quality_format(quality: str) -> str:
    # Prefer MP4/H.264-ish delivery where the site exposes it, but retain
    # a generic fallback because Bilibili/Youku may expose different containers.
    if quality == "1080p":
        return (
            "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/"
            "bv*[height<=1080]+ba/"
            "b[height<=1080][ext=mp4]/b[height<=1080]/b"
        )
    if quality == "720p":
        return (
            "bv*[height<=720][ext=mp4]+ba[ext=m4a]/"
            "bv*[height<=720]+ba/"
            "b[height<=720][ext=mp4]/b[height<=720]/b"
        )
    return (
        "bv*[ext=mp4]+ba[ext=m4a]/"
        "bv*+ba/"
        "b[ext=mp4]/b"
    )


def _has_curl_cffi() -> bool:
    return importlib.util.find_spec("curl_cffi") is not None


def _windows_browser_cookie_roots(browser: str) -> list[Path]:
    if os.name != "nt":
        return []

    local = Path(os.environ.get("LOCALAPPDATA", ""))
    roaming = Path(os.environ.get("APPDATA", ""))
    b = (browser or "").lower()

    roots = {
        "chrome": [local / "Google" / "Chrome" / "User Data"],
        "edge": [local / "Microsoft" / "Edge" / "User Data"],
        "brave": [local / "BraveSoftware" / "Brave-Browser" / "User Data"],
        "firefox": [roaming / "Mozilla" / "Firefox" / "Profiles"],
    }
    return [x for x in roots.get(b, []) if str(x)]


def browser_cookie_database_exists(browser: str) -> bool:
    browser = (browser or "").strip().lower()

    if os.name != "nt":
        return True

    roots = _windows_browser_cookie_roots(browser)

    if browser == "firefox":
        for root in roots:
            if not root.exists():
                continue
            try:
                if any(root.glob("*/cookies.sqlite")):
                    return True
            except Exception:
                pass
        return False

    for root in roots:
        if not root.exists():
            continue
        try:
            for pattern in (
                "Default/Network/Cookies",
                "Profile */Network/Cookies",
                "Default/Cookies",
                "Profile */Cookies",
            ):
                if any(root.glob(pattern)):
                    return True
        except Exception:
            pass
    return False


def validate_cookie_file(path: str | None) -> str:
    if not path:
        return ""

    p = Path(path)
    if not p.exists() or not p.is_file():
        raise DownloadError("File cookies.txt không tồn tại.")

    try:
        head = p.read_text(
            encoding="utf-8",
            errors="replace",
        )[:4000]
    except Exception as e:
        raise DownloadError(f"Không đọc được file cookies: {e}")

    if head.lstrip().startswith(("{", "[")):
        raise DownloadError(
            "File cookie đang là JSON. yt-dlp cần cookies.txt định dạng Netscape."
        )

    return str(p.resolve())


def _cookie_error_kind(text: str) -> str:
    s = (text or "").lower()
    if "failed to decrypt with dpapi" in s:
        return "dpapi"
    if "could not copy chrome cookie database" in s:
        return "locked_db"
    if "could not find" in s and "cookie" in s and "database" in s:
        return "missing_db"
    if "fresh cookies" in s:
        return "fresh_cookies"
    if "sign in" in s or "login" in s or "authentication" in s:
        return "auth"
    return ""


def _friendly_cookie_error(kind: str, browser: str | None = None) -> str:
    b = (browser or "browser").capitalize()

    if kind == "dpapi":
        return (
            f"{b} cookie không giải mã được bằng DPAPI trên Windows. "
            "Hãy dùng cookies.txt trong app thay vì Auto đọc cookie từ Chrome/Edge."
        )

    if kind == "locked_db":
        return (
            f"{b} đang giữ khóa cookie database. Đóng hoàn toàn browser rồi thử lại, "
            "hoặc dùng cookies.txt."
        )

    if kind == "missing_db":
        return (
            f"Không tìm thấy cookie database của {b} trên máy này. "
            "Chọn browser khác hoặc dùng cookies.txt."
        )

    if kind == "fresh_cookies":
        return (
            "Site yêu cầu cookie mới. Hãy mở video trong browser, sau đó xuất "
            "cookies.txt mới và chọn file đó trong Downloader."
        )

    return ""


def _browser_candidates(selection: str) -> list[str | None]:
    value = (selection or "").strip().lower()

    if value in ("none", "không dùng cookies", "no cookies", "off"):
        return [None]

    if value in ("cookies.txt", "cookie file", "file cookies"):
        return []

    if value in ("", "auto", "tự động", "auto (khuyến nghị)", "auto an toàn"):
        # Windows Auto intentionally never touches browser cookie DB:
        # Chrome/Edge may fail DPAPI/App-Bound decryption and open browsers
        # may lock their databases.
        if os.name == "nt":
            return [None]

        return [
            None,
            *[
                b for b in ("chrome", "firefox")
                if browser_cookie_database_exists(b)
            ],
        ]

    if os.name == "nt" and not browser_cookie_database_exists(value):
        return []

    return [value]


def _strategy_list(
    platform: str,
    cookies_selection: str,
    cookies_file: str = "",
):
    selection = (cookies_selection or "").strip()
    value = selection.lower()
    can_impersonate = _has_curl_cffi()

    strategies = []
    prefer_impersonation = platform in {
        "Douyin", "Youku", "Xiaohongshu", "TikTok", "Instagram", "Facebook"
    }

    safe_cookie_file = validate_cookie_file(cookies_file) if cookies_file else ""

    def add(browser=None, cookie_file="", impersonate=False, label=""):
        strategies.append({
            "browser": browser,
            "cookie_file": cookie_file,
            "impersonate": bool(impersonate),
            "label": label,
        })

    is_auto = value in (
        "", "auto", "tự động", "auto (khuyến nghị)", "auto an toàn"
    )
    is_file_mode = value in (
        "cookies.txt", "cookie file", "file cookies"
    )

    if is_auto:
        if prefer_impersonation and can_impersonate:
            add(
                impersonate=True,
                label="không cookies + impersonate",
            )

        add(label="không cookies")

        if safe_cookie_file:
            if prefer_impersonation and can_impersonate:
                add(
                    cookie_file=safe_cookie_file,
                    impersonate=True,
                    label="cookies.txt + impersonate",
                )

            add(
                cookie_file=safe_cookie_file,
                label="cookies.txt",
            )

        # Critical: on Windows Auto stops here.
        if os.name == "nt":
            return strategies

    elif is_file_mode:
        if not safe_cookie_file:
            raise DownloadError(
                "Bạn đang chọn cookies.txt nhưng chưa chọn file cookie."
            )

        if prefer_impersonation and can_impersonate:
            add(
                cookie_file=safe_cookie_file,
                impersonate=True,
                label="cookies.txt + impersonate",
            )

        add(
            cookie_file=safe_cookie_file,
            label="cookies.txt",
        )
        return strategies

    browsers = _browser_candidates(selection)

    if not browsers and not is_auto:
        if value in ("edge", "chrome", "firefox", "brave"):
            raise DownloadError(
                f"Không tìm thấy profile/cookie database của {selection} trên máy. "
                "Hãy dùng cookies.txt hoặc browser khác."
            )

    for browser in browsers:
        if prefer_impersonation and can_impersonate:
            add(
                browser=browser,
                impersonate=True,
                label=f"{browser or 'không cookies'} + impersonate",
            )

        add(
            browser=browser,
            label=browser or "không cookies",
        )

    seen = set()
    unique = []

    for item in strategies:
        key = (
            item["browser"],
            item["cookie_file"],
            item["impersonate"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique


def _base_command(
    url: str,
    out: Path,
    quality: str,
    browser: str | None,
    cookie_file: str,
    impersonate: bool,
):
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--ignore-config",
        "--newline",
        "--no-playlist",
        "--continue",
        "--part",
        "--retries",
        "5",
        "--fragment-retries",
        "5",
        "--extractor-retries",
        "3",
        "--socket-timeout",
        "25",
        "--retry-sleep",
        "fragment:1",
        "--no-write-comments",
        "-f",
        _quality_format(quality),
        "--merge-output-format",
        "mp4",
        "--windows-filenames",
        "--trim-filenames",
        "180",
        "-o",
        str(out / "%(title).140B_%(id)s.%(ext)s"),
        "--print",
        "after_move:__MS_FILE__%(filepath)s",
    ]

    if cookie_file:
        cmd += ["--cookies", cookie_file]
    elif browser:
        cmd += ["--cookies-from-browser", browser]

    if impersonate:
        # curl_cffi provides the impersonation layer. `chrome` lets yt-dlp
        # select an available Chrome target.
        cmd += ["--impersonate", "chrome"]

    # `--` prevents a URL beginning with "-" from being interpreted as an option.
    cmd += ["--", url]
    return cmd


def _run_command(cmd, log=None):
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )

    lines = []
    files = []

    assert p.stdout is not None
    for raw_line in p.stdout:
        line = raw_line.rstrip("\r\n")
        lines.append(line)

        if line.startswith("__MS_FILE__"):
            path = line[len("__MS_FILE__"):].strip()
            if path:
                files.append(path)
        elif log:
            log(line)

    rc = p.wait()
    return rc, lines, files


def _error_looks_cookie_related(text: str) -> bool:
    s = text.lower()
    keys = (
        "cookies",
        "fresh cookies",
        "login",
        "sign in",
        "authentication",
        "captcha",
        "verify",
        "verification",
        "anti-bot",
        "403",
        "forbidden",
    )
    return any(k in s for k in keys)


def download_video(
    url: str,
    out_dir: str,
    quality: str = "Best MP4",
    cookies_browser: str = "Auto (khuyến nghị)",
    cookies_file: str = "",
    log=None,
):
    cleaned_url = extract_video_url(url)
    platform = detect_platform(cleaned_url)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if log:
        log(f"[MachineScope] Platform: {platform}")
        log(f"[MachineScope] URL đã làm sạch: {cleaned_url}")
        log(
            "[MachineScope] Cookie mode: "
            + ((cookies_browser or "").strip() or "Auto (khuyến nghị)")
        )
        if cookies_file:
            log(f"[MachineScope] Cookie file: {cookies_file}")

    strategies = _strategy_list(
        platform,
        cookies_browser,
        cookies_file=cookies_file,
    )

    cookie_failures = []
    last_tail = ""

    for index, strategy in enumerate(strategies, 1):
        browser = strategy["browser"]
        cookie_file = strategy.get("cookie_file", "")
        impersonate = strategy["impersonate"]

        if log:
            log("")
            log(
                f"[MachineScope] Thử {index}/{len(strategies)}: "
                f"{strategy['label']}"
            )

        cmd = _base_command(
            cleaned_url,
            out,
            quality,
            browser=browser,
            cookie_file=cookie_file,
            impersonate=impersonate,
        )

        rc, lines, files = _run_command(cmd, log=log)

        if rc == 0:
            existing = [x for x in files if Path(x).exists()]

            if log:
                log("[MachineScope] Tải thành công.")
                for file in existing:
                    log(f"[MachineScope] File: {file}")

            return {
                "output_dir": str(out),
                "files": existing or files,
                "url": cleaned_url,
                "platform": platform,
                "strategy": strategy["label"],
            }

        tail = "\n".join(lines[-45:])
        last_tail = tail

        kind = _cookie_error_kind(tail)
        if kind:
            friendly = _friendly_cookie_error(kind, browser)
            if friendly and friendly not in cookie_failures:
                cookie_failures.append(friendly)
                if log:
                    log("[MachineScope] " + friendly)

    if platform == "Douyin" and not cookies_file:
        msg = (
            "Douyin hiện thường yêu cầu fresh cookies. "
            "Khuyến nghị chọn cookies.txt vừa xuất từ browser."
        )
        if msg not in cookie_failures:
            cookie_failures.append(msg)

    error_lines = []

    for line in last_tail.splitlines():
        low = line.lower()
        if (
            "error:" in low
            or "fresh cookies" in low
            or "http error" in low
            or "unable to" in low
            or "unsupported url" in low
        ):
            error_lines.append(line.strip())

    concise_error = "\n".join(error_lines[-8:])
    if not concise_error:
        concise_error = "yt-dlp không tải được URL này."

    details = "\n\n".join(cookie_failures)

    raise DownloadError(
        f"Không tải được từ {platform}.\n"
        f"URL: {cleaned_url}\n\n"
        f"{concise_error}"
        + (f"\n\n{details}" if details else "")
    )


def yt_dlp_version() -> str:
    cmd = [sys.executable, "-m", "yt_dlp", "--version"]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if proc.returncode != 0:
            return "chưa sẵn sàng"

        lines = [
            line.strip()
            for line in (proc.stdout or "").splitlines()
            if line.strip()
        ]
        for line in reversed(lines):
            if re.fullmatch(
                r"(?:stable@|nightly@|master@)?\\d{4}\\.\\d{2}\\.\\d{2}(?:\\.\\d+)?",
                line,
            ):
                return line
        return lines[-1] if lines else "unknown"
    except Exception:
        return "unknown"


def update_yt_dlp(log=None):
    """Install/update yt-dlp nightly + recommended networking dependencies.

    yt-dlp's official README recommends trying nightly when a supported site
    breaks due to website changes.
    """
    packages = [
        "yt-dlp[default]",
        "curl-cffi",
    ]

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-U",
        "--pre",
        *packages,
    ]

    if log:
        log("[MachineScope] Đang cập nhật yt-dlp nightly + curl-cffi...")
        log("[MachineScope] " + " ".join(cmd))

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )

    lines = []
    assert p.stdout is not None
    for raw in p.stdout:
        line = raw.rstrip()
        lines.append(line)
        if log:
            log(line)

    rc = p.wait()
    if rc != 0:
        raise DownloadError(
            "Cập nhật yt-dlp thất bại:\n" + "\n".join(lines[-40:])
        )

    version = yt_dlp_version()
    if log:
        log(f"[MachineScope] yt-dlp hiện tại: {version}")
    return version
