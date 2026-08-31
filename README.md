# Lecture Slides to Obsidian

一个面向长期维护的 Agent Skill 项目：把 Canvas 中下载或本地已有的 PDF、PPT/PPTX、政策文档和论文，通过 MinerU 官方 CLI 整理成适合 Obsidian 阅读、连接和课堂补充的派生资料。

当前实现采用组合架构：MinerU 官方 CLI 负责提取，Obsidian 标准技能负责 Markdown/Canvas，本仓库只维护课程路由、normalization、目录边界和 QA。

## 设计目标

- 追求 semantic fidelity，而不是宣称 PDF → Markdown “无损”。
- 文字、层级、列表、公式和表格尽量结构化。
- 图表、复杂排版、手写标注和低置信度页面保留视觉兜底。
- 源 PDF/PPT/Office 文件始终留在 Obsidian vault 外部。
- 每份资料在 vault 中拥有独立文件夹：完整 Markdown、assets 和关系 Canvas。QA report 只存在于 staging，验证完成即删除。
- 用户在一个新学期首次提供课程名称时，只询问一次学期根目录并持久记录学期与课程映射。
- 后续通过课程代码、正式名称或已登记别名唯一匹配，自动归档到对应学期的课程子目录。
- 同一份技能内容兼容 Claude Code 和 Pi，并适合作为 cc-switch 自定义技能源。
- 除官方 CLI 访问 MinerU 服务外，不把课件发送到其他第三方服务。
- 课程文件内容解析只使用官方 `mineru-open-api extract` 精准模式，不下载本地模型，也不维护自定义 HTTP client。

## 仓库结构

```text
lecture-slides-to-obsidian/
├── README.md
├── AGENTS.md
├── scripts/
│   └── validate.sh
├── skills/
│   └── lecture-slides-to-obsidian/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       ├── config/
│       ├── examples/
│       ├── requirements/
│       ├── references/
│       ├── scripts/
│       ├── templates/
│       └── state/
└── tests/
    ├── cases/
    ├── fixtures/
    └── golden/
```

`skills/lecture-slides-to-obsidian/` 是可分发、可安装的完整技能目录。仓库级的 `tests/` 和 `scripts/` 只用于开发维护，不随技能运行。

## 课程路由模型

技能把真实注册表保存在自己的安装目录内：

```text
<installed-skill-directory>/state/course-registry.yaml
```

首次处理一门尚未登记的课程时：

1. 用户输入课程名称或课程代码。
2. 若没有 active semester，Agent 询问 Obsidian 内的目标根目录。
3. 学期 ID 与路径独立：路径能明确推断学期时提出建议；像 `Courses` 这样的通用路径会再询问一次学期 ID/label。
4. Agent 精确匹配课程目录；存在 `<course>-materials` 之类疑似候选时，先列出让用户选择，不能静默新建。
5. Agent 持久记录学期、课程、别名和派生目录规则；原件路径只保存在 skill-owned registry，且必须位于 vault 外。

默认分类契约为：

```text
<vault-root>/
└── <course-folder>/
    └── Lectures/
        └── <document-slug>/
            ├── <document-slug>.md       # 完整课件/文档
            ├── <document-slug>.canvas   # 关系画布
            └── assets/                  # MinerU 派生图片/表格/兜底页
```

原始 PDF/PPT 等不会复制、移动、symlink、embed 或作为 Canvas file node 放进 vault。Canvas 只连接完整 Markdown 的章节、关键概念和 `assets/` 中的派生文件。

关系 Canvas 参考 [phd-deepread-workflow](https://github.com/heleninsights-dot/phd-deepread-workflow/tree/main) 的“中心文档 + 观点/证据/问题节点 + 有向边 + verifier”模式，但改为动态支持 lecture、policy 和 paper，不采用它的本地 PDF parser 或固定论文模板。

注册表是 skill-owned 本机状态，不应提交 GitHub。正常删除整个技能目录时，注册表会一起删除，不会另行残留在 `~/.config`。完整匹配与安全规则见 `references/course-routing.md`。

cc-switch 卸载时可能创建自己的 skill backup。若要求卸载备份中也不保留课程路径，应先运行技能内的 `scripts/purge-state.sh --confirm`，再从 cc-switch 卸载技能。

目录整体替换式更新必须保留并原位恢复 `state/`。在自动迁移实现前，更新器不应把 package 内容覆盖到一个已有运行态目录而忽略其中的 registry。

## 解析策略与前置要求

PDF 会上传到 MinerU 官方服务进行解析。转换前必须：

- 能发现并加载 `obsidian-markdown`，用于 Obsidian properties、wikilinks、embeds、callouts 和 Markdown 语法。
- 能发现并加载 `json-canvas`，用于关系画布生成与 JSON Canvas 校验。
- 已安装官方 `mineru-open-api` CLI，并能访问 MinerU Precision API。
- 本机具有支持 `aes-256-cbc` 的 OpenSSL。
- 当前自动 credential backend 为 macOS Keychain（`security` CLI）；其他平台会明确失败，不会退回明文或同目录 key 文件。

当前 adapter 已使用官方 CLI `v0.5.9` 验证命令/参数兼容性。

安装 CLI（二选一）：

```bash
npm install -g mineru-open-api
# 或
uv tool install mineru-open-api
```

API token 加密保存为：

```text
<installed-skill-directory>/state/mineru-api-token.enc.json
```

首次配置：

```bash
skills/lecture-slides-to-obsidian/scripts/token-store.py set
```

若 Agent 已从聊天框收到 token，只能通过 stdin 调用 `set --token-stdin`，不能放进命令参数。脚本自动生成随机 wrapping key 并写入 macOS Keychain；后续转换直接自动解锁，不再询问 token、额外口令或重复同意。CLI 没有输出明文 token 的命令。

密文采用 AES-256-CBC + PBKDF2-HMAC-SHA256（600,000 iterations），并用独立的 Encrypt-then-HMAC-SHA256 做完整性校验。token 文件权限为 `0600`，state 目录写入时设为 `0700`。`purge-state.sh --confirm` 会同时删除密文与对应 Keychain 项。

提取流程：

1. `mineru-cli-adapter.py` 从 Keychain 自动解锁 token。
2. Token 只通过子进程 `MINERU_TOKEN` 注入官方 CLI。
3. 官方 CLI 执行 `extract -f md,json -o <staging>/`，负责上传、轮询、下载和 assets。
4. Adapter 把 CLI legacy content-list JSON 按 `page_idx` 转成 page-group compatibility JSON。
5. `reconstruct-note.py`、`obsidian-markdown` 和 `json-canvas` 继续完成派生文档。

支持三个 conversion profile：`lecture-notes`、`policy-document`、`paper`。不是 slides 的资料不会被拒绝，而会在写入 vault 前要求确认合适的 profile。

机器可读声明位于 `requirements/skills.yaml`、`requirements/tools.yaml` 和 `requirements/services.yaml`，组合契约位于 `references/mineru-cli.md`。

## 安装与加载

### Claude Code

开发期推荐软链接，改动可立即反映：

```bash
ln -s /absolute/path/to/lecture-slides-to-obsidian/skills/lecture-slides-to-obsidian \
  ~/.claude/skills/lecture-slides-to-obsidian
```

Claude Code 中可让模型按描述自动加载，或显式运行：

```text
/lecture-slides-to-obsidian
```

### Pi

Pi 可以直接从共享目录发现技能：

```bash
ln -s /absolute/path/to/lecture-slides-to-obsidian/skills/lecture-slides-to-obsidian \
  ~/.agents/skills/lecture-slides-to-obsidian
```

也可以在 Pi 的 settings 中把本仓库的 `skills` 目录加入技能路径。显式调用名为：

```text
/skill:lecture-slides-to-obsidian
```

### cc-switch

上传 GitHub 后，在 cc-switch 的自定义仓库中填写仓库 Owner、Name、Branch，并把 **Subdirectory** 设为 `skills`。仓库不要在 cc-switch 管理的安装目录里直接开发；让 cc-switch 负责复制或链接已发布版本。

## 本地验证

技能提供四个 Agent-facing automation entry：

```text
preflight.py          分段收集/验证 vault、course、profile、language、OCR、helper skills、token state
reconstruct-note.py  content_list_v2.json → 完整 profile-aware Markdown + normalization context
build-canvas.py       note headings/assets → 完整 vault-relative JSON Canvas
fill-report.py        QA context JSON → staging 临时 report
```

完整处理完成后：

```bash
./scripts/validate.sh
```

仓库验证检查技能规范与模板。实际输出还必须运行：

```bash
python3 skills/lecture-slides-to-obsidian/scripts/validate-output.py \
  <document-folder> --vault-root <vault-root> \
  --report <staging>/conversion-report.md --delete-report-on-success
```

它验证 source-original exclusion、frontmatter、H1/page markers、wikilinks/assets、Canvas IDs/edges/paths/non-overlap，以及 staging 临时报告；成功后删除该报告。

## 测试素材政策

- `tests/fixtures/synthetic/`：可提交自行生成、可再分发的小型 PDF。
- `tests/fixtures/public/`：仅提交许可证和来源明确的公开材料，并附元数据。
- `tests/fixtures/private/`：本机私有课件，已被 Git 忽略，不得提交。
- `tests/golden/`：只保存由可再分发素材生成的期望输出。
- 真实课程 PDF、学生信息、Canvas 会话数据和登录凭据不得进入仓库。

详细规则见 `tests/fixtures/README.md`。

## 后续阶段

1. 用代表性课件建立合成/公开基准集。
2. 实现技能内课程注册表的原子读写、唯一匹配和目录路由测试。
3. 使用私有测试课件在官方 CLI v0.5.9 上完成一次不进入公共 fixture 的端到端试运行。
4. 扩充 CLI 输出、Canvas 和 profile normalization 回归样例。
5. 在真实课前工作流中小范围试用，再依据失败样例修订技能。

## 暂未决定

- 官方 CLI 的长期最低兼容版本与升级策略。
- 许可证和发布策略。

这些内容应在有实现和测试证据后再确定。
