import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Mail,
  ClipboardList,
  Table,
  Settings,
  FileText,
  Save,
  LogOut,
  User,
} from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { removeToken } from "@/services/api";

const cn = (...classes: string[]) => twMerge(clsx(classes));

const NAV = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Email Inbox", href: "/inbox", icon: Mail },
  { name: "Review Queue", href: "/review", icon: ClipboardList },
  { name: "Placement Register", href: "/register", icon: Table },
  { name: "Audit Log", href: "/audit", icon: FileText },
  { name: "Backup", href: "/backup", icon: Save },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const token = localStorage.getItem("placementsync_token");
  const user = localStorage.getItem("placementsync_user");

  const handleLogout = () => {
    removeToken();
    localStorage.removeItem("placementsync_user");
    navigate("/login");
  };

  const authButtons = token ? (
    <>
      <div className="hidden md:flex items-center gap-2">
        <User className="h-5 w-5 text-gray-600" />
        <span className="text-sm font-medium text-gray-700 hidden sm:block">
          {user ? JSON.parse(user).username : "User"}
        </span>
      </div>
      <button
        onClick={handleLogout}
        className="btn-outline text-sm px-3 py-1.5"
      >
        <LogOut className="h-4 w-4 mr-2" />
        Sign out
      </button>
    </>
  ) : (
    <button
      onClick={() => navigate("/login")}
      className="btn-primary text-sm px-4 py-2"
    >
      Sign in
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50 border-gray-200">
      <nav className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-auto rounded-md bg-indigo-600 p-1 text-white">
            <span className="ml-1 text-sm font-bold">PS</span>
          </div>
          <span className="font-bold text-gray-900 tracking-tight">PlacementSync</span>
        </div>
        <div className="flex items-center gap-4">
          <nav className="hidden md:flex items-center gap-2">
            <Link
              to="/"
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                location.pathname === "/"
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
              )}
            >
              Dashboard
            </Link>
            <Link
              to="/inbox"
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                location.pathname === "/inbox"
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
              )}
            >
              Inbox
            </Link>
            <Link
              to="/review"
              className={cn(
                "px-3 py-2 text-sm font-medium transition-colors",
                location.pathname === "/review"
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
              )}
            >
              Review
            </Link>
          </nav>
          <div className="flex items-center gap-3">{authButtons}</div>
        </div>
      </nav>

      <div className="flex">
        <aside className="hidden w-64 flex-col border-r border-gray-200 bg-white md:flex">
          <div className="flex h-full flex-col py-6">
            <nav className="flex-1 space-y-1 px-3">
              {NAV.map((item) => {
                const Icon = item.icon;
                const active = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </div>
        </aside>

        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}
