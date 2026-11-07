import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  XAxis,
  YAxis,
  CartesianGrid,
  LabelList,
} from "recharts";
import { recordsService } from "@/services/api";
import type { DashboardStats } from "@/types";
import { Panel } from "@/components/Panel";

const COLORS = ["#4f46e5", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2"];

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    company: "",
    branch: "",
    status: "",
    date_from: "",
    date_to: "",
  });

  useEffect(() => {
    fetchStats();
  }, [filters.company, filters.branch, filters.status, filters.date_from, filters.date_to]);

  async function fetchStats() {
    setLoading(true);
    try {
      const res = await recordsService.stats({
        company: filters.company || undefined,
        branch: filters.branch || undefined,
        status: filters.status || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
      });
      setStats(res.data);
    } catch (err) {
      console.error("Failed to load dashboard stats", err);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        <p className="text-gray-500">Loading statistics…</p>
      </div>
    );
  }

  const s = stats;
  if (!s) {
    return (
      <div className="page">
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        <p className="text-gray-500">Unable to load statistics.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-500 text-sm">
            Placement statistics and analytics. All figures reflect
            human-approved records only.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6">
        <Panel>
          <div className="flex flex-wrap gap-4 items-end">
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">
              Company
            </label>
            <input
              className="input"
              value={filters.company}
              onChange={(e) => setFilters({ ...filters, company: e.target.value })}
              placeholder="Filter by company"
            />
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">
              Branch
            </label>
            <input
              className="input"
              value={filters.branch}
              onChange={(e) => setFilters({ ...filters, branch: e.target.value })}
              placeholder="e.g. CSE"
            />
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">
              Status
            </label>
            <select
              className="input"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              <option value="">All statuses</option>
              <option value="Selected">Selected</option>
              <option value="Shortlisted">Shortlisted</option>
              <option value="Offered">Offered</option>
            </select>
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">
              From date
            </label>
            <input
              className="input"
              type="date"
              value={filters.date_from}
              onChange={(e) =>
                setFilters({ ...filters, date_from: e.target.value })
              }
            />
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-medium text-gray-500 mb-1">
              To date
            </label>
            <input
              className="input"
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            />
          </div>
          <button
            onClick={() => {
              setFilters({
                company: "",
                branch: "",
                status: "",
                date_from: "",
                date_to: "",
              });
            }}
            className="btn-outline px-4 py-2 text-sm font-semibold"
          >
            Clear filters
          </button>
        </div>
        </Panel>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <StatCard
          title="Total selected students"
          value={s.total_selected_students}
          icon="graduation-cap"
        />
        <StatCard
          title="Unique placed students"
          value={s.total_unique_placed_students}
          icon="user"
        />
        <StatCard
          title="Total companies"
          value={s.total_companies}
          icon="building-2"
        />
        <StatCard
          title="Pending reviews"
          value={s.pending_email_reviews}
          accent
          icon="clock"
        />
        <StatCard
          title="Highest package"
          value={s.highest_package ?? 0}
          suffix=" LPA"
          accent
          icon="trending-up"
        />
        <StatCard
          title="Average package"
          value={s.average_package ?? 0}
          suffix=" LPA"
          icon="file-text"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Branch-wise bar chart */}
        <Panel>
          <h2 className="text-lg font-semibold mb-4">Branch-wise Placements</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={s.branch_statistics}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="branch" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                <LabelList dataKey="count" position="insideTop" fill="#fff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Company-wise bar chart */}
        <Panel>
          <h2 className="text-lg font-semibold mb-4">Company-wise Placements</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={s.company_statistics.slice(0, 10)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="company" angle={-45} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#059669" radius={[4, 4, 0, 0]} />
                <LabelList dataKey="count" position="insideTop" fill="#fff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Package distribution pie chart */}
        <Panel>
          <h2 className="text-lg font-semibold mb-4">Package Distribution</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={s.package_distribution}
                  dataKey="count"
                  nameKey="range"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  labelLine={false}
                  label={({ name, percent }: any) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {s.package_distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  suffix = "",
  accent = false,
  icon = "",
}: {
  title: string;
  value: number;
  suffix?: string;
  accent?: boolean;
  icon?: string;
}) {
  return (
    <div className={`panel p-6 ${accent ? "border-indigo-100" : ""}`}>
      <p className="text-sm text-gray-500">{title}</p>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-3xl font-bold ${accent ? "text-indigo-600" : "text-gray-900"}`}>
          {value}
        </span>
        <span className="text-sm text-gray-500">{suffix}</span>
      </div>
    </div>
  );
}
