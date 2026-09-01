# Lecture Slides to Obsidian

一个面向长期维护的 Agent Skill 项目：把 Canvas 中下载或本地已有的 PDF、PPT/PPTX、政策文档和论文，通过 MinerU 官方 CLI 整理成适合 Obsidian 阅读、连接和课堂补充的派生资料。

当前实现采用五技能组合：MinerU官方CLI与主技能负责课前转换，可选layout refiner整理每张slide内部版式，Canvas子技能负责视觉产物，live-notes技能负责课堂即时思考，ASR enricher负责课后教师上下文增量。

## 设计目标

- 追求 semantic fidelity，而不是宣称 PDF → Markdown “无损”。
- 文字、层级、列表、公式和表格尽量结构化。
- 图表、复杂排版、手写标注和低置信度页面保留视觉兜底。
- 可选使用MiniMax-M3等多模态模型逐页对照原PDF，只整理每个`source-page`边界内部的版式；默认关闭，内容与顺序守恒验证失败时保留MinerU原稿。
- 最终视觉资产统一命名为 `page-PPP-kind-NN.ext`，例如 `page-004-figure-01.png`。
- 源 PDF/PPT/Office 文件始终留在 Obsidian vault 外部。
- 每份资料在 vault 中拥有独立文件夹：完整 Markdown、assets 和知识回忆 Canvas。report、snapshot、recall model、aesthetic/render checks 只存在于系统 tmp 或技能安装目录的 `tmp/`，验证完成即删除；不会在 vault 中创建任何点号开头的工作目录。
- Canvas 不是目录图：它提炼中心问题、学习模块、概念依赖/因果/对比链、边界条件和主动回忆问题，并让每个概念回链到完整课件。
- Canvas 卡片高度通过本机 Obsidian DOM 两遍测量，不使用截图判断；最终阅读视图固定为 1:1、16px 字体，高于当前侧栏的 13px。
- 课堂即时想法通过独立技能插入对应章节，并与课件转录正文分层保存。
- 课后教师ASR上下文通过独立技能做增量比较，只补充老师新增的信息，不重复课件内容。
- 用户在一个新学期首次提供课程名称时，只询问一次学期根目录并持久记录学期与课程映射。
- 后续通过课程代码、正式名称或已登记别名唯一匹配，自动归档到对应学期的课程子目录。
- 这是通用、运行环境无关的 Agent Skill；推荐通过 cc-switch 统一安装、更新和切换。
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
│   ├── lecture-slides-to-obsidian/
│   │   ├── SKILL.md
│   │   └── ...课程解析、路由、Markdown 与最终 QA
│   ├── obsidian-canvas-designer/
│   │   └── ...Canvas 设计、Axton 美术规则、静态评分与 DOM QA
│   ├── obsidian-live-lecture-notes/
│   │   └── ...课堂即时想法路由与非破坏式插入
│   ├── slide-layout-refiner/
│   │   └── ...可选多模态逐页版式整理与内容守恒验证
│   └── lecture-asr-enricher/
│       └── ...课后ASR增量提取、证据计划与老师补充
└── tests/
    ├── cases/
    ├── fixtures/
    └── golden/
```

`skills/` 是可由 cc-switch 一起管理的技能包；其中五个目录均可独立发现和调用。仓库级 `tests/` 与 `scripts/` 只用于开发维护。

## 课程路由模型

请求在任何 preflight 之前分流：外部源文件需要提取时运行完整流程；已有 normalized page groups 只缺 Markdown 时只运行 reconstruction；完整 Markdown 只缺 Canvas 时直接调用 `obsidian-canvas-designer`，不加载 MinerU、token 或课程路由。

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
            ├── <document-slug>.canvas   # 一分钟知识回忆地图
            └── assets/                  # MinerU 派生图片/表格/兜底页
```

原始 PDF/PPT 等不会复制、移动、symlink、embed 或作为 Canvas file node 放进 vault。Canvas 只连接完整 Markdown、经语义建模的关键概念，以及最多六个真正有助于记忆的派生视觉素材。

知识回忆 Canvas 参考 [phd-deepread-workflow](https://github.com/heleninsights-dot/phd-deepread-workflow/tree/main) 的批判思考节点，并强制吸收 [Axton Obsidian Canvas Creator](https://github.com/axtonliu/axton-obsidian-visual-skills/tree/1265976d9746a84858b4b7b42fb86a215aa93de9/obsidian-canvas-creator) 的布局选择、留白、视觉重心和边线优化原则；字符高度估算则由本机 DOM 实测替代。

注册表是 skill-owned 本机状态，不应提交 GitHub。正常删除整个技能目录时，注册表会一起删除，不会另行残留在 `~/.config`。完整匹配与安全规则见 `references/course-routing.md`。

cc-switch 卸载时可能创建自己的 skill backup。若要求卸载备份中也不保留课程路径，应先运行技能内的 `scripts/purge-state.sh --confirm`，再从 cc-switch 卸载技能。

目录整体替换式更新必须保留并原位恢复 `state/`。在自动迁移实现前，更新器不应把 package 内容覆盖到一个已有运行态目录而忽略其中的 registry。

## 课堂中与课后补充

课堂中直接调用 `obsidian-live-lecture-notes`。它只绑定一次当前打开的 course-material note；每条聊天想法会被路由到最匹配的现有H2/H3，以稳定ID callout追加。无法可靠归位时暂存到 `## In-class notes`，避免打断课堂。

课后已有教师ASR Markdown时调用 `lecture-asr-enricher`。它比较ASR与现有课件笔记，只保留老师新增的解释、例子、强调、纠正、边界、Q&A和有效课程安排；低置信度内容留在review plan，不写入笔记。教师补充复用同一插入协议，因此不会覆盖课件正文或学生课堂思考。

## 解析策略与前置要求

PDF 会上传到 MinerU 官方服务进行解析。转换前必须：

- 能发现并加载 `obsidian-markdown`，用于 Obsidian properties、wikilinks、embeds、callouts 和 Markdown 语法。
- 能发现并加载 `obsidian-canvas-designer`；其绘图 subagent 会加载 `json-canvas` 和 `obsidian-cli` 完成格式、美术与真实 DOM 检查。
- 主技能加载 `obsidian-cli` 处理 vault-native 操作和最终交付验证。
- 当前只支持已测量的 MacBook Pro 14 / Composer 主题 / Obsidian 1.13.7 环境，不宣称其他机器兼容。
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
5. Adapter 按页码/类型/序号重命名图片，输出 `asset-map.json` 和 `normalized-assets/`。
6. `reconstruct-note.py`生成基础MinerU Markdown与不可变source-page markers。
7. 可选的`slide-layout-refiner`让MiniMax-M3直接查看原PDF，并直接覆盖最终Markdown，但只能修改相邻markers之间的结构。目标是完整保存信息和提高可读性，不是像素级还原；会将`\-`/装饰符号整理为真实列表，并让每级子列表使用两个普通空格加`- `表达层级，禁止Tab缩进。marker行逐字节锁定，文本token顺序和每页asset集合必须完全守恒；验证失败时自动从tmp快照恢复。
8. 主 Agent 通读最终采用的Markdown并建立覆盖所有H2的临时recall model。
9. 独立`obsidian-canvas-designer`子技能由subagent执行布局、美术评分、DOM实测和重排；主Agent只消费Canvas与PASS/FAIL证据。

支持三个 conversion profile：`lecture-notes`、`policy-document`、`paper`。不是 slides 的资料不会被拒绝，而会在写入 vault 前要求确认合适的 profile。

机器可读声明位于 `requirements/skills.yaml`、`requirements/tools.yaml` 和 `requirements/services.yaml`，组合契约位于 `references/mineru-cli.md`。

## 安装与加载

推荐使用 **cc-switch** 管理。在自定义仓库中填写仓库 Owner、Name、Branch，并把 **Subdirectory** 设为 `skills`。让 cc-switch 负责安装、更新、切换和恢复运行态 `state/`；不要直接在它管理的安装目录中开发。

若不使用 cc-switch，把 `skills/` 下五个技能目录一起复制或链接到当前运行环境支持的技能目录。具体目录位置和调用语法由运行环境决定。

如果完整 Markdown 已存在而只缺 Canvas，直接调用 `obsidian-canvas-designer`。这一入口不加载 MinerU、token、提取、课程路由或 conversion report。

如果一次需要为两个或更多文件生成 Canvas，主 Agent 必须创建“一文件一任务”的 Canvas subagents。semantic authoring、初版布局和 aesthetic QA 可按可用容量并行；共享的本机 Obsidian DOM measure/reflow/check 必须单通道串行，避免不同 Canvas 互相抢 active renderer。批计划由 `plan-canvas-batch.py` 生成，单文件失败按文件报告，不得把整批笼统标成 PASS/FAIL。

## 本地验证

主技能提供三个流程入口，Canvas子技能提供四个入口，课堂补充技能各提供一个确定性入口，可选layout refiner提供一个守恒validator：

```text
preflight.py          分段收集/验证 vault、course、profile、language、OCR、helper skills、token state
reconstruct-note.py  content_list_v2.json → 完整 profile-aware Markdown + normalization context
fill-report.py        QA context JSON → staging 临时 report

obsidian-canvas-designer/build-canvas.py          recall model → Canvas
obsidian-canvas-designer/recall-skeleton.py       H2/page inventory → authoring draft
obsidian-canvas-designer/canvas-aesthetic-qa.py   Axton-informed static visual score
obsidian-canvas-designer/canvas-render-qa.py      本机 DOM → 实测高度、字体与 PASS/FAIL

obsidian-live-lecture-notes/apply-note-patches.py  学生/老师callout → Obsidian原生幂等插入
lecture-asr-enricher/validate-enrichment-plan.py   ASR增量计划 → 可应用teacher patch
slide-layout-refiner/validate-layout-refinement.py  原位覆盖结果 → 逐页内容/asset守恒PASS或自动回滚
```

Canvas 必须执行本机两遍渲染：

```bash
python3 skills/obsidian-canvas-designer/scripts/recall-skeleton.py \
  --note <document.md> --profile <profile> \
  --output <staging>/recall-model.json

# Agent completes the authoring draft before this step.
python3 skills/obsidian-canvas-designer/scripts/build-canvas.py \
  --note <document.md> --vault-root <vault-root> --profile <profile> \
  --model <staging>/recall-model.json --output <document.canvas>

python3 skills/obsidian-canvas-designer/scripts/canvas-aesthetic-qa.py \
  --canvas <document.canvas>

python3 skills/obsidian-canvas-designer/scripts/canvas-render-qa.py measure \
  --canvas <document.canvas> --vault-root <vault-root> \
  --output <staging>/canvas-render-metrics.json

python3 skills/obsidian-canvas-designer/scripts/build-canvas.py \
  --note <document.md> --vault-root <vault-root> --profile <profile> \
  --model <staging>/recall-model.json \
  --render-metrics <staging>/canvas-render-metrics.json \
  --output <document.canvas> --overwrite

python3 skills/obsidian-canvas-designer/scripts/canvas-aesthetic-qa.py \
  --canvas <document.canvas> \
  --output <staging>/canvas-aesthetic-check.json

python3 skills/obsidian-canvas-designer/scripts/canvas-render-qa.py check \
  --canvas <document.canvas> --vault-root <vault-root> \
  --output <staging>/canvas-render-check.json
```

这一流程读取 Obsidian 实际 DOM 高度并把阅读视图留在 1:1；不会生成或分析截图。

完整处理完成后：

```bash
./scripts/validate.sh
```

仓库验证检查技能规范与模板。实际输出还必须运行：

```bash
python3 skills/lecture-slides-to-obsidian/scripts/validate-output.py \
  <document-folder> --vault-root <vault-root> \
  --report <staging>/conversion-report.md \
  --recall-model <staging>/recall-model.json \
  --aesthetic-check <staging>/canvas-aesthetic-check.json \
  --render-metrics <staging>/canvas-render-metrics.json \
  --render-check <staging>/canvas-render-check.json --delete-qa-on-success
```

启用可选版式整理时，最终验证额外传入 `--layout-refinement-report <tmp>/layout-refinement-report.json`；未启用时不需要该文件。

它验证 source-original exclusion、frontmatter、H1/page markers、wikilinks/assets，以及 Canvas 的语义结构、真实 DOM 高度、安全余量、有效字体、路径和非重叠布局；成功后删除全部 staging QA 文件。

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
