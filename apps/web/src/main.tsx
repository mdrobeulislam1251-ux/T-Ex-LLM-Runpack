import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { BrandProvider } from "./state/brand";
import { ProjectsProvider } from "./state/projects";
import { SettingsProvider } from "./state/settings";
import { TaskProvider } from "./state/task";
import { ThemeProvider } from "./state/theme";
import "./tailwind.css";
import "./styles/global.css";
import "./styles/runbook.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <SettingsProvider>
          <BrandProvider>
            <ProjectsProvider>
              <TaskProvider>
                <App />
              </TaskProvider>
            </ProjectsProvider>
          </BrandProvider>
        </SettingsProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);
