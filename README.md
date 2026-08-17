# PDF Math Translate for Obsidian

An Obsidian desktop plugin that connects scientific-PDF reading workflows with **PDFMathTranslate**, **PDF++**, and optionally **Claudian**.

The plugin can translate complete PDFs or selected pages, batch-process PDFs in a vault, translate selected PDF text, create Markdown annotations with precise PDF++ backlinks, and bridge selected PDF text to Claudian for grounded Q&A.

> Current plugin version: **0.7.2**

## Features

### PDF translation

- Translate the active PDF.
- Pick a PDF from the vault and translate it.
- Batch-select and translate multiple PDFs.
- Batch-translate PDFs from a folder, with already translated files recognized and skipped where possible.
- Cancel the current translation and queued jobs.
- Choose source/target language, translation service, model, thread count, and page range such as `1-3,5`.
- Optional custom prompt loaded from a Markdown note in the vault.
- Output monolingual PDF only, or both monolingual and bilingual PDFs.
- Optional translation-summary Markdown note with Obsidian links/embeds to the generated PDFs.
- Optional compatibility mode, font-subsetting control, and cache bypass.

### Two backends

**Local Python API**

The plugin launches a Python bridge and imports PDFMathTranslate directly from a local source checkout. This backend supports PDF translation, selected-text translation, environment checks, and model discovery for OpenAI/OpenAI-compatible services.

**HTTP API**

The plugin can also submit translation jobs to a PDFMathTranslate HTTP service, poll job status, download mono/dual outputs, and cancel remote jobs.

The HTTP server is expected to expose the PDFMathTranslate `/v1/translate` job API. A typical server deployment may use Flask, Celery, and Redis.

### PDF++ integration

When PDF++ integration is enabled, the PDF selection menu can provide:

- **Translate selected text**
- **Quickly annotate selected text**
- **Send selected text to Claudian Q&A** (optional)
- **Import the last Claudian answer as an annotation**

Annotations are stored as Markdown beside the source PDF and can include precise PDF++ selection backlinks. Existing highlighted annotations can be located or removed without rewriting the PDF itself.

### Claudian bridge

The plugin can pass the selected PDF text, source file, page information, precise selection coordinates, and your question into Claudian.

The plugin itself does **not** automatically send the question. Claudian/Codex remains responsible for the model, conversation, provider, and tools. After you confirm the response, the final answer can be imported into the PDF annotation Markdown.

### Other integration

If **Notebook Navigator** is installed, PDF Math Translate can register translation actions in its file/folder menus.

## Requirements

- Obsidian Desktop `>= 1.5.0`
- Windows/macOS/Linux desktop environment supported by your Python/PDFMathTranslate setup
- For the local Python backend:
  - Python `>= 3.11, < 3.13`
  - A local **PDFMathTranslate 1.x** source checkout containing `pdf2zh/__init__.py`
  - Translation-service credentials/configuration as required by PDFMathTranslate
- Optional:
  - PDF++ for precise selection backlinks and PDF annotation workflow
  - Claudian (`realclaudian`) for PDF-grounded Q&A
  - Notebook Navigator for additional context-menu integration

## Installation

This repository contains the built Obsidian plugin files. Create the following directory inside your vault:

```text
<Vault>/.obsidian/plugins/pdf-math-translate/
```

Copy these files into it:

```text
main.js
manifest.json
styles.css
```

Then restart/reload Obsidian, open **Settings → Community plugins**, and enable **PDF Math Translate**.

## Local Python backend setup

### 1. Prepare PDFMathTranslate

Install or clone PDFMathTranslate separately. The configured source directory must contain:

```text
<PDFMathTranslate>/pdf2zh/__init__.py
```

Use Python 3.11 or 3.12 for PDFMathTranslate 1.x.

### 2. Configure the plugin

Open **Settings → PDF Math Translate** and set:

- **Connection mode**: Local Python API
- **Python executable**: the Python executable from the environment where PDFMathTranslate dependencies are installed
- **PDFMathTranslate source directory**: your local PDFMathTranslate source root
- **PDFMathTranslate config file**: optional configuration JSON containing translator credentials

Example Windows paths:

```text
Python executable:
C:\path\to\your\.venv\Scripts\python.exe

PDFMathTranslate source directory:
C:\path\to\PDFMathTranslate

Configuration file:
C:\path\to\pdf2zh-api-config.json
```

Do **not** copy another user's absolute paths. Configure paths for your own machine through the plugin settings UI.

### 3. Configure a translation service

A sanitized example is provided as:

```text
pdf2zh-api-config.example.json
```

Copy it to a private location, rename it if desired, and replace the placeholders with your own provider settings.

Example:

```json
{
  "translators": [
    {
      "name": "openailiked",
      "envs": {
        "OPENAILIKED_BASE_URL": "https://api.example.com/v1",
        "OPENAILIKED_API_KEY": "YOUR_API_KEY",
        "OPENAILIKED_MODEL": "gpt-4o-mini",
        "OPENAILIKED_STREAM": "false"
      }
    }
  ],
  "NOTO_FONT_PATH": "C:/path/to/SourceHanSerifCN-Regular.ttf"
}
```

For OpenAI/OpenAI-compatible endpoints, the base URL must end with `/v1`.

Never commit a real API key to Git.

## HTTP backend setup

Choose **HTTP API** in plugin settings and configure the service URL, for example:

```text
http://127.0.0.1:11008
```

The plugin uses endpoints equivalent to:

```text
POST   /v1/translate
GET    /v1/translate/<job-id>
DELETE /v1/translate/<job-id>
GET    /v1/translate/<job-id>/mono
GET    /v1/translate/<job-id>/dual
```

The exact server deployment is outside this plugin; configure the corresponding PDFMathTranslate HTTP service separately.

## Translation services

The current UI contains presets for multiple PDFMathTranslate services, including:

- OpenAI-compatible API (`openailiked`)
- OpenAI
- DeepSeek
- Gemini
- SiliconCloud
- ModelScope
- Qwen-MT
- Ollama
- Azure OpenAI
- Zhipu
- Grok
- Groq
- MiniMax
- DeepL / DeepLX
- Tencent
- Dify
- Google
- Bing

Actual availability and required environment variables depend on the installed PDFMathTranslate version and the selected provider.

For the local Python backend, model discovery is supported for OpenAI and OpenAI-compatible services when the provider exposes a compatible model-list endpoint.

## Commands

The plugin currently registers these Obsidian commands:

- Translate current PDF
- Choose and translate PDF
- Batch-select and translate PDFs
- Cancel current PDF translation and queued jobs
- Open selected-text translation sidebar
- Import the last Claudian answer as a PDF annotation
- Check PDFMathTranslate connection

It also adds ribbon actions for single-PDF translation, batch translation, and Claudian-answer import.

## Output and annotation behavior

Generated translation files use timestamped names to avoid overwriting existing outputs. The plugin can keep only the monolingual PDF or retain both mono and dual versions.

Translation notes can contain YAML metadata such as source PDF, output PDFs, backend, translation service, language direction, page range, PDFMathTranslate version, and generation time.

PDF annotations are Markdown files stored beside the source PDF. When PDF++ exposes precise selection coordinates, annotations link back to the exact selected region; otherwise the plugin falls back to page-level positioning.

## Security and privacy

This public package intentionally excludes Obsidian's runtime `data.json`, because it may contain:

- absolute local filesystem paths;
- vault paths;
- translation history/mappings;
- model/backend choices.

The repository also ignores the real `pdf2zh-api-config.json`, because it may contain API keys or private endpoints.

Before publishing a fork, search the repository for:

```text
sk-
API_KEY
TOKEN
SECRET
C:\Users\
/Users/
/home/
```

If a credential has ever been committed to Git history, deleting it from the latest commit is not sufficient. Revoke/rotate the credential and, if necessary, rewrite repository history.

## Files in this release

```text
main.js                           Built plugin bundle
manifest.json                    Obsidian plugin manifest
styles.css                       Plugin styles
pdf2zh-api-config.example.json   Sanitized provider configuration example
.gitignore                       Prevents local settings/secrets from being committed
README.md                        Documentation
```

`data.json` is deliberately not included.

## Development note

`main.js` is a generated bundle. If you maintain the plugin publicly, the preferred repository layout is to publish the original TypeScript/source files and build configuration in addition to the compiled release artifacts. This package only contains the files supplied for this release, so the original TypeScript sources are not reconstructed here.

## License

No license file was supplied with this release package. Before publishing the repository as open source, add an explicit license such as MIT, Apache-2.0, GPL, or another license appropriate for your project and its dependencies.
