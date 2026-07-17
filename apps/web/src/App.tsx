import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { BrandPage } from "./pages/BrandPage";
import { BrainsPage } from "./pages/BrainsPage";
import { ChatPage } from "./pages/ChatPage";
import { IdeaToAgenticPage } from "./pages/IdeaToAgenticPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { MCPPage } from "./pages/MCPPage";
import { MemoryPage } from "./pages/MemoryPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";
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
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="onboarding/*" element={<OnboardingPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="memory" element={<MemoryPage />} />
        <Route path="brains" element={<BrainsPage />} />
        <Route path="skills" element={<SkillsPage />} />
        <Route path="idea-to-agentic" element={<IdeaToAgenticPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="mcp" element={<MCPPage />} />
        <Route path="brand" element={<BrandPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
