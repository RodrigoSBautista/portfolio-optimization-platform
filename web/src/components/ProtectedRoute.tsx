import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) {
    return (
      <div
        className="flex h-full items-center justify-center"
        role="status"
        aria-label="Loading"
      >
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-edge border-t-brand dark:border-edge-dark dark:border-t-brand" />
      </div>
    );
  }
  // Remember where the user was headed so Login can return them there.
  return isAuthenticated ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace state={{ from: location }} />
  );
}
