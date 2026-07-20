import { Routes, Route } from "react-router-dom";
import LandingPage from "./features/landing/LandingPage";
import AboutPage from "./features/about/AboutPage";
import KnowledgePage from "./features/knowledge/KnowledgePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/knowledge" element={<KnowledgePage />} />
      <Route path="/oracle" element={<div>Oracle</div>} />
      <Route path="/oracle/:conversationId" element={<div>Oracle</div>} />
    </Routes>
  );
}
