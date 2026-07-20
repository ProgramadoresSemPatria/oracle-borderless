import { Routes, Route } from "react-router-dom";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<div>Landing</div>} />
      <Route path="/about" element={<div>About</div>} />
      <Route path="/knowledge" element={<div>Knowledge</div>} />
      <Route path="/oracle" element={<div>Oracle</div>} />
      <Route path="/oracle/:conversationId" element={<div>Oracle</div>} />
    </Routes>
  );
}
