"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import type { AuthUser } from "@/types";

const PUBLIC_PATHS = ["/", "/login"];
const SIDEBAR_WIDTH = 240;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    setUser(stored ? JSON.parse(stored) : null);
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("medsift_user");
    setUser(null);
    router.push("/login");
  };

  const isPublic = PUBLIC_PATHS.includes(pathname);

  if (isPublic || !user) return <>{children}</>;

  return (
    <div className="min-h-screen bg-slate-50 relative overflow-x-hidden">
      {/* Background (your blobs) */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden" aria-hidden>
        <svg
          viewBox="0 0 800 600"
          xmlns="http://www.w3.org/2000/svg"
          className="absolute -top-32 -right-32 w-[600px] h-[600px] opacity-[0.18]"
        >
          <defs>
            <linearGradient id="wg1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0288d1" />
              <stop offset="100%" stopColor="#00c853" />
            </linearGradient>
          </defs>
          <path
            d="M400,80 C520,60 680,120 720,260 C760,400 660,520 520,560 C380,600 200,540 120,420 C40,300 80,140 200,100 C280,72 320,96 400,80 Z"
            fill="url(#wg1)"
          />
        </svg>

        <svg
          viewBox="0 0 700 600"
          xmlns="http://www.w3.org/2000/svg"
          className="absolute -bottom-40 -left-32 w-[500px] h-[500px] opacity-[0.14]"
        >
          <defs>
            <linearGradient id="wg2" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1565c0" />
              <stop offset="100%" stopColor="#26c6da" />
            </linearGradient>
          </defs>
          <path
            d="M350,60 C470,40 600,130 620,280 C640,430 540,560 380,580 C220,600 80,500 50,360 C20,220 100,80 220,55 C280,42 300,72 350,60 Z"
            fill="url(#wg2)"
          />
        </svg>

        <svg
          viewBox="0 0 1440 200"
          xmlns="http://www.w3.org/2000/svg"
          className="absolute top-1/3 left-0 w-full opacity-[0.08]"
          preserveAspectRatio="none"
        >
          <path
            d="M0,100 C240,40 480,160 720,100 C960,40 1200,160 1440,100 L1440,200 L0,200 Z"
            fill="#0288d1"
          />
        </svg>
      </div>

      <Sidebar user={user} onLogout={handleLogout} />

      <main className="relative z-10" style={{ marginLeft: SIDEBAR_WIDTH }}>
        {children}
      </main>
    </div>
  );
}