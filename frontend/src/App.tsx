import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Inbox } from "@/pages/Inbox";
import { Review } from "@/pages/Review";
import { Register } from "@/pages/Register";
import { Settings } from "@/pages/Settings";
import { Audit } from "@/pages/Audit";
import { Backup as BackupPage } from "@/pages/Backup";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/inbox" element={<Layout><Inbox /></Layout>} />
        <Route path="/review" element={<Layout><Review /></Layout>} />
        <Route path="/register" element={<Layout><Register /></Layout>} />
        <Route path="/settings" element={<Layout><Settings /></Layout>} />
        <Route path="/audit" element={<Layout><Audit /></Layout>} />
        <Route path="/backup" element={<Layout><BackupPage /></Layout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
