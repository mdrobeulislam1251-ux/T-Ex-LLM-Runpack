import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { BrandPage } from "./pages/BrandPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useSettings } from "./state/settings";

function HomeRedirect() {
  const { settings } = useSettings();
  return (
    <Navigate to={settings.onboarded ? "/jobs" : "/onboarding"} replace />
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<HomeRedirect />} />
        <Route path="onboarding/*" element={<OnboardingPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailPage />} />
        <Route path="brand" element={<BrandPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
