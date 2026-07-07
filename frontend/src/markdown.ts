/**
 * Simple markdown renderer for grill me messages (no external deps).
 *
 * Security: output is injected via dangerouslySetInnerHTML, so ALL input
 * text is HTML-escaped before any formatting is applied. Code blocks and
 * inline code are extracted into placeholders first (their content is
 * escaped independently), the remaining text is escaped wholesale, and the
 * markdown transforms then run on already-escaped text.
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// NUL bytes delimit code placeholders — they can't appear in the input
// because we strip them below, so untrusted text can't forge a placeholder.
// eslint-disable-next-line no-control-regex
const PLACEHOLDER_RE = /\x00CODE(\d+)\x00/g;
// eslint-disable-next-line no-control-regex
const NUL_RE = /\x00/g;

export function renderMarkdown(md: string): string {
  // Strip NUL characters so untrusted input can't forge placeholder tokens.
  let text = md.replace(NUL_RE, "");

  const placeholders: string[] = [];
  const stash = (renderedHtml: string): string => {
    placeholders.push(renderedHtml);
    return `\x00CODE${placeholders.length - 1}\x00`;
  };

  // Fenced code blocks — extract first so their content is untouched by
  // later transforms (content is escaped here).
  text = text.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_match, lang: string, code: string) =>
      stash(
        `<pre class="grill-code-block"><code class="language-${escapeHtml(lang)}">${escapeHtml(code.trimEnd())}</code></pre>`,
      ),
  );
  // Inline code — same placeholder treatment.
  text = text.replace(/`([^`]+)`/g, (_m, code: string) =>
    stash(`<code class="grill-inline-code">${escapeHtml(code)}</code>`),
  );

  // Escape EVERYTHING that remains before applying formatting.
  let html = escapeHtml(text);

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h4 class="grill-h">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="grill-h">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="grill-h">$1</h2>');
  // Unordered lists
  html = html.replace(/^- (.+)$/gm, '<li class="grill-li">$1</li>');
  html = html.replace(
    /(<li class="grill-li">[\s\S]*?<\/li>)/g,
    '<ul class="grill-ul">$1</ul>',
  );
  // Collapse adjacent <ul> tags
  html = html.replace(/<\/ul>\s*<ul class="grill-ul">/g, "");
  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="grill-li">$1</li>');
  // Paragraphs (double newline)
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  // Clean up empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, "");
  // Line breaks within paragraphs
  html = html.replace(/\n/g, "<br/>");

  // Restore extracted code blocks / inline code (already escaped & rendered).
  // Restoring after the <br/> pass means pre content keeps its raw newlines.
  html = html.replace(PLACEHOLDER_RE, (_m, idx: string) => placeholders[Number(idx)] ?? "");

  return html;
}
