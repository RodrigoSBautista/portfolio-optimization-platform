import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Compare } from "./views/Compare";
import { DashboardPage } from "./views/DashboardPage";
import { Diversification } from "./views/Diversification";
import { Layout } from "./views/Layout";
import { Login } from "./views/Login";
import { OptimizePage } from "./views/OptimizePage";
import { Projection } from "./views/Projection";
import { Retirement } from "./views/Retirement";
import { Tracking } from "./views/Tracking";

// Layout renders the persistent chrome + an AnimatePresence-wrapped <Outlet>, so
// the routed children below cross-fade on navigation (reduced-motion aware).
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/projection" element={<Projection />} />
          <Route path="/retirement" element={<Retirement />} />
          <Route path="/optimize" element={<OptimizePage />} />
          <Route path="/diversification" element={<Diversification />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/tracking" element={<Tracking />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
