import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
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
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
