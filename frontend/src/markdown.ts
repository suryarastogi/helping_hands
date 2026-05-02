/**
 * Simple markdown renderer for grill me messages (no external deps).
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function renderMarkdown(md: string): string {
  // Fenced code blocks
  let html = md.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_match, lang, code) =>
      `<pre class="grill-code-block"><code class="language-${escapeHtml(lang)}">${escapeHtml(code.trimEnd())}</code></pre>`,
  );
  // Inline code
  html = html.replace(/`([^`]+)`/g, (_m, code) => `<code class="grill-inline-code">${escapeHtml(code)}</code>`);
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
  // Don't break inside pre blocks
  html = html.replace(/<pre([^>]*)>([\s\S]*?)<\/pre>/g, (_m, attrs, inner) =>
    `<pre${attrs}>${inner.replace(/<br\/>/g, "\n")}</pre>`,
  );

  return html;
}
