import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Today from "./pages/Today";
import BriefPage from "./pages/BriefPage";
import Learn from "./pages/Learn";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/today" element={<Today />} />
        <Route path="/brief" element={<BriefPage />} />
        <Route path="/brief/:date" element={<BriefPage />} />
        <Route path="/learn" element={<Learn />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
