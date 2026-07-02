import { useAuth } from "../auth/useAuth";
import { MenuIcon } from "./icons";
import { ThemeToggle } from "./ThemeToggle";

interface Props {
  onMenu: () => void;
}

export function TopBar({ onMenu }: Props) {
  const { user, logout } = useAuth();
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-edge bg-surface px-3 sm:px-4 dark:border-edge-dark dark:bg-surface-dark">
      <button
        onClick={onMenu}
        aria-label="Open navigation"
        className="rounded-lg p-2 text-content-muted hover:bg-surface-alt hover:text-content focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand lg:hidden dark:text-content-dark-muted dark:hover:bg-surface-dark-alt"
      >
        <MenuIcon />
      </button>
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-brand">Portfolio</span>
        <span className="text-lg font-light text-content-muted dark:text-content-dark-muted">
          Finance
        </span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        {user && (
          <span className="hidden text-sm text-content-muted sm:inline dark:text-content-dark-muted">
            {user.username}
          </span>
        )}
        <button
          onClick={logout}
          className="rounded-lg border border-edge px-3 py-1.5 text-sm transition hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand dark:border-edge-dark dark:hover:bg-surface-dark-alt"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
