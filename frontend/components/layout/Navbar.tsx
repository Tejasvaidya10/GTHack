"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LogOut, LayoutDashboard, Stethoscope, User } from "lucide-react";
import type { AuthUser } from "@/types";

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    setUser(stored ? JSON.parse(stored) : null);
  }, [pathname]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("medsift_user");
    setUser(null);
    router.push("/login");
  };

  const isClinician = user?.role === "clinician";

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#060f24]/80 backdrop-blur-xl shadow-lg shadow-black/10"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex h-20 items-center">
        {/* Left spacer for centering */}
        <div className="flex-1" />

        {/* Center: Logo — always links home */}
        <Link href="/" className="flex items-center">
          <div className="relative w-[160px] h-[44px]">
            <Image
              src="/logo.png"
              alt="MedSift AI"
              fill
              className="object-cover object-center"
              priority
            />
          </div>
        </Link>

        {/* Right: Auth */}
        <div className="flex-1 flex justify-end">
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="flex items-center gap-2 text-sm text-white/80 hover:text-white hover:bg-white/10"
                >
                  <div className="h-7 w-7 rounded-full bg-white/10 flex items-center justify-center border border-white/10">
                    {isClinician ? (
                      <Stethoscope className="h-3.5 w-3.5 text-[#29b6f6]" />
                    ) : (
                      <User className="h-3.5 w-3.5 text-[#00c853]" />
                    )}
                  </div>
                  <span className="hidden sm:inline">{user.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem asChild>
                  <Link href="/dashboard" className="cursor-pointer">
                    <LayoutDashboard className="mr-2 h-4 w-4" /> Dashboard
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-red-600 cursor-pointer">
                  <LogOut className="mr-2 h-4 w-4" /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link href="/login">
              <Button
                size="sm"
                className="font-semibold text-white border-0 rounded-full px-6 transition-all hover:opacity-90"
                style={{
                  background: "linear-gradient(135deg,#1565c0,#29b6f6)",
                  boxShadow: "0 2px 16px rgba(21,101,192,0.3)",
                }}
              >
                Sign in
              </Button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
