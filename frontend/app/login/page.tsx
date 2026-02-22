"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Stethoscope, User, ArrowRight,
  Eye, EyeOff, CheckSquare, Square, MessageSquare,
  CheckCircle2, Shield,
} from "lucide-react";
import type { UserRole } from "@/types";
import { toast } from "sonner";

const DEMO_ACCOUNTS: Record<UserRole, { email: string; password: string; name: string }> = {
  clinician: { email: "dr.smith@hospital.org", password: "demo1234", name: "Dr. Smith" },
  patient:   { email: "patient@example.com",   password: "demo1234", name: "Alex Johnson" },
};

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();

  const [role, setRole] = useState<UserRole>((params.get("role") as UserRole) ?? "clinician");
  const [mode, setMode] = useState<"signin" | "signup">("signin");

  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [showPass, setShowPass]       = useState(false);
  const [remember, setRemember]       = useState(false);

  const [name, setName]               = useState("");
  const [dob, setDob]                 = useState("");
  const [phone, setPhone]             = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [smsConsent, setSmsConsent]   = useState(false);

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (mode === "signin") {
      setEmail(DEMO_ACCOUNTS[role].email);
      setPassword(DEMO_ACCOUNTS[role].password);
    } else {
      setEmail(""); setPassword(""); setName(""); setDob(""); setPhone(""); setConfirmPass("");
    }
  }, [role, mode]);

  useEffect(() => {
    if (role === "clinician") setMode("signin");
  }, [role]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "signup" && password !== confirmPass) {
      toast.error("Passwords do not match"); return;
    }
    setLoading(true);
    setTimeout(() => {
      const demoMatch = Object.values(DEMO_ACCOUNTS).find(
        d => d.email.toLowerCase() === email.toLowerCase()
      );
      const resolvedName = mode === "signup"
        ? name.trim() || email.split("@")[0]
        : demoMatch
          ? demoMatch.name
          : role === "clinician"
            ? "Dr. " + email.split("@")[0].replace("dr.", "").replace(/\./g, " ").trim()
            : email.split("@")[0].replace(/\./g, " ").trim();

      const userPayload: Record<string, unknown> = { name: resolvedName, email, role };
      if (mode === "signup" && phone) userPayload.phone = phone;
      if (mode === "signup") userPayload.sms_consent = smsConsent;
      localStorage.setItem("medsift_user", JSON.stringify(userPayload));
      toast.success(mode === "signup"
        ? `Account created! Welcome, ${resolvedName}!`
        : `Welcome back, ${resolvedName}!`
      );
      router.push("/dashboard");
    }, 800);
  };

  const handleGoogle = () => {
    toast.info("Google sign-in is not available in demo mode.");
  };

  const isPatient  = role === "patient";
  const showSignup = isPatient && mode === "signup";

  return (
    <div className="min-h-screen flex bg-gray-50">

      {/* ── LEFT: Image Panel ── */}
      <div className="hidden lg:flex lg:w-[45%] xl:w-[48%] relative overflow-hidden">
        {/* Background gradient shape */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#e0f4fc] via-[#f0faff] to-white" />

        {/* Curved shape */}
        <svg className="absolute top-0 right-0 h-full w-1/2" viewBox="0 0 200 600" preserveAspectRatio="none">
          <path d="M200 0 C100 150, 150 300, 100 450 C50 550, 150 600, 200 600 Z" fill="white" />
        </svg>

        {/* Wave pattern decoration */}
        <svg className="absolute bottom-0 left-0 w-full h-40 opacity-30" viewBox="0 0 400 100">
          <path d="M0 50 Q50 30 100 50 T200 50 T300 50 T400 50 L400 100 L0 100 Z" fill="#0ea5e9" fillOpacity="0.1" />
          <path d="M0 60 Q50 40 100 60 T200 60 T300 60 T400 60" stroke="#0ea5e9" strokeWidth="1" fill="none" opacity="0.3" />
          <path d="M0 70 Q50 50 100 70 T200 70 T300 70 T400 70" stroke="#0ea5e9" strokeWidth="1" fill="none" opacity="0.2" />
        </svg>

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-between p-10 xl:p-14 h-full w-full">
          {/* Logo */}
          <Link href="/" className="-mt-20">
            <Image
              src="/logo.png"
              alt="MedSift AI"
              width={200}
              height={130}
              className="h-48 w-auto object-contain"
              priority
            />
          </Link>

          {/* Center content — rounded image box with floating cards, same size as original */}
          <div className="flex-1 flex items-center justify-center relative">
            <div className="relative">
              {/* ── Only change: local images instead of Unsplash URLs ── */}
              <img
                key={role}
                src={role === "clinician" ? "/clinician-login.png" : "/patient-login.png"}
                alt={role === "clinician" ? "Doctor at desk" : "Doctor and patient consultation"}
                className="w-[280px] xl:w-[320px] h-[350px] xl:h-[400px] object-cover rounded-3xl shadow-2xl"
              />

              {/* Floating card — top right */}
              <div className="absolute -top-4 -right-8 backdrop-blur-xl bg-[#0ea5e9]/20 rounded-2xl p-3 shadow-lg border border-[#0ea5e9]/30">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-lg bg-white/80 flex items-center justify-center">
                    <CheckCircle2 className="h-4 w-4 text-[#0ea5e9]" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-900">&lt;30 Seconds</p>
                    <p className="text-[10px] text-gray-600">Processing Time</p>
                  </div>
                </div>
              </div>

              {/* Floating card — bottom left */}
              <div className="absolute -bottom-4 -left-6 backdrop-blur-xl bg-[#0ea5e9]/20 rounded-2xl p-3 shadow-lg border border-[#0ea5e9]/30">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-lg bg-white/80 flex items-center justify-center">
                    <Shield className="h-4 w-4 text-[#0ea5e9]" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-900">100% Local</p>
                    <p className="text-[10px] text-gray-600">HIPAA Compliant</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom text */}
          <div>
            <h2 className="text-2xl xl:text-3xl font-bold text-gray-900 mb-3">
              {role === "clinician"
                ? "Better clinical intelligence, faster."
                : "Your health, clearly explained."}
            </h2>
            <p className="text-gray-600 text-sm leading-relaxed max-w-sm">
              {role === "clinician"
                ? "Turn patient-doctor conversations into structured SOAP notes, care plans, and risk scores."
                : "Access your visit summaries, medication history, and follow-up reminders."}
            </p>
          </div>
        </div>
      </div>

      {/* ── RIGHT: Form Panel (unchanged) ── */}
      <div className="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-16 xl:px-20 py-12 bg-white">
        <div className="max-w-md mx-auto w-full">

          {/* Mobile logo */}
          <div className="lg:hidden mb-8">
            <Link href="/">
              <Image src="/logo.png" alt="MedSift AI" width={150} height={40} className="h-10 w-auto object-contain" priority />
            </Link>
          </div>

          {/* Role toggle */}
          <div className="flex p-1 rounded-full bg-gray-100 mb-8">
            {(["clinician", "patient"] as UserRole[]).map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-full text-sm font-medium transition-all ${
                  role === r
                    ? "bg-[#0ea5e9] text-white shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {r === "clinician" ? <Stethoscope className="h-4 w-4" /> : <User className="h-4 w-4" />}
                {r === "clinician" ? "Clinician" : "Patient"}
              </button>
            ))}
          </div>

          {/* Heading */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {mode === "signup" ? "Create an account" : "Login to start your session"}
            </h1>
            <p className="text-gray-500 text-sm">
              {mode === "signup"
                ? "Sign up to access your health records"
                : "Welcome back! Please enter your details."}
            </p>
          </div>

          {/* Patient: sign-in / sign-up toggle */}
          {isPatient && (
            <div className="flex gap-4 mb-6">
              <button
                onClick={() => setMode("signin")}
                className={`text-sm font-medium pb-1 border-b-2 transition-colors ${
                  mode === "signin" ? "border-[#0ea5e9] text-[#0ea5e9]" : "border-transparent text-gray-400 hover:text-gray-600"
                }`}
              >
                Existing Patient
              </button>
              <button
                onClick={() => setMode("signup")}
                className={`text-sm font-medium pb-1 border-b-2 transition-colors ${
                  mode === "signup" ? "border-[#0ea5e9] text-[#0ea5e9]" : "border-transparent text-gray-400 hover:text-gray-600"
                }`}
              >
                New Patient
              </button>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {showSignup && (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="name" className="text-sm text-gray-600">Full Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="Alex Johnson"
                    required
                    className="h-12 rounded-xl border-gray-200 bg-gray-50/50 focus:bg-white"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="dob" className="text-sm text-gray-600">Date of Birth</Label>
                    <Input
                      id="dob"
                      type="date"
                      value={dob}
                      onChange={e => setDob(e.target.value)}
                      required
                      className="h-12 rounded-xl border-gray-200 bg-gray-50/50 focus:bg-white"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="phone" className="text-sm text-gray-600">Phone</Label>
                    <Input
                      id="phone"
                      type="tel"
                      value={phone}
                      onChange={e => setPhone(e.target.value)}
                      placeholder="(555) 000-0000"
                      className="h-12 rounded-xl border-gray-200 bg-gray-50/50 focus:bg-white"
                    />
                  </div>
                </div>

                <label className="flex items-start gap-3 cursor-pointer p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-gray-100 transition-colors">
                  <div className="mt-0.5 shrink-0">
                    {smsConsent
                      ? <CheckSquare className="h-5 w-5 text-[#0ea5e9]" onClick={() => setSmsConsent(false)} />
                      : <Square className="h-5 w-5 text-gray-300" onClick={() => setSmsConsent(true)} />}
                  </div>
                  <div onClick={() => setSmsConsent(!smsConsent)}>
                    <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-[#0ea5e9]" />
                      Receive SMS medication reminders
                    </span>
                    <span className="text-xs text-gray-500 mt-1 block">
                      Msg &amp; data rates may apply. Reply STOP to opt out.
                    </span>
                  </div>
                </label>
              </>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm text-gray-600">Email / Phone</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="h-12 rounded-xl border-gray-200 bg-gray-50/50 focus:bg-white"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm text-gray-600">Password</Label>
                {!showSignup && (
                  <button
                    type="button"
                    onClick={() => toast.info("Password reset not available in demo.")}
                    className="text-xs text-[#0ea5e9] hover:underline"
                  >
                    Reset Password
                  </button>
                )}
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="h-12 rounded-xl border-gray-200 bg-gray-50/50 focus:bg-white pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPass ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {showSignup && (
              <div className="space-y-1.5">
                <Label htmlFor="confirmPass" className="text-sm text-gray-600">Confirm Password</Label>
                <Input
                  id="confirmPass"
                  type="password"
                  value={confirmPass}
                  onChange={e => setConfirmPass(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="h-12 rounded-xl border-gray-200 bg-gray-50/50 focus:bg-white"
                />
              </div>
            )}

            {!showSignup && (
              <button
                type="button"
                onClick={() => setRemember(!remember)}
                className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700"
              >
                {remember
                  ? <CheckSquare className="h-5 w-5 text-[#0ea5e9]" />
                  : <Square className="h-5 w-5 text-gray-300" />}
                Remember me for 30 days
              </button>
            )}

            <Button
              type="submit"
              className="w-full h-12 rounded-xl bg-[#0ea5e9] hover:bg-[#0284c7] text-white font-medium"
              disabled={loading}
            >
              {loading ? "Please wait…" : (showSignup ? "Create Account" : "Login")}
            </Button>

            <Button
  variant="outline"
  className="w-full flex items-center justify-center gap-2"
  onClick={() => alert("Google login coming soon")}
>
  <svg width="18" height="18" viewBox="0 0 48 48">
    <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.1 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.1-.1-2.3-.4-3.5z"/>
    <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.6 15.4 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.1 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
    <path fill="#4CAF50" d="M24 44c5.2 0 10-2 13.6-5.2l-6.3-5.2C29.3 35.7 26.8 36 24 36c-5.3 0-9.8-3.4-11.4-8.1l-6.6 5.1C9.4 39.7 16.1 44 24 44z"/>
    <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-1.2 3.1-3.7 5.3-7 6.6l6.3 5.2C38.9 36 44 30.7 44 24c0-1.1-.1-2.3-.4-3.5z"/>
  </svg>
  Login with Google
</Button>
          </form>

          {/* Demo hint */}
          {mode === "signin" && (
            <div className="mt-6 p-4 rounded-xl bg-[#0ea5e9]/5 border border-[#0ea5e9]/20 text-sm text-gray-600">
              <strong className="text-gray-900">Demo mode.</strong> Credentials are pre-filled — just click Login.
            </div>
          )}

          <p className="text-center text-sm text-gray-400 mt-8">
            <Link href="/" className="hover:text-[#0ea5e9] transition-colors">← Back to home</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-gray-400">Loading…</div>}>
      <LoginForm />
    </Suspense>
  );
}