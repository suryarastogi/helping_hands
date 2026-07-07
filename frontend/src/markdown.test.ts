import { describe, expect, it } from "vitest";

import { renderMarkdown } from "./markdown";

describe("renderMarkdown — XSS hardening", () => {
  it("escapes HTML inside bold markup", () => {
    const out = renderMarkdown("**<img src=x onerror=alert(1)>**");
    expect(out).not.toContain("<img");
    expect(out).toContain("<strong>&lt;img src=x onerror=alert(1)&gt;</strong>");
  });

  it("escapes a bare script tag line", () => {
    const out = renderMarkdown("<script>alert(1)</script>");
    expect(out).not.toContain("<script>");
    expect(out).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
  });

  it("escapes HTML inside headers", () => {
    const out = renderMarkdown("# <b>hi</b>");
    expect(out).not.toContain("<b>");
    expect(out).toContain('<h2 class="grill-h">&lt;b&gt;hi&lt;/b&gt;</h2>');
  });

  it("escapes HTML inside italic and list items", () => {
    const out = renderMarkdown("*<i>x</i>*\n- <u>item</u>");
    expect(out).not.toContain("<i>");
    expect(out).not.toContain("<u>");
    expect(out).toContain("<em>&lt;i&gt;x&lt;/i&gt;</em>");
    expect(out).toContain('<li class="grill-li">&lt;u&gt;item&lt;/u&gt;</li>');
  });

  it("escapes attribute-breaking quotes in plain text", () => {
    const out = renderMarkdown('say "hello"');
    expect(out).toContain("&quot;hello&quot;");
  });

  it("renders fenced code blocks with escaped content", () => {
    const out = renderMarkdown('```js\nconst a = "<script>alert(1)</script>";\n```');
    expect(out).toContain('<pre class="grill-code-block"><code class="language-js">');
    expect(out).not.toContain("<script>");
    expect(out).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
  });

  it("renders inline code with escaped content", () => {
    const out = renderMarkdown("use `<div>` here");
    expect(out).toContain('<code class="grill-inline-code">&lt;div&gt;</code>');
    expect(out).not.toContain("<div>");
  });

  it("does not let NUL bytes forge code placeholders", () => {
    const out = renderMarkdown("\x00CODE0\x00 `real`");
    expect(out).toContain('<code class="grill-inline-code">real</code>');
    // Only the real inline-code span should appear once.
    expect(out.match(/grill-inline-code/g)?.length).toBe(1);
  });
});

describe("renderMarkdown — formatting still works", () => {
  it("renders bold and italic", () => {
    const out = renderMarkdown("**bold** and *italic*");
    expect(out).toContain("<strong>bold</strong>");
    expect(out).toContain("<em>italic</em>");
  });

  it("renders all header levels", () => {
    const out = renderMarkdown("# H1\n## H2\n### H3");
    expect(out).toContain('<h2 class="grill-h">H1</h2>');
    expect(out).toContain('<h3 class="grill-h">H2</h3>');
    expect(out).toContain('<h4 class="grill-h">H3</h4>');
  });

  it("renders unordered lists wrapped in a single ul", () => {
    const out = renderMarkdown("- one\n- two");
    expect(out).toContain('<ul class="grill-ul">');
    expect(out).toContain('<li class="grill-li">one</li>');
    expect(out).toContain('<li class="grill-li">two</li>');
    expect(out.match(/<ul class="grill-ul">/g)?.length).toBe(1);
  });

  it("renders ordered list items", () => {
    const out = renderMarkdown("1. first\n2. second");
    expect(out).toContain('<li class="grill-li">first</li>');
    expect(out).toContain('<li class="grill-li">second</li>');
  });

  it("splits paragraphs on double newline and keeps line breaks", () => {
    const out = renderMarkdown("para one\n\npara two\nsame para");
    expect(out).toContain("</p><p>");
    expect(out).toContain("para two<br/>same para");
  });

  it("keeps raw newlines (not <br/>) inside code blocks", () => {
    const out = renderMarkdown("```\nline1\nline2\n```");
    expect(out).toContain("line1\nline2");
    expect(out).not.toContain("line1<br/>line2");
  });
});
