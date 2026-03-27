import { type KeyboardEvent, useEffect, useRef, useState } from "react";

export interface RepoChipInputProps {
  /** Current chips (repo strings). */
  value: string[];
  /** Called when chips change. */
  onChange: (repos: string[]) => void;
  /** Suggestions to show in the dropdown. */
  suggestions: string[];
  placeholder?: string;
  ariaLabel?: string;
}

/**
 * A chip-based input for repo paths. Users can type a repo, press Enter/Tab/comma
 * to add it as a chip, and click × to remove. A dropdown shows matching suggestions
 * from the recent repos list.
 */
export default function RepoChipInput({
  value,
  onChange,
  suggestions,
  placeholder = "owner/repo",
  ariaLabel = "Reference repos",
}: RepoChipInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = inputValue.trim()
    ? suggestions.filter(
        (s) =>
          s.toLowerCase().includes(inputValue.trim().toLowerCase()) &&
          !value.includes(s),
      )
    : suggestions.filter((s) => !value.includes(s));

  const addChip = (repo: string) => {
    const trimmed = repo.trim();
    if (!trimmed || value.includes(trimmed)) return;
    onChange([...value, trimmed]);
    setInputValue("");
    setHighlightIdx(-1);
  };

  const removeChip = (repo: string) => {
    onChange(value.filter((r) => r !== repo));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "Tab" || e.key === ",") {
      if (highlightIdx >= 0 && highlightIdx < filtered.length) {
        e.preventDefault();
        addChip(filtered[highlightIdx]);
        return;
      }
      if (inputValue.trim()) {
        e.preventDefault();
        addChip(inputValue);
        return;
      }
      // Let Tab pass through when input is empty
      if (e.key === "Tab") return;
    }
    if (e.key === "Backspace" && !inputValue && value.length > 0) {
      removeChip(value[value.length - 1]);
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => Math.min(i + 1, filtered.length - 1));
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => Math.max(i - 1, -1));
    }
    if (e.key === "Escape") {
      setShowDropdown(false);
      setHighlightIdx(-1);
    }
  };

  // Close dropdown on outside click.
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
        setHighlightIdx(-1);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="repo-chip-wrapper" ref={wrapperRef}>
      <div
        className="repo-chip-container"
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((repo) => (
          <span key={repo} className="repo-chip">
            {repo}
            <button
              type="button"
              className="repo-chip-remove"
              onClick={(e) => {
                e.stopPropagation();
                removeChip(repo);
              }}
              aria-label={`Remove ${repo}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          className="repo-chip-input"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value);
            setShowDropdown(true);
            setHighlightIdx(-1);
          }}
          onFocus={() => setShowDropdown(true)}
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? placeholder : ""}
          aria-label={ariaLabel}
        />
      </div>
      {showDropdown && filtered.length > 0 && (
        <ul className="repo-chip-dropdown repo-chip-dropdown-up">
          {filtered.slice(0, 8).map((repo, idx) => (
            <li
              key={repo}
              className={`repo-chip-option${idx === highlightIdx ? " highlighted" : ""}`}
              onMouseDown={(e) => {
                e.preventDefault();
                addChip(repo);
              }}
              onMouseEnter={() => setHighlightIdx(idx)}
            >
              {repo}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
