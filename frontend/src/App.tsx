import { Routes, Route } from "react-router-dom";
import LandingPage from "./features/landing/LandingPage";
import AboutPage from "./features/about/AboutPage";
import KnowledgePage from "./features/knowledge/KnowledgePage";
import ChatPage from "./features/chat/ChatPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/knowledge" element={<KnowledgePage />} />
      <Route path="/oracle" element={<ChatPage />} />
      <Route path="/oracle/:conversationId" element={<ChatPage />} />
    </Routes>
  );
}
