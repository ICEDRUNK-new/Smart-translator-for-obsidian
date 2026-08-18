"""JSON-lines bridge between the Obsidian plugin and PDFMathTranslate's Python API.

The request is read as one JSON object from stdin. Protocol events are written to
stdout; output produced by PDFMathTranslate itself is redirected to stderr so it
cannot corrupt the protocol.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback
from typing import Any, TextIO
import importlib.util
import subprocess

PROTOCOL_OUT: TextIO = sys.stdout

REQUIRED_PACKAGES = ["peewee==3.18.2", "tencentcloud-sdk-python-tmt==3.1.121"]

def run_pip_and_decide(packages):
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install"] + packages,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise ValueError("pip install fail")
    
    output = result.stdout + result.stderr  # 合并以防信息在err里
    
    if "Successfully installed" in output or "成功安装" in output:
        return True 
    else:
        return False

def emit(event_type: str, **values: Any) -> None:
    payload = {"type": event_type, **values}
    PROTOCOL_OUT.write(json.dumps(payload, ensure_ascii=False) + "\n")
    PROTOCOL_OUT.flush()


def parse_pages(expression: str) -> list[int] | None:
    """Parse one-based user input such as ``1-3,5`` into zero-based pages."""
    normalized = expression.strip()
    if not normalized:
        return None

    pages: set[int] = set()
    for raw_part in normalized.split(","):
        part = raw_part.strip()
        if not part:
            raise ValueError("\u9875\u7801\u8868\u8FBE\u5F0F\u4E2D\u5B58\u5728\u7A7A\u9879")
        pieces = [piece.strip() for piece in part.split("-")]
        if len(pieces) == 1:
            page = _positive_page(pieces[0], part)
            pages.add(page - 1)
        elif len(pieces) == 2:
            start = _positive_page(pieces[0], part)
            end = _positive_page(pieces[1], part)
            if end < start:
                raise ValueError(f"\u9875\u7801\u8303\u56F4 {part!r} \u7684\u7ED3\u675F\u9875\u5C0F\u4E8E\u8D77\u59CB\u9875")
            pages.update(range(start - 1, end))
        else:
            raise ValueError(f"\u9875\u7801\u8303\u56F4 {part!r} \u683C\u5F0F\u9519\u8BEF")
    return sorted(pages)


def _positive_page(value: str, source: str) -> int:
    if not value.isdecimal():
        raise ValueError(f"\u9875\u7801 {source!r} \u4E0D\u662F\u6B63\u6574\u6570")
    page = int(value)
    if page < 1:
        raise ValueError("\u9875\u7801\u5FC5\u987B\u4ECE 1 \u5F00\u59CB")
    return page


def require_string(request: dict[str, Any], key: str) -> str:
    value = request.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"\u7F3A\u5C11\u6709\u6548\u5B57\u6BB5: {key}")
    return value.strip()


def configure_source(request: dict[str, Any]) -> Path:
    project_path = Path(require_string(request, "projectPath")).expanduser().resolve()
    package_file = project_path / "pdf2zh" / "__init__.py"
    if not package_file.is_file():
        raise ValueError(f"\u6E90\u7801\u76EE\u5F55\u4E2D\u6CA1\u6709 pdf2zh/__init__.py: {project_path}")
    sys.path.insert(0, str(project_path))
    return project_path


def configure_pdf2zh(request: dict[str, Any]) -> None:
    config_file = str(request.get("configFile", "")).strip()
    if not config_file:
        return
    config_path = Path(config_file).expanduser().resolve()
    if not config_path.is_file():
        raise ValueError(f"PDFMathTranslate \u914D\u7F6E\u6587\u4EF6\u4E0D\u5B58\u5728: {config_path}")
    from pdf2zh.config import ConfigManager

    ConfigManager.custome_config(str(config_path))


def ensure_openai_api_base_url(service: str, base_url: str) -> None:
    """Reject OpenAI-compatible base URLs that omit the required API prefix."""
    service_name = service.split(":", 1)[0].strip().lower()
    if service_name not in {"openai", "openailiked"}:
        return
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ValueError(f"{service_name} \u5C1A\u672A\u914D\u7F6E API Base URL")
    if normalized and not normalized.lower().endswith("/v1"):
        raise ValueError(
            f"{service_name} \u7684 API Base URL \u5FC5\u987B\u4EE5 /v1 \u7ED3\u5C3E\uFF0C\u5F53\u524D\u4E3A: {normalized}"
        )


def validate_translation_service_config(service: str) -> None:
    service_name = service.split(":", 1)[0].strip().lower()
    base_url_keys = {
        "openai": "OPENAI_BASE_URL",
        "openailiked": "OPENAILIKED_BASE_URL",
    }
    base_url_key = base_url_keys.get(service_name)
    if not base_url_key:
        return

    from pdf2zh.config import ConfigManager

    translator_envs = ConfigManager.get_translator_by_name(service_name) or {}
    default_url = "https://api.openai.com/v1" if service_name == "openai" else ""
    base_url = str(os.environ.get(base_url_key) or translator_envs.get(base_url_key) or default_url)
    ensure_openai_api_base_url(service_name, base_url)


def extract_model_ids(items: Any) -> list[str]:
    """Return stable unique model IDs from OpenAI-compatible model objects."""
    model_ids: set[str] = set()
    for item in items or []:
        value = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        if isinstance(value, str) and value.strip():
            model_ids.add(value.strip())
    return sorted(model_ids, key=str.casefold)


def get_openai_connection(service_name: str) -> tuple[str, str, dict[str, Any]]:
    """Resolve an OpenAI-compatible connection from PDFMathTranslate configuration."""
    connection_keys = {
        "openai": (
            "OPENAI_BASE_URL",
            "OPENAI_API_KEY",
            "https://api.openai.com/v1",
            None,
        ),
        "openailiked": (
            "OPENAILIKED_BASE_URL",
            "OPENAILIKED_API_KEY",
            "",
            "openailiked",
        ),
    }
    connection = connection_keys.get(service_name)
    if connection is None:
        raise ValueError("AI \u95EE\u7B54\u53EA\u652F\u6301 OpenAI \u548C OpenAI \u517C\u5BB9\u63A5\u53E3")

    from pdf2zh.config import ConfigManager

    base_url_key, api_key_key, default_url, default_api_key = connection
    translator_envs = ConfigManager.get_translator_by_name(service_name) or {}
    base_url = str(os.environ.get(base_url_key) or translator_envs.get(base_url_key) or default_url)
    api_key = os.environ.get(api_key_key) or translator_envs.get(api_key_key) or default_api_key
    ensure_openai_api_base_url(service_name, base_url)
    if not api_key:
        raise ValueError(f"{service_name} \u5C1A\u672A\u914D\u7F6E API Key")
    return base_url, str(api_key), translator_envs


def list_models(request: dict[str, Any]) -> None:
    project_path = configure_source(request)
    configure_pdf2zh(request)
    service_name = require_string(request, "service").split(":", 1)[0].lower()
    import openai

    base_url, api_key, _ = get_openai_connection(service_name)

    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    try:
        response = client.models.list()
        model_ids = extract_model_ids(getattr(response, "data", []))
    finally:
        client.close()
    if not model_ids:
        raise RuntimeError("\u6A21\u578B\u63A5\u53E3\u6CA1\u6709\u8FD4\u56DE\u4EFB\u4F55\u6A21\u578B ID")
    emit("models", models=model_ids, source=str(project_path))


def split_text_chunks(text: str, max_chars: int = 2500) -> list[str]:
    """Split a large selection without issuing concurrent translation requests."""
    normalized = text.strip()
    if not normalized:
        return []
    if max_chars < 200:
        raise ValueError("\u5212\u8BCD\u7FFB\u8BD1\u5206\u6BB5\u957F\u5EA6\u4E0D\u80FD\u5C0F\u4E8E 200 \u4E2A\u5B57\u7B26")

    chunks: list[str] = []
    remaining = normalized
    separators = ("\\n\\n", "\\n", "\u3002", "\uFF01", "\uFF1F", ". ", "! ", "? ", "; ", "\uFF1B")
    while len(remaining) > max_chars:
        minimum = max_chars // 2
        cut = max_chars
        candidates = [remaining.rfind(separator, minimum, max_chars + 1) for separator in separators]
        best = max(candidates, default=-1)
        if best >= minimum:
            cut = best + 1
        chunk = remaining[:cut].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def is_rate_limit_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        token in message
        for token in ("429", "rate_limit", "rate limit", "concurrency limit", "too many requests")
    )


def translate_chunk_with_retry(
    translator: Any,
    chunk: str,
    chunk_index: int,
    chunk_total: int,
    max_retries: int = 3,
) -> str:
    for attempt in range(max_retries + 1):
        try:
            translated = translator.translate(chunk)
            if not isinstance(translated, str) or not translated.strip():
                raise RuntimeError("\u7FFB\u8BD1\u670D\u52A1\u6CA1\u6709\u8FD4\u56DE\u6587\u672C\u7ED3\u679C")
            return translated.strip()
        except Exception as error:
            if not is_rate_limit_error(error):
                raise
            if attempt >= max_retries:
                raise RuntimeError(
                    "\u7FFB\u8BD1\u670D\u52A1\u6301\u7EED\u9650\u6D41\uFF08HTTP 429\uFF09\uFF1B\u5DF2\u81EA\u52A8\u91CD\u8BD5\u4ECD\u672A\u6062\u590D\u3002"
                    "\u8BF7\u7A0D\u540E\u518D\u8BD5\uFF0C\u6216\u964D\u4F4E\u5B8C\u6574 PDF \u7FFB\u8BD1\u7684\u7EBF\u7A0B\u6570\u3002"
                ) from error
            wait_seconds = min(2 ** (attempt + 1), 16)
            emit(
                "progress",
                current=chunk_index - 1,
                total=chunk_total,
                message=(
                    f"\u7FFB\u8BD1\u670D\u52A1\u9650\u6D41\uFF1A\u7B2C {chunk_index}/{chunk_total} \u6BB5\u5C06\u5728 "
                    f"{wait_seconds} \u79D2\u540E\u91CD\u8BD5\uFF08{attempt + 1}/{max_retries}\uFF09\u2026"
                ),
            )
            time.sleep(wait_seconds)

    raise RuntimeError("\u5212\u8BCD\u7FFB\u8BD1\u91CD\u8BD5\u72B6\u6001\u5F02\u5E38")


def doctor(request: dict[str, Any]) -> None:
    project_path = configure_source(request)
    configure_pdf2zh(request)
    service = str(request.get("service", "")).strip()
    if service:
        validate_translation_service_config(service)

    if sys.version_info < (3, 11) or sys.version_info >= (3, 13):
        raise RuntimeError(
            f"PDFMathTranslate 1.x \u8981\u6C42 Python >=3.11,<3.13\uFF0C\u5F53\u524D\u4E3A {sys.version.split()[0]}"
        )

    import pdf2zh
    from pdf2zh import translate, translate_stream

    if not callable(translate) or not callable(translate_stream):
        raise RuntimeError("pdf2zh.translate/translate_stream \u4E0D\u53EF\u8C03\u7528")

    emit(
        "doctor",
        version=getattr(pdf2zh, "__version__", "unknown"),
        python=sys.executable,
        source=str(project_path),
    )


def translate_pdf(request: dict[str, Any]) -> None:
    project_path = configure_source(request)
    configure_pdf2zh(request)

    input_path = Path(require_string(request, "inputPath")).expanduser().resolve()
    if not input_path.is_file() or input_path.suffix.lower() != ".pdf":
        raise ValueError(f"\u8F93\u5165\u6587\u4EF6\u4E0D\u662F\u53EF\u8BFB\u7684 PDF: {input_path}")

    output_dir = Path(require_string(request, "outputDir")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    lang_in = require_string(request, "langIn")
    lang_out = require_string(request, "langOut")
    service = require_string(request, "service")
    validate_translation_service_config(service)
    threads = int(request.get("threads", 4))
    if threads < 1 or threads > 64:
        raise ValueError("threads \u5FC5\u987B\u5728 1 \u5230 64 \u4E4B\u95F4")

    pages = parse_pages(str(request.get("pages", "")))

    from pdf2zh import __version__, translate
    from pdf2zh.doclayout import ModelInstance, OnnxModel

    if ModelInstance.value is None:
        emit("ready", message="\u6B63\u5728\u52A0\u8F7D PDFMathTranslate \u7248\u9762\u5206\u6790\u6A21\u578B\u2026")
        ModelInstance.value = OnnxModel.load_available()

    prompt_text = str(request.get("prompt", ""))
    prompt = None
    if prompt_text:
        from string import Template

        prompt = Template(prompt_text)

    def on_progress(progress: Any) -> None:
        emit(
            "progress",
            current=int(getattr(progress, "n", 0)),
            total=int(getattr(progress, "total", 0)),
            message="PDFMathTranslate Python API \u6B63\u5728\u7FFB\u8BD1\u2026",
        )

    emit("ready", message="\u5DF2\u8C03\u7528 pdf2zh.translate()\uFF0C\u51C6\u5907\u7FFB\u8BD1\u2026")
    results = translate(
        files=[str(input_path)],
        output=str(output_dir),
        pages=pages,
        lang_in=lang_in,
        lang_out=lang_out,
        service=service,
        thread=threads,
        callback=on_progress,
        compatible=bool(request.get("compatible", False)),
        model=ModelInstance.value,
        prompt=prompt,
        skip_subset_fonts=bool(request.get("skipSubsetFonts", False)),
        ignore_cache=bool(request.get("ignoreCache", False)),
    )
    if not results:
        raise RuntimeError("pdf2zh.translate() \u6CA1\u6709\u8FD4\u56DE\u7ED3\u679C")

    mono_path = Path(results[0][0]).resolve()
    dual_path = Path(results[0][1]).resolve()
    if not mono_path.is_file() or not dual_path.is_file():
        raise RuntimeError("pdf2zh.translate() \u8FD4\u56DE\u7684\u8BD1\u6587\u6587\u4EF6\u4E0D\u5B58\u5728")
    if output_dir not in mono_path.parents or output_dir not in dual_path.parents:
        raise RuntimeError("pdf2zh.translate() \u8FD4\u56DE\u4E86\u8F93\u51FA\u76EE\u5F55\u4EE5\u5916\u7684\u6587\u4EF6")

    emit(
        "result",
        mono=str(mono_path),
        dual=str(dual_path),
        version=__version__,
        source=str(project_path),
    )


def translate_text(request: dict[str, Any]) -> None:
    project_path = configure_source(request)
    configure_pdf2zh(request)

    text = require_string(request, "text")
    if len(text) > 50_000:
        raise ValueError("\u5212\u8BCD\u7FFB\u8BD1\u6587\u672C\u4E0D\u80FD\u8D85\u8FC7 50000 \u4E2A\u5B57\u7B26")

    lang_in = require_string(request, "langIn")
    lang_out = require_string(request, "langOut")
    service = require_string(request, "service")
    validate_translation_service_config(service)

    service_name, _, service_model = service.partition(":")
    from pdf2zh import __version__
    from pdf2zh import translator as translator_module
    from pdf2zh.translator import BaseTranslator

    translator_class = next(
        (
            candidate
            for candidate in vars(translator_module).values()
            if isinstance(candidate, type)
            and issubclass(candidate, BaseTranslator)
            and candidate is not BaseTranslator
            and getattr(candidate, "name", "") == service_name
        ),
        None,
    )
    if translator_class is None:
        raise ValueError(f"\u4E0D\u652F\u6301\u7684\u7FFB\u8BD1\u670D\u52A1: {service_name}")

    prompt_text = str(request.get("prompt", ""))
    prompt = None
    if prompt_text and getattr(translator_class, "CustomPrompt", False):
        from string import Template

        prompt = Template(prompt_text)

    emit("ready", message="\u6B63\u5728\u7FFB\u8BD1\u6240\u9009\u6587\u672C\u2026")
    translator = translator_class(
        lang_in,
        lang_out,
        service_model or None,
        envs={},
        prompt=prompt,
        ignore_cache=bool(request.get("ignoreCache", False)),
    )
    chunks = split_text_chunks(text)
    translated_chunks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        emit(
            "progress",
            current=index - 1,
            total=len(chunks),
            message=f"\u6B63\u5728\u7FFB\u8BD1\u7B2C {index}/{len(chunks)} \u6BB5\u2026",
        )
        translated_chunks.append(
            translate_chunk_with_retry(translator, chunk, index, len(chunks))
        )
        emit(
            "progress",
            current=index,
            total=len(chunks),
            message=f"\u5DF2\u5B8C\u6210\u7B2C {index}/{len(chunks)} \u6BB5",
        )

    translated = "\\n\\n".join(translated_chunks)

    emit(
        "text-result",
        text=translated.strip(),
        version=__version__,
        source=str(project_path),
    )


def main() -> int:
    import sys as _diag
    _diag.stderr.write(f"[DIAG] sys.executable={_diag.executable}\n")
    _diag.stderr.write(f"[DIAG] os.getcwd()={os.getcwd()}\n")
    _diag.stderr.write(f"[DIAG] sys.argv={sys.argv}\n")
    _diag.stderr.flush()
    try:
        run_pip_and_decide(REQUIRED_PACKAGES)
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("\u8BF7\u6C42\u5FC5\u987B\u662F JSON \u5BF9\u8C61")
        action = request.get("action")
        with contextlib.redirect_stdout(sys.stderr):
            if action == "doctor":
                doctor(request)
            elif action == "list_models":
                list_models(request)
            elif action == "translate":
                translate_pdf(request)
            elif action == "translate_text":
                translate_text(request)
            else:
                raise ValueError(f"\u4E0D\u652F\u6301\u7684\u64CD\u4F5C: {action!r}")
        _diag.stderr.write(f"[DIAG] About to return 0\n")
        _diag.stderr.flush()
        return 0
    except Exception as error:  # The bridge must always return a protocol error.
        traceback.print_exc(file=sys.stderr)
        _diag.stderr.write(f"[DIAG] EXCEPTION: {type(error).__name__}: {error}\n")
        _diag.stderr.write(f"[DIAG] About to return 1\n")
        _diag.stderr.flush()
        emit("error", message=str(error), errorType=type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())