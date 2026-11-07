import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, Mail, ClipboardList, Table, Settings } from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

const cn = (...classes: string[]) => twMerge(clsx(classes));

const NAV = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Email Inbox", href: "/inbox", icon: Mail },
  { name: "Review Queue", href: "/review", icon: ClipboardList },
  { name: "Placement Register", href: "/register", icon: Table },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();

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
          <button
            onClick={() => navigate("/")}
            className="text-sm font-semibold text-gray-900 hover:text-placementsync-600"
          >
            Dashboard
          </button>
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
