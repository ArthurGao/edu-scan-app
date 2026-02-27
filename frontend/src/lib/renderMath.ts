import katex from "katex";

/**
 * Render a pure LaTeX string via KaTeX.
 */
export function renderLatex(latex: string, displayMode = false): string {
  try {
    return katex.renderToString(latex, {
      throwOnError: false,
      displayMode,
    });
  } catch {
    return latex;
  }
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Render mixed text that may contain inline math ($...$) or display math ($$...$$).
 * Non-math portions are HTML-escaped; math portions are rendered via KaTeX.
 */
export function renderMathText(text: string): string {
  if (!text) return "";

  // Collect all math segments with positions
  const segments: {
    start: number;
    end: number;
    latex: string;
    display: boolean;
  }[] = [];

  // Display math: $$...$$
  const displayRegex = /\$\$([\s\S]*?)\$\$/g;
  let match: RegExpExecArray | null;
  while ((match = displayRegex.exec(text)) !== null) {
    segments.push({
      start: match.index,
      end: match.index + match[0].length,
      latex: match[1],
      display: true,
    });
  }

  // Inline math: $...$ (skip positions already claimed by display math)
  const inlineRegex = /\$([^\$\n]+?)\$/g;
  while ((match = inlineRegex.exec(text)) !== null) {
    const overlaps = segments.some(
      (s) => match!.index >= s.start && match!.index < s.end
    );
    if (!overlaps) {
      segments.push({
        start: match.index,
        end: match.index + match[0].length,
        latex: match[1],
        display: false,
      });
    }
  }

  segments.sort((a, b) => a.start - b.start);

  // No math delimiters — return escaped text
  if (segments.length === 0) {
    return escapeHtml(text);
  }

  // Build output with interleaved text and math
  const parts: string[] = [];
  let lastIndex = 0;
  for (const seg of segments) {
    if (seg.start > lastIndex) {
      parts.push(escapeHtml(text.substring(lastIndex, seg.start)));
    }
    const rendered = renderLatex(seg.latex, seg.display);
    parts.push(
      seg.display
        ? `<div class="katex-container my-2">${rendered}</div>`
        : `<span class="katex-container">${rendered}</span>`
    );
    lastIndex = seg.end;
  }
  if (lastIndex < text.length) {
    parts.push(escapeHtml(text.substring(lastIndex)));
  }

  return parts.join("");
}
