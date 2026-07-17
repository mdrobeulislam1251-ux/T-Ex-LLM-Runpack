import { Navigate, Route, Routes } from "react-router-dom";
import RuntimeConsole from "./components/RuntimeConsole";
import { Shell } from "./components/Shell";
import { BrandPage } from "./pages/BrandPage";
import { BrainsPage } from "./pages/BrainsPage";
import { ChatPage } from "./pages/ChatPage";
import { DomainReviewPage } from "./pages/DomainReviewPage";
import { IdeaToAgenticPage } from "./pages/IdeaToAgenticPage";
import { IdeasPage } from "./pages/IdeasPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobsPage } from "./pages/JobsPage";
import { MCPPage } from "./pages/MCPPage";
import { MemoryPage } from "./pages/MemoryPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PersonalBdPage } from "./pages/PersonalBdPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";
import { TeamDashboardPage } from "./pages/TeamDashboardPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { useSettings } from "./state/settings";

function HomeRedirect() {
  const { settings } = useSettings();
  // Default into the Grok-style runtime console for product review
  return (
    <Navigate to={settings.onboarded ? "/console" : "/console"} replace />
  );
}

export default function App() {
  return (
    <Routes>
      {/* Full-bleed Grok aesthetic runtime console (no legacy shell) */}
      <Route path="console" element={<RuntimeConsole />} />
      <Route index element={<HomeRedirect />} />

      <Route element={<Shell />}>
        <Route path="workspace" element={<WorkspacePage />} />
        <Route path="teams/:slug" element={<TeamDashboardPage />} />
        <Route path="domain-review" element={<DomainReviewPage />} />
        <Route path="personal-bd" element={<PersonalBdPage />} />
        <Route path="ideas" element={<IdeasPage />} />
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
        <Route path="*" element={<Navigate to="/console" replace />} />
      </Route>
    </Routes>
  );
}
