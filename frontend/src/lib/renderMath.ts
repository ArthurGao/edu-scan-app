import katex from "katex";

/* ------------------------------------------------------------------ */

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

/**
 * Render text containing both markdown formatting and math.
 * Handles: **bold**, bullet lists (- item), line breaks, plus $...$  / $$...$$ math.
 * Suitable for AI-generated follow-up replies.
 */
export function renderRichText(text: string): string {
  if (!text) return "";

  // Step 1: Render math (also HTML-escapes non-math text)
  let html = renderMathText(text);

  // Step 2: Bold  (**...**)
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Step 3: Convert lines starting with "- " into list items
  const lines = html.split("\n");
  const out: string[] = [];
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trimStart();
    if (trimmed.startsWith("- ")) {
      if (!inList) {
        out.push('<ul class="list-disc pl-5 my-1 space-y-0.5">');
        inList = true;
      }
      out.push(`<li>${trimmed.slice(2)}</li>`);
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push(line);
    }
  }
  if (inList) out.push("</ul>");

  // Step 4: Line breaks — double newline → paragraph gap, single → <br>
  html = out.join("\n");
  html = html.replace(/\n\n/g, '<div class="my-2"></div>');
  html = html.replace(/\n/g, "<br>");

  return html;
}
