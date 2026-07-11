import { useEffect } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Today from "./pages/Today";
import BriefPage from "./pages/BriefPage";
import Learn from "./pages/Learn";

// SPAs keep the scroll position across route changes; a reader who was at the
// bottom of one page would land at the bottom of the next. Reset on every
// pathname change (instant, not smooth — a navigation, not an animation).
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <>
      <ScrollToTop />
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
    </>
  );
}
