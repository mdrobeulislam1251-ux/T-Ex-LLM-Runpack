import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { BrandProvider } from "./state/brand";
import { SettingsProvider } from "./state/settings";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <SettingsProvider>
        <BrandProvider>
          <App />
        </BrandProvider>
      </SettingsProvider>
    </BrowserRouter>
  </StrictMode>
);
