import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Portfolio } from "./pages/Portfolio";
import { Research } from "./pages/Research";
import { Settings } from "./pages/Settings";
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
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
