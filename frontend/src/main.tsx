import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles/app.css";

const root = document.getElementById("kok");
if (!root) throw new Error("#kok öğesi bulunamadı");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
