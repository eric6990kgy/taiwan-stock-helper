import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Journal } from "./pages/Journal";
import { Portfolio } from "./pages/Portfolio";
import { Recommendations } from "./pages/Recommendations";
import { Research } from "./pages/Research";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { Strategy } from "./pages/Strategy";
import { Transactions } from "./pages/Transactions";
import { Watchlist } from "./pages/Watchlist";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="portfolio" element={<Portfolio />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="research" element={<Research />} />
        <Route path="watchlist" element={<Watchlist />} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="strategy" element={<Strategy />} />
        <Route path="review" element={<Review />} />
        <Route path="journal" element={<Journal />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
