# LaTeX normalization rules

Any toolchain can emit LaTeX that is valid for a document compiler but does not render in Obsidian's MathJax: MinerU, LaTeXML, pandoc, an LLM draft, or a hand-written note. This skill performs the mechanical, content-preserving subset of fixes. Anything requiring a meaning decision stays out of scope and is reported for review.

## Agent decision flow

1. Run the analyzer: `normalize-latex.py --target <note> --analyze`. It is read-only.
2. Read `totals`, `recommended_transforms`, and `review_items`.
3. Choose the groups to apply with `--only shell,delimiters,environments,labels,cjk,multiline-inline`, or omit `--only` to apply all recommended groups.
4. Optionally preview with `--dry-run`.
5. Apply, then confirm the report is `valid` and the on-disk hash matches `refined_sha256`.

## Delimiters

| Source form | Obsidian form |
| --- | --- |
| `\( ... \)` | `$ ... $` |
| `\begin{math} ... \end{math}` | `$ ... $` |
| `\[ ... \]` | `$$ ... $$` |
| `\begin{displaymath} ... \end{displaymath}` | `$$ ... $$` |

## Environments

| Source environment | Obsidian environment |
| --- | --- |
| `equation`, `equation*` | unwrapped into `$$ ... $$` |
| `align`, `align*`, `eqnarray`, `eqnarray*`, `flalign`, `flalign*`, `alignat`, `alignat*`, `split` | `aligned` |
| `gather`, `gather*`, `multline`, `multline*` | `gathered` |
| `cases`, `array`, `matrix`, `pmatrix`, `bmatrix`, `Bmatrix`, `vmatrix`, `Vmatrix`, `smallmatrix`, `subarray` | unchanged |

A bare environment outside a display span is wrapped in `$$ ... $$`. An environment already inside a display span is renamed in place.

## Redundant display shell

When a math payload already carries its own display delimiters and a pipeline wraps it a second time, the result is a doubled fence with the formula stranded between the two pairs:

```markdown
$$

$$
E = mc^2
$$

$$
```

The `shell` transform collapses this to one display block:

```markdown
$$
E = mc^2
$$
```

Without the collapse the parser sees two empty math spans and the formula is left as plain text. The analyzer reports this as `redundant_display_shell`.

## Non-rendering commands

`\label{...}`, `\nonumber`, and `\notag` are removed because they carry no visible glyphs. `\tag{...}` is preserved because it is visible.

## CJK inside math

A raw CJK run inside math is wrapped in a text command so it renders upright. A CJK run already inside `\text{...}`, `\mbox{...}`, or `\textrm{...}` is left alone. Use `--only` without `cjk`, or `--no-cjk`, to skip it. Canonical comparison neutralizes the wrapper so conservation still holds.

## Multiline inline math

An inline `$...$` span that contains a single newline is promoted to a display `$$...$$` span, because Obsidian does not render inline math across lines.

## Review-only cases

These are reported in `review_items` and never auto-transformed, because deciding them requires meaning:

- `\begin{table}` or `\begin{tabular}`: keep the extracted table image or convert manually;
- `\includegraphics`: replace with an Obsidian embed of the extracted asset;
- `\href` or `\url`: convert to a Markdown link;
- `\cite`, `\ref`, `\eqref`, or `\footnote`: reference plumbing that MathJax will not render;
- an unbalanced dollar, parenthesis, or bracket delimiter: verify the page manually.

## Example

Before:

```markdown
Solve \(x^2 = 4\).

\[
\begin{align}
x &= 2 \\
x &= -2 \nonumber
\end{align}
\]
```

After:

```markdown
Solve $x^2 = 4$.

$$
\begin{aligned}
x &= 2 \\
x &= -2
\end{aligned}
$$
```
