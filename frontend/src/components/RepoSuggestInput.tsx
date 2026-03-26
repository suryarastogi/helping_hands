import { type KeyboardEvent, useEffect, useRef, useState } from "react";

export interface RepoSuggestInputProps {
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
  className?: string;
  required?: boolean;
  placeholder?: string;
  ariaLabel?: string;
}

/**
 * A text input with a dropdown of recent repo suggestions.
 * Used for the main repo_path field.
 */
export default function RepoSuggestInput({
  value,
  onChange,
  suggestions,
  className,
  required,
  placeholder = "owner/repo",
  ariaLabel = "Repository path",
}: RepoSuggestInputProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const filtered = value.trim()
    ? suggestions.filter((s) =>
        s.toLowerCase().includes(value.trim().toLowerCase()),
      )
    : suggestions;

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setShowDropdown(true);
      setHighlightIdx((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter" && highlightIdx >= 0 && highlightIdx < filtered.length) {
      e.preventDefault();
      onChange(filtered[highlightIdx]);
      setShowDropdown(false);
      setHighlightIdx(-1);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      setHighlightIdx(-1);
    }
  };

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
    <div className="repo-suggest-wrapper" ref={wrapperRef}>
      <input
        className={className}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowDropdown(true);
          setHighlightIdx(-1);
        }}
        onFocus={() => setShowDropdown(true)}
        onKeyDown={handleKeyDown}
        required={required}
        placeholder={placeholder}
        aria-label={ariaLabel}
        autoComplete="off"
      />
      {showDropdown && filtered.length > 0 && (
        <ul className="repo-chip-dropdown">
          {filtered.slice(0, 8).map((repo, idx) => (
            <li
              key={repo}
              className={`repo-chip-option${idx === highlightIdx ? " highlighted" : ""}`}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(repo);
                setShowDropdown(false);
                setHighlightIdx(-1);
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
