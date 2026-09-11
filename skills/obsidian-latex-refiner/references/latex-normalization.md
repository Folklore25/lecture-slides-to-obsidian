# LaTeX normalization rules

MinerU can emit LaTeX that is valid in a document toolchain but does not render in Obsidian's MathJax. This skill performs the mechanical, content-preserving subset of fixes. Anything requiring a meaning decision stays out of scope and is reported for review.

## Delimiters

| MinerU form | Obsidian form |
| --- | --- |
| `\\( ... \\)` | `$ ... $` |
| `\begin{math} ... \end{math}` | `$ ... $` |
| `\\[ ... \\]` | `$$ ... $$` |
| `\begin{displaymath} ... \end{displaymath}` | `$$ ... $$` |
| `\begin{equation} ... \end{equation}` | `$$ ... $$` |
| `\begin{equation*} ... \end{equation*}` | `$$ ... $$` |

## Environments

| MinerU environment | Obsidian environment |
| --- | --- |
| `align`, `align*`, `eqnarray`, `eqnarray*`, `flalign`, `flalign*`, `alignat`, `alignat*`, `split` | `aligned` |
| `gather`, `gather*`, `multline`, `multline*` | `gathered` |
| `cases`, `array`, `matrix`, `pmatrix`, `bmatrix`, `Bmatrix`, `vmatrix`, `Vmatrix`, `smallmatrix`, `subarray` | unchanged |

A top-level environment is wrapped in `$$ ... $$`. An environment already inside a display span is renamed in place.

## Non-rendering commands

`\label{...}`, `\nonumber`, and `\notag` are removed because they carry no visible glyphs. `\tag{...}` is preserved because it is visible.

## CJK inside math

A raw CJK run inside math is wrapped in a text command so it renders upright. A CJK run already inside `\text{...}`, `\mbox{...}`, or `\textrm{...}` is left alone. Use `--no-cjk` to disable this transformation. Canonical comparison neutralizes the wrapper so conservation still holds.

## Multiline inline math

An inline `$...$` span that contains a single newline is promoted to a display `$$...$$` span, because Obsidian does not render inline math across lines.

## Review-only cases

These are reported in `review_items` and never auto-transformed, because deciding them requires meaning:

- `\begin{table}` or `\begin{tabular}`: keep the extracted table image or convert manually;
- `\includegraphics`: replace with an Obsidian embed of the extracted asset;
- `\href` or `\url`: convert to a Markdown link;
- `\cite`, `\ref`, `\eqref`, or `\footnote`: reference plumbing that MathJax will not render;
- an unbalanced dollar delimiter: verify the page manually.

## Examples

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

Before:

```markdown
$$能量 E = mc^2$$
```

After:

```markdown
$$
\text{能量} E = mc^2
$$
```
