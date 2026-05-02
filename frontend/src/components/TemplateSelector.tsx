import { useEffect, useState } from "react";

import type { Backend, FormState, TaskTemplate } from "../types";
import { apiUrl } from "../App.utils";

export interface TemplateSelectorProps {
  onApply: <K extends keyof FormState>(key: K, value: FormState[K]) => void;
}

export default function TemplateSelector({ onApply }: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(apiUrl("/templates"));
        if (!r?.ok) return;
        const data = (await r.json()) as { templates: TaskTemplate[] };
        if (!cancelled) setTemplates(data.templates);
      } catch {
        // network error or mock returning undefined — ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelect = (templateId: string) => {
    if (!templateId) return;
    const tmpl = templates.find((t) => t.template_id === templateId);
    if (!tmpl) return;

    if (tmpl.repo_path != null) onApply("repo_path", tmpl.repo_path);
    if (tmpl.prompt != null) onApply("prompt", tmpl.prompt);
    if (tmpl.backend != null) onApply("backend", tmpl.backend as Backend);
    if (tmpl.model != null) onApply("model", tmpl.model);
    if (tmpl.max_iterations != null) onApply("max_iterations", tmpl.max_iterations);
    if (tmpl.pr_number != null) onApply("pr_number", String(tmpl.pr_number));
    if (tmpl.issue_number != null) onApply("issue_number", String(tmpl.issue_number));
    if (tmpl.create_issue != null) onApply("create_issue", tmpl.create_issue);
    if (tmpl.project_url != null) onApply("project_url", tmpl.project_url);
    if (tmpl.no_pr != null) onApply("no_pr", tmpl.no_pr);
    if (tmpl.enable_execution != null) onApply("enable_execution", tmpl.enable_execution);
    if (tmpl.enable_web != null) onApply("enable_web", tmpl.enable_web);
    if (tmpl.use_native_cli_auth != null) onApply("use_native_cli_auth", tmpl.use_native_cli_auth);
    if (tmpl.fix_ci != null) onApply("fix_ci", tmpl.fix_ci);
    if (tmpl.fix_conflicts != null) onApply("fix_conflicts", tmpl.fix_conflicts);
    if (tmpl.master_rebase != null) onApply("master_rebase", tmpl.master_rebase);
    if (tmpl.ci_check_wait_minutes != null) onApply("ci_check_wait_minutes", tmpl.ci_check_wait_minutes);
    if (tmpl.reference_repos != null) onApply("reference_repos", tmpl.reference_repos.join(", "));
    if (tmpl.tools != null) onApply("tools", tmpl.tools.join(", "));
  };

  if (loading || templates.length === 0) return null;

  return (
    <div className="template-selector" style={{ marginBottom: "0.5rem" }}>
      <select
        onChange={(e) => handleSelect(e.target.value)}
        defaultValue=""
        aria-label="Apply a task template"
        style={{ width: "100%" }}
      >
        <option value="">Apply template...</option>
        {templates.map((t) => (
          <option key={t.template_id} value={t.template_id}>
            {t.name}{t.description ? ` — ${t.description}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
