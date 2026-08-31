# Lecture Slides to Obsidian

一个面向长期维护的 Agent Skill 项目：把 Canvas 中下载或本地已有的 lecture-slide PDF，整理成适合课前预习、课上补充的 Obsidian Markdown。

当前是 **Phase 1：规范与骨架**。仓库已经定义技能入口、持久课程路由、输出契约、质量门槛、测试素材规则和跨工具安装方式，但**尚未实现或绑定任何 PDF 提取引擎**。

## 设计目标

- 追求 semantic fidelity，而不是宣称 PDF → Markdown “无损”。
- 文字、层级、列表、公式和表格尽量结构化。
- 图表、复杂排版、手写标注和低置信度页面保留视觉兜底。
- 输出可直接放进 Obsidian vault，资源使用相对路径。
- 用户在一个新学期首次提供课程名称时，只询问一次学期根目录并持久记录学期与课程映射。
- 后续通过课程代码、正式名称或已登记别名唯一匹配，自动归档到对应学期的课程子目录。
- 同一份技能内容兼容 Claude Code 和 Pi，并适合作为 cc-switch 自定义技能源。
- 默认本地处理，不把课件上传到第三方服务。

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
│       ├── references/
│       └── scripts/
└── tests/
    ├── cases/
    ├── fixtures/
    └── golden/
```

`skills/lecture-slides-to-obsidian/` 是可分发、可安装的完整技能目录。仓库级的 `tests/` 和 `scripts/` 只用于开发维护，不随技能运行。

## 课程路由模型

技能使用本机注册表：

```text
~/.config/lecture-slides-to-obsidian/course-registry.yaml
```

首次处理一门尚未登记的课程时：

1. 用户输入课程名称或课程代码。
2. 若没有可用的 active semester，Agent 询问该学期的根目录；同一学期只需提供一次。
3. Agent 在根目录内精确查找课程文件夹；没有现成目录时创建安全的课程目录和默认子目录。
4. Agent 将学期根目录、课程别名、课程相对目录和分类规则写入本机注册表。
5. 以后只要 active semester 仍有效，新课程也会直接在该根目录下登记；已登记课程唯一匹配时直接分类，不再询问路径。

默认分类契约为：

```text
<semester-root>/
└── <course-folder>/
    ├── Slides/                 # 原始 PDF 的保留副本
    └── Lectures/
        ├── <lecture>.md        # Obsidian 课堂笔记
        ├── assets/<lecture>/   # 图像与页面兜底
        └── reports/            # 转换报告
```

如果学期根目录已有明确的课程/课件/笔记子目录，Agent 应优先复用并记录它们。模糊匹配、多个同名学期课程、失效根目录或多个候选课程文件夹不会自动选择。

注册表是本机状态，不能放在技能安装目录内，也不应提交 GitHub。完整匹配与安全规则见 `references/course-routing.md`。

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

```bash
./scripts/validate.sh
```

验证包括：Agent Skills frontmatter、必需资源、未完成占位符、目录边界和合成测试素材约定。它只证明骨架一致，不证明转换质量。

## 测试素材政策

- `tests/fixtures/synthetic/`：可提交自行生成、可再分发的小型 PDF。
- `tests/fixtures/public/`：仅提交许可证和来源明确的公开材料，并附元数据。
- `tests/fixtures/private/`：本机私有课件，已被 Git 忽略，不得提交。
- `tests/golden/`：只保存由可再分发素材生成的期望输出。
- 真实课程 PDF、学生信息、Canvas 会话数据和登录凭据不得进入仓库。

详细规则见 `tests/fixtures/README.md`。

## 后续阶段

1. 用代表性课件建立合成/公开基准集。
2. 实现课程注册表的原子读写、唯一匹配和目录路由测试。
3. 定义 fast path 与 layout-aware path 的适配接口。
4. 选择并实现第一个本地提取后端。
5. 加入输出契约验证、回归测试和转换报告。
6. 在真实课前工作流中小范围试用，再依据失败样例修订技能。

## 暂未决定

- 默认提取引擎及其版本。
- Python、Node 或其他实现语言。
- OCR、公式识别与表格识别的具体依赖。
- GitHub 仓库地址、许可证和发布策略。

这些内容应在有实现和测试证据后再确定。
