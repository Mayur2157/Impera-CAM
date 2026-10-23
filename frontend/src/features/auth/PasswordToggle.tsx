import { Eye, EyeOff } from "lucide-react";

export function PasswordToggle({ shown, onToggle }: { shown: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={shown}
      aria-label={shown ? "Hide password" : "Show password"}
      className="grid size-9 place-items-center rounded-md text-muted hover:text-text"
    >
      {shown ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
    </button>
  );
}
