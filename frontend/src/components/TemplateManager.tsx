import { useCallback, useEffect, useState } from "react";

import type { TaskTemplate } from "../types";
import { apiUrl, loadGithubToken } from "../App.utils";

export default function TemplateManager() {
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(apiUrl("/templates"));
      if (!r?.ok) throw new Error("fetch failed");
      const data = (await r.json()) as { templates: TaskTemplate[] };
      setTemplates(data.templates);
      setError(null);
    } catch {
      setError("Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleDelete = async (templateId: string) => {
    const token = loadGithubToken();
    const headers: Record<string, string> = {};
    if (token) headers["X-GitHub-Token"] = token;

    try {
      const resp = await fetch(apiUrl(`/templates/${templateId}`), {
        method: "DELETE",
        headers,
      });
      if (resp.ok || resp.status === 204) {
        setTemplates((prev) => prev.filter((t) => t.template_id !== templateId));
      } else {
        const data = await resp.json().catch(() => ({}));
        setError((data as { detail?: string }).detail ?? `Delete failed (${resp.status})`);
      }
    } catch {
      setError("Delete request failed");
    }
  };

  if (loading) return <p className="muted">Loading templates...</p>;
  if (error) return <p className="muted" style={{ color: "var(--danger)" }}>{error}</p>;
  if (templates.length === 0) return <p className="muted">No saved templates.</p>;

  return (
    <div className="template-manager">
      <table style={{ width: "100%", fontSize: "0.85rem" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Name</th>
            <th style={{ textAlign: "left" }}>Description</th>
            <th style={{ textAlign: "left" }}>Created</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {templates.map((t) => (
            <tr key={t.template_id}>
              <td>{t.name}</td>
              <td className="muted">{t.description || "—"}</td>
              <td className="muted">{new Date(t.created_at).toLocaleDateString()}</td>
              <td>
                <button
                  type="button"
                  className="btn-link danger"
                  onClick={() => handleDelete(t.template_id)}
                  aria-label={`Delete template ${t.name}`}
                  style={{ fontSize: "0.8rem" }}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
