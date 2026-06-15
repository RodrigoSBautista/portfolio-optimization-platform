import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-content-muted dark:text-content-dark-muted">
        Loading…
      </div>
    );
  }
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
