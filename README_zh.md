# PDF Math Translate for Obsidian

![Obsidian Desktop](https://img.shields.io/badge/Obsidian-Desktop-7C3AED?logo=obsidian&logoColor=white)
![Version](https://img.shields.io/badge/version-0.7.2-blue)
![License](https://img.shields.io/badge/license-AGPL--3.0--only-green)

**主文档**：[README.md](README.md)

在 Obsidian 桌面版中调用 [PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate)，把 Vault 内的科技论文 PDF 翻译为单语译文，或同时输出单语译文和双语对照 PDF；翻译说明 Markdown 可选生成且默认关闭。

> An Obsidian desktop plugin for scientific PDF translation, Claudian-powered selection Q&A, and PDF++-based annotations.

当前版本：`0.7.2`

## 功能

- 从当前 PDF、命令面板、左侧工具栏或 PDF 文件右键菜单发起翻译；
- 每次任务可通过下拉列表指定页码范围、源语言、目标语言、翻译服务和模型；
- 支持资源管理器式文件树多选 PDF，或右键文件夹顺序批量翻译，显示总进度和逐文件结果；
- 同时兼容 Obsidian 原生文件列表和 Notebook Navigator 的文件夹/PDF右键菜单；
- 批量选择器自动排除插件生成的单语/双语 PDF，并检测原文是否已有译文；已有译文会标记、提示并跳过；
- 本地模式直接调用 `pdf2zh.translate()` Python API；
- HTTP 模式调用项目已有的 `/v1/translate`、状态查询、下载和取消接口；
- 显示翻译进度并支持取消；点击窗口外部或按 Esc 会缩成可实时查看进度的右下角小窗，可随时展开，任务在后台继续；
- 翻译运行期间仍可从进度窗、迷你进度窗、工具栏、命令或右键菜单新增任务；新任务保留各自设置并进入顺序等待队列，不并发调用翻译服务；
- 可在每次任务前选择"仅输出单语"或"输出单语、双语"，并写入原 PDF 所在文件夹；
- 翻译说明 Markdown 可单独开启，新安装默认不生成；
- 每次翻译使用带毫秒的任务时间命名，不覆盖旧结果；
- 在生成的笔记中嵌入双语 PDF，并记录来源、翻译方向、服务和核心版本；
- 可选读取一篇 Vault Markdown 笔记作为 PDFMathTranslate 自定义提示词；
- OpenAI 和 OpenAI 兼容中转站可自动检测文本模型，并在每次翻译前提供模型下拉列表；
- 设置页提供不执行翻译的连接检查。
- 接入 PDF++ 自定义右键菜单，划词后直接调用当前 PDFMathTranslate 服务翻译短文本；
- PDF++ 划词后可输入问题，并把"问题 + 精确选区 + 来源页码"填入 Claudian/Codex；
- Claudian 负责模型切换、连续对话和 agent 工具，本插件不再维护第二套聊天后端；
- 回答完成后，可从右键菜单、命令面板或左侧高亮图标快速导入批注；
- 一键生成带 PDF++ 精确选区反链的 Markdown 批注，或把译文一起保存为双语批注；
- AI 批注同时保存问题、回答、实际模型和精确选区反链；
- 批注 Markdown 与原 PDF 同目录保存，每篇论文维护一个稳定的批注笔记，且不直接改写 PDF 文件。
- 划词译文显示在右侧栏；大段文字自动分段串行翻译，并对 429 限流自动退避重试；
- 划词翻译右侧栏可切换检测到的模型或输入自定义模型 ID，并对当前选区重新翻译；
- 单击 PDF++ 高亮可直接定位到对应批注，右键可删除这一处批注；高亮仍不会阻止再次拖选文字。
- 完成全文翻译后自动建立原文/译文映射；在原文或译文页面双击，可跳到另一篇 PDF 的同页、相对区域并显示短暂定位标记。

该插件仅支持 Obsidian 桌面版，因为本地模式需要启动 Python，HTTP 模式也需要访问桌面文件系统来保存 PDF。

## 环境要求

| 组件 | 要求 |
| --- | --- |
| Obsidian | 桌面版 `1.5.0` 或更高 |
| PDFMathTranslate | 需单独准备一份本地源码；当前测试基线为 `1.9.11` |
| Python | 本地 API 模式需要 `3.11` 或 `3.12`，建议通过本仓库的 `scripts/setup-python.ps1` 创建专用 `.venv` |
| PDF++ | 可选；用于划词翻译和精确选区批注 |
| Notebook Navigator | 可选；用于扩展右键菜单入口 |

## 架构

```text
Obsidian 命令 / 文件菜单 / PDF++ 选区菜单 / 任务窗口
                           │
                           ▼
              Vault 输入、输出与笔记管理
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
   本地 Python API    PDFMathTranslate HTTP API   PDF++ 精确选区反链
 PDF/短文本翻译/Claudian问答  PDF 全文翻译          Markdown 快速批注
           │               │
           └───────┬───────┘
                   ▼
 PDFMathTranslate：版面识别、公式保护、文本翻译、PDF 重建
```

插件没有复制或改写 PDFMathTranslate 的翻译算法。Python 桥接程序（`bridge/pdf2zh_bridge.py`）只负责把 Obsidian 的 JSON 请求转换为项目公开的 `translate()` 参数，并把进度和结果转换回 JSON 事件。

桥接代码已从 `main.js` 中分离，作为独立文件存放于 `bridge/` 目录。插件通过设置中的 `configFile` 绝对路径定位桥接文件（`path.dirname(configFile) + "/bridge/pdf2zh_bridge.py"`），因此安装插件时需确保 `bridge/` 目录与插件其他文件在同一目录下。

## 安装

### 从 GitHub Releases 安装

1. 在项目 Releases 页面下载 `pdf-math-translate-x.y.z.zip`；
2. 解压后将 `main.js`、`manifest.json`、`styles.css` 和 `bridge/` 目录复制到 `<Vault>/.obsidian/plugins/pdf-math-translate/`；
3. 在 Obsidian 的"设置 → 第三方插件"中重新加载并启用 **PDF Math Translate**。

当前版本尚未收录到 Obsidian 官方社区插件库，因此需要手动安装。

### 从源码构建

需要 Node.js 和 pnpm：

```powershell
pnpm install
pnpm run build
pnpm test
```

构建成功后，Obsidian 所需的文件是：

- `main.js`
- `manifest.json`
- `styles.css`
- `bridge/pdf2zh_bridge.py`

### 安装构建产物

可以手动把上述文件复制到：

```text
<Vault>/.obsidian/plugins/pdf-math-translate/
```

也可以使用仓库提供的安装脚本：

```powershell
.\scripts\install-plugin.ps1 -VaultPath "C:\路径\到\你的 Vault"
```

然后打开 Obsidian 的"设置 → 第三方插件"，刷新插件列表并启用 **PDF Math Translate**。

建议先在测试 Vault 中验证，不要直接把开发版本放入唯一的主 Vault。

## 配置

### 本地 Python API（推荐）

这一模式**需要两样东西**，而且两者不是同一个目录：

1. **一个 Python 3.11 / 3.12 虚拟环境**，供插件实际调用；
2. **一份本地 PDFMathTranslate 源码目录**，供桥接脚本导入 `pdf2zh`。

最容易让人混淆的点是：**虚拟环境建在本插件仓库里，源码目录则是你单独下载的 PDFMathTranslate 仓库**。插件设置里这两项都要填。

先准备 PDFMathTranslate 源码，例如：

```text
D:\src\PDFMathTranslate
```

然后在本插件仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-python.ps1 `
  -ProjectPath "D:\src\PDFMathTranslate" `
  -Python "C:\Python312\python.exe"
```

如果脚本是从网上下载的，先执行一次：

```powershell
Unblock-File .\scripts\setup-python.ps1
```

这个脚本会做以下事情：

- 检查你指定的 Python 是否为 `3.11` 或 `3.12`；
- 在**当前插件项目目录**创建或更新 `.venv`；
- 在这个 `.venv` 里安装你提供的 **PDFMathTranslate 本地源码**；
- 额外固定当前已验证的 `peewee 3.18.2` 和 `tencentcloud-sdk-python-tmt 3.1.121`，避开已知的 Windows 兼容问题。

运行完成后，实际应填写的是：

- **Python 可执行文件**：本插件目录下的 `.venv\Scripts\python.exe`
- **PDFMathTranslate 源码目录**：你自己的上游源码目录，例如 `D:\src\PDFMathTranslate`

在 Obsidian 中按下面顺序配置：

1. 打开"设置 → PDF Math Translate"；
2. 连接方式选择"本地 Python API"；
3. 把"Python 可执行文件"设为脚本输出的 `.venv\Scripts\python.exe`；
4. 把"PDFMathTranslate 源码目录"设为你的 `D:\src\PDFMathTranslate`；
5. 点击"检查连接"；
6. 检查通过后再翻译 PDF。

如果"检查连接"失败，优先核对这三件事：

- 你填的是 **本插件的 `.venv` Python**，不是系统 Python；
- 你填的是 **PDFMathTranslate 仓库根目录**，并且里面存在 `pdf2zh\__init__.py`；
- 该 `.venv` 确实是用同一个 `-ProjectPath` 跑 `setup-python.ps1` 建出来的。

翻译服务的密钥继续由 PDFMathTranslate 管理，可使用它的 `~/.config/PDFMathTranslate/config.json`、自定义配置文件或系统环境变量。本插件不保存 API 密钥。

当服务选择"OpenAI"或"OpenAI 兼容接口"时，插件会在打开翻译窗口时调用配置地址的 `/v1/models`，并将返回的文本模型加入下拉列表。设置页和翻译窗口都可以手动刷新。自动检测只读取现有配置，不会改写配置文件；如果中转站没有实现模型端点，仍可手动输入准确模型 ID。

### HTTP API（可选）

HTTP 模式适合已经部署 PDFMathTranslate 服务的情况。按照上游 `docs/APIS.md`，服务端需要 Flask、Celery worker 和 Redis，例如：

```powershell
pip install "pdf2zh[backend]"
pdf2zh --flask
pdf2zh --celery worker
```

插件设置中选择"HTTP API"，填写服务地址（默认 `http://127.0.0.1:11008`）并检查连接。连接检查只能证明 Flask 可访问；Redis 与 Celery worker 会在提交实际任务时被验证。

注意：当前上游 HTTP API 没有接收 `compatible` 参数对应的文件路径处理流程，因此插件的"兼容模式"只对本地 Python API 生效。

## 使用

打开一个 Vault 内的 PDF，然后任选一种方式：

- 点击左侧工具栏的语言图标；
- 在命令面板运行"PDF Math Translate: 翻译当前 PDF"；
- 在文件列表中右键 PDF，选择"使用 PDF Math Translate 翻译"；
- 当前不是 PDF 时，运行"选择并翻译 PDF"。
- 运行"批量选择并翻译 PDF"，在可展开的 Vault 文件树中勾选文件或整层文件夹，再使用统一设置顺序处理；
- 在文件列表中右键文件夹，选择"批量翻译此文件夹中的 PDF"；插件会先显示"待翻译 / 总数"，开始前列出并跳过已有译文。

页码输入使用人类习惯的从 1 开始编号，例如 `1-3,5`。留空翻译全文。

### PDF++ 划词翻译、Claudian 问答与快速批注

1. 安装并启用 PDF++，在 PDF++ 设置中启用自定义 PDF 右键菜单；
2. 在"设置 → PDF Math Translate"中保持"启用 PDF++ 集成"开启；
3. 在 PDF 中选中文字并右键：
   - 选择"翻译所选文本"，在右侧栏查看译文、复制译文或保存为双语批注；
   - 选择"发送所选文本到 Claudian 问答"，输入问题；插件只填入 Claudian，不自动发送；
   - 在 Claudian 中确认 provider、模型和问题后发送，可继续追问；
   - 回答完成后，选择"导入 Claudian 最后回答为批注"，或使用命令面板/左侧高亮图标；
   - 在右侧栏选择另一个模型，再点击"用此模型重新翻译"，可对比同一选区的不同模型结果；
   - 选择"快速批注所选文本"，立即把原文和精确定位链接写入批注笔记；
   - 单击已有高亮，直接打开批注笔记并定位到对应条目；
   - 右键已有高亮，可选择"打开对应批注"或"删除此处批注"。删除后 15 秒内可点击通知中的"撤销删除"；
4. 批注笔记保存在原 PDF 的同一文件夹。一篇论文一个文件夹时直接使用"批注.md"；同目录有多篇 PDF 时自动加简短论文编号，例如"DAC2026-900 - 批注.md"。

划词翻译仍使用本地 Python API；问答由 Claudian 的 Codex provider 负责。插件会记录提问时的 Claudian 标签页、会话和消息数量，只导入本次提问之后的新 assistant 回答，避免把旧会话答案误写到当前选区。超过 2500 字符的翻译选区会按自然边界拆分并串行翻译；问答选区上限为 50000 字符。

快速批注采用 Obsidian 原生的 `#page=…&selection=…` 深链接；PDF++ 会把反链显示为选区高亮。插件按点击位置匹配同一 PDF、页码和精确选区：单击只负责打开批注，删除必须从高亮右键菜单明确选择。高亮层仍忽略拖拽事件，因此重新划词不会误打开批注。若 PDF++ 未返回选区坐标，插件会明确提示并退化为页级链接；页级链接没有选区高亮，需要在批注笔记中管理。

默认输出结构（仅输出单语，不生成翻译说明 Markdown）：

```text
论文目录/
├─ 论文名.pdf
├─ 批注.md
└─ 论文标题 - 单语译文 - 20260813-153012-123.pdf
```

选择"输出单语、双语"时会额外写入双语 PDF；开启"生成翻译说明 Markdown"后，目录中会额外出现 `翻译说明 - 时间戳.md`。翻译说明不是 PDFMathTranslate 的必需输出。

单语译文、双语译文和翻译说明始终使用原 PDF 标题作为前缀，例如 `论文标题 - 单语译文 - 时间戳.pdf`。标题过长时会安全截短并增加校验后缀；批注文件仍沿用单论文文件夹中的简短名称。

翻译过程使用系统临时目录；成功后才把产物写入原论文目录，临时文件会自动清理。已写入 Vault 的结果不会被后续任务覆盖。

翻译开始后，可点击完整进度窗或右下角迷你进度窗中的"新增任务"，也可继续使用左侧批量翻译图标、命令面板和文件右键菜单。新增批次会显示"已加入翻译队列"，当前文件完成后自动继续。执行"取消当前 PDF 翻译及等待队列"会同时终止当前文件并移除尚未开始的任务。

原文/译文映射保存在插件数据中，新生成的单语、双语译文会与来源 PDF 精确配对。升级前已经由本插件生成、且仍符合时间戳命名规则的同目录译文，也可以按文件名自动识别。双击跳转使用"同页码 + 页内相对位置"，适合 PDFMathTranslate 保持页面结构的输出；若译文发生明显重排，它不是语义级段落对齐。

## API 选择说明

PDFMathTranslate 上游的英文 `README.md` 和 `docs/APIS.md` 记录了 Python 与 HTTP API，代码也从 `pdf2zh.__init__` 导出了 `translate`、`translate_stream`。与此同时，`docs/README_zh-CN.md` 曾存在"API 暂时弃用"的文字，文档状态并不完全一致。

本插件采用以下兼容策略：

- 本地集成以实际存在的公开 Python API 为主；
- HTTP 集成严格使用上游已实现的端点；
- 所有调用集中在独立适配器和小型桥接层中；
- 如果将来上游 API 变化，只需替换适配器，不影响 Vault 文件和交互层。

## 隐私与外部访问

- 本地 Python 模式会读取选中的 Vault PDF，并让 PDFMathTranslate 按所选翻译服务访问网络；
- Claudian 问答会在你确认发送后，把问题、选中文本、PDF 路径和页码发送到其 Codex provider；数据保留策略取决于配置的中转站；
- HTTP 模式会把选中的 PDF 上传到你配置的服务器；
- 若配置自定义提示词笔记，其全文会随翻译请求交给所选翻译服务；
- 插件没有遥测、广告或额外账户系统；
- 插件不会把密钥写入 `data.json`。

## 开发验证

```powershell
# TypeScript 类型检查与生产构建
pnpm run build

# TypeScript 纯逻辑测试
pnpm run test:ts

# Python 桥接测试
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_bridge.py

# Python API 只读诊断（不会翻译）
'{"action":"doctor","projectPath":"D:\\src\\PDFMathTranslate","configFile":""}' |
  .\.venv\Scripts\python.exe -X utf8 .\bridge\pdf2zh_bridge.py

# 可选真实一页端到端测试；会访问 Google 翻译并按需下载上游模型/字体
$env:PDF2ZH_TEST_PROJECT = "D:\src\PDFMathTranslate"
$env:PDF2ZH_TEST_PYTHON = ".\.venv\Scripts\python.exe"
pnpm run test:e2e
```

真实端到端翻译会调用外部翻译服务并可能下载字体/模型，因此不属于默认自动测试；应在测试 Vault 中用一份小 PDF、页码 `1` 完成人工验收。

## 仓库结构

```text
src/                    Obsidian 插件、交互和适配器（TypeScript 源码）
bridge/                 PDFMathTranslate Python 桥接（独立文件）
scripts/                环境准备与安装脚本
tests/                  TypeScript、Python 与可选端到端测试
manifest.json           Obsidian 插件元数据
styles.css              插件样式
main.js                 构建产物（Obsidian 插件入口）
```

## 已知限制

- 只支持 Obsidian 桌面版；
- 划词翻译只支持本地 Python API；
- Claudian 桥接依赖 `realclaudian` 当前提供的 `appendToActiveInput()` 与活动标签页消息状态；升级 Claudian 后应重新做一次交互验收；
- 当前问答以用户选区为主要上下文，尚未自动检索整篇 PDF；需要全文资料时可在 Claudian 中继续使用 agent 工具；
- PDF++ 无法返回选区坐标时，批注会退化为页级链接，不会生成精确高亮；
- 原文/译文双击联动按页码和页内相对位置导航，不是逐句语义对齐；源 PDF 或译文被手动改名、移动后，旧映射可能需要重新翻译或恢复文件位置；
- PDFMathTranslate 的配置格式和 API 可能在上游版本中变化，升级前请先在测试 Vault 验证。

## 贡献

欢迎提交 Issue 和 Pull Request。请说明使用场景、环境版本、可复现步骤和已执行的测试，并在公开日志前删除 API 密钥、私有 PDF 与 Vault 路径等敏感信息。

## 致谢

- [PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate) 及其贡献者；
- [Obsidian](https://obsidian.md/)；
- [PDF++](https://github.com/RyotaUshio/obsidian-pdf-plus)；
- [Notebook Navigator](https://github.com/johansan/notebook-navigator)。

## 许可证

本插件采用 [GNU AGPL-3.0-only](LICENSE)，以便与 PDFMathTranslate 的 AGPL-3.0 许可保持一致。PDFMathTranslate 本身由其原作者和贡献者维护。
