"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Mic, ShieldCheck, FileText, Activity,
  FlaskConical, ArrowRight, Search,
  Lock, Zap, CheckCircle2, Clock, Brain, Star,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────────────────────
   MedSift AI — Healthcare Landing Page with Circular Image Cluster
   ───────────────────────────────────────────────────────────────────────────── */

export default function HomePage() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <div className="min-h-screen bg-white text-gray-900 overflow-x-hidden">
      {/* ── NAVIGATION ─────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100">        
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center">
            <div className="h-16 w-[240px] flex items-center">
              <Image
                src="/logo.png"
                alt="MedSift AI"
                width={300}
                height={120}
                className="object-contain"
                priority
              />
            </div>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#" className="text-sm text-[#0ea5e9] font-semibold border-b-2 border-[#0ea5e9] pb-1">Home</a>
            <a href="#features" className="text-sm text-gray-600 hover:text-[#0ea5e9] transition-colors font-medium">Features</a>
            <a href="#how-it-works" className="text-sm text-gray-600 hover:text-[#0ea5e9] transition-colors font-medium">How it Works</a>
            <a href="#about" className="text-sm text-gray-600 hover:text-[#0ea5e9] transition-colors font-medium">About</a>
            <Link href="/login" className="text-sm text-gray-600 hover:text-[#0ea5e9] transition-colors font-medium">
              Login
            </Link>
          </div>
          <Link href="/login" className="hidden md:block">
            <Button className="bg-[#0ea5e9] hover:bg-[#0284c7] text-white rounded-lg px-6 h-11 font-medium">
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      {/* ── HERO SECTION ───────────────────────────────────────────────── */}
      <section className="relative min-h-screen pt-28 pb-16 overflow-hidden">
        {/* Background Decorations */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Top right corner stripes */}
          <div className="absolute top-16 right-0 w-32 h-32">
            <div className="absolute top-0 right-8 w-24 h-3 bg-[#0ea5e9] rounded-full transform rotate-[-35deg]" />
            <div className="absolute top-4 right-4 w-20 h-3 bg-[#0ea5e9]/60 rounded-full transform rotate-[-35deg]" />
            <div className="absolute top-8 right-0 w-16 h-3 bg-[#0ea5e9]/30 rounded-full transform rotate-[-35deg]" />
          </div>

          {/* Curved wave lines */}
          <svg className="absolute bottom-20 left-0 w-[400px] h-[200px] opacity-20" viewBox="0 0 400 200">
            <path d="M0 100 Q100 50 200 100 T400 100" stroke="#0ea5e9" strokeWidth="1" fill="none" />
            <path d="M0 120 Q100 70 200 120 T400 120" stroke="#0ea5e9" strokeWidth="1" fill="none" />
            <path d="M0 140 Q100 90 200 140 T400 140" stroke="#0ea5e9" strokeWidth="1" fill="none" />
          </svg>

          {/* Dot grid pattern */}
          <div className="absolute bottom-32 right-[45%] grid grid-cols-5 gap-2">
            {[...Array(15)].map((_, i) => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-[#0ea5e9]/40" />
            ))}
          </div>

          {/* Teal accent shape */}
          <div className="absolute top-1/4 right-[15%] w-16 h-16 bg-[#0ea5e9] rounded-lg transform rotate-45 opacity-10" />
        </div>

        <div className="relative max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-12 items-center min-h-[calc(100vh-180px)]">
            {/* Left Column - Text */}
            <div className={`transition-all duration-1000 ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
              <h1 className="text-5xl sm:text-6xl lg:text-[68px] font-bold leading-[1.1] mb-6 text-gray-900">
                AI-Powered{" "}
                <span className="text-[#0ea5e9]">Medical</span>{" "}
                Intelligence
              </h1>

              <p className="text-lg text-gray-600 leading-relaxed mb-8 max-w-md">
                Transform patient-doctor conversations into structured SOAP notes, 
                care plans, and risk assessments—fully local, zero cloud, HIPAA-aware.
              </p>

              <div className="flex flex-wrap items-center gap-4 mb-10">
                <Link href="/login">
                  <Button size="lg" className="bg-[#0ea5e9] hover:bg-[#0284c7] text-white rounded-lg h-14 px-8 text-base font-semibold gap-2 group">
                    Get Started
                    <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </Link>
                <Button size="lg" variant="outline" className="rounded-lg h-14 px-8 border-gray-300 hover:border-[#0ea5e9] hover:text-[#0ea5e9] font-medium">
                  Learn More
                </Button>
              </div>

              {/* Stats removed - now shown in floating tiles */}
            </div>

            {/* Right Column - Circular Images Cluster with Floating Tiles */}
            <div className={`relative transition-all duration-1000 delay-300 ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
              <div className="relative w-full h-[550px] lg:h-[600px]">
                {/* Large circle - top right */}
                <div className="absolute top-0 right-0 w-[280px] h-[280px] lg:w-[320px] lg:h-[320px]">
                  <div className="absolute inset-0 rounded-full border-4 border-[#0ea5e9] p-1">
                    <div className="w-full h-full rounded-full overflow-hidden">
                      <img
                        src="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=400&h=400&fit=crop&crop=face"
                        alt="Doctor"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </div>
                </div>

                {/* Medium circle - bottom right */}
                <div className="absolute bottom-8 right-4 w-[220px] h-[220px] lg:w-[260px] lg:h-[260px]">
                  <div className="absolute inset-0 rounded-full border-4 border-[#0ea5e9] p-1">
                    <div className="w-full h-full rounded-full overflow-hidden">
                      <img
                        src="https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=400&h=400&fit=crop&crop=face"
                        alt="Healthcare professional"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </div>
                </div>

                {/* Small circle - left */}
                <div className="absolute top-1/3 left-0 w-[180px] h-[180px] lg:w-[200px] lg:h-[200px]">
                  <div className="absolute inset-0 rounded-full border-4 border-[#0ea5e9] p-1">
                    <div className="w-full h-full rounded-full overflow-hidden">
                      <img
                        src="https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=400&h=400&fit=crop&crop=face"
                        alt="Medical equipment"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </div>
                </div>

                {/* ═══ FLOATING TILES - Teal Glass Effect ═══ */}
                
                {/* Tile 1: 100% Local - Top left */}
                <div className="absolute top-12 left-[8%] backdrop-blur-xl bg-[#0ea5e9]/20 rounded-2xl px-4 py-3 shadow-lg border border-[#0ea5e9]/30 z-20 animate-[fadeInUp_0.6s_ease_0.3s_both]">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-white/80 flex items-center justify-center">
                      <Lock className="h-5 w-5 text-[#0ea5e9]" />
                    </div>
                    <div>
                      <p className="text-lg font-bold text-gray-900">100%</p>
                      <p className="text-xs text-gray-600">Local Processing</p>
                    </div>
                  </div>
                </div>

                {/* Tile 2: <30s Processing - Top right, outside images */}
                <div className="absolute top-4 -right-16 backdrop-blur-xl bg-[#0ea5e9]/20 rounded-2xl px-4 py-3 shadow-lg border border-[#0ea5e9]/30 z-20 animate-[fadeInUp_0.6s_ease_0.5s_both]">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-white/80 flex items-center justify-center">
                      <Clock className="h-5 w-5 text-[#0ea5e9]" />
                    </div>
                    <div>
                      <p className="text-lg font-bold text-gray-900">&lt;30s</p>
                      <p className="text-xs text-gray-600">Processing Time</p>
                    </div>
                  </div>
                </div>

                {/* Tile 3: 50+ PHI Types - Bottom middle */}
                <div className="absolute bottom-[25%] left-[20%] backdrop-blur-xl bg-[#0ea5e9]/20 rounded-2xl px-4 py-3 shadow-lg border border-[#0ea5e9]/30 z-20 animate-[fadeInUp_0.6s_ease_0.7s_both]">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-white/80 flex items-center justify-center">
                      <ShieldCheck className="h-5 w-5 text-[#0ea5e9]" />
                    </div>
                    <div>
                      <p className="text-lg font-bold text-gray-900">50+</p>
                      <p className="text-xs text-gray-600">PHI Types Detected</p>
                    </div>
                  </div>
                </div>

                {/* Decorative elements */}
                {/* Cyan filled circle decoration */}
                <div className="absolute top-[15%] left-[35%] w-8 h-8 bg-[#0ea5e9] rounded-full opacity-20" />

                {/* Small dots cluster */}
                <div className="absolute bottom-[30%] left-[25%] grid grid-cols-3 gap-1.5">
                  {[...Array(9)].map((_, i) => (
                    <div key={i} className="w-2 h-2 rounded-full bg-[#0ea5e9]/50" />
                  ))}
                </div>

                {/* Ring decoration */}
                <div className="absolute top-[60%] right-[35%] w-8 h-8 rounded-full border-4 border-[#0ea5e9]/30" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES SECTION ───────────────────────────────────────────── */}
      <section id="features" className="py-24 bg-[#f8fcfc]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold mb-4">
              Complete <span className="text-[#0ea5e9]">Pipeline</span>
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto text-lg">
              Five specialized modules working together to transform audio into actionable care plans.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Mic, title: "Voice Capture", desc: "Record directly in browser or upload audio files. Supports MP3, WAV, M4A, and WebM.", color: "#0ea5e9" },
              { icon: ShieldCheck, title: "PHI Protection", desc: "Microsoft Presidio automatically redacts 50+ identifier types before AI processing.", color: "#10b981" },
              { icon: FileText, title: "Care Plans & SOAP", desc: "Generate structured SOAP notes and patient-friendly summaries with evidence quotes.", color: "#8b5cf6" },
              { icon: FlaskConical, title: "Clinical Trials", desc: "Auto-match patient conditions to actively recruiting ClinicalTrials.gov studies.", color: "#f59e0b" },
              { icon: Search, title: "PubMed Search", desc: "Find relevant peer-reviewed research papers ranked by citation impact.", color: "#06b6d4" },
            ].map((feature) => (
              <Card key={feature.title} className="border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-white">
                <CardContent className="p-6">
                  <div 
                    className="h-14 w-14 rounded-2xl flex items-center justify-center mb-5"
                    style={{ background: `${feature.color}15` }}
                  >
                    <feature.icon className="h-7 w-7" style={{ color: feature.color }} />
                  </div>
                  <h3 className="text-lg font-bold mb-2 text-gray-900">{feature.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{feature.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold mb-4">
              How It <span className="text-[#0ea5e9]">Works</span>
            </h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              Our five-stage pipeline processes your audio entirely on-device in under 30 seconds.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              { num: "01", icon: Mic, title: "Record", desc: "Capture the conversation using browser microphone or upload audio" },
              { num: "02", icon: Brain, title: "Transcribe", desc: "OpenAI Whisper converts speech to text on your device" },
              { num: "03", icon: ShieldCheck, title: "Protect", desc: "Microsoft Presidio redacts all PHI before AI processing" },
              { num: "04", icon: FileText, title: "Extract", desc: "LLaMA 3 structures medications, tests, and SOAP notes" },
              { num: "05", icon: CheckCircle2, title: "Deliver", desc: "Care plan ready for clinician review and patient access" },
            ].map((step) => (
              <div key={step.num} className="relative p-6 rounded-2xl border border-gray-100 hover:border-[#0ea5e9]/50 hover:shadow-lg transition-all group bg-white">
                <span className="absolute top-6 right-6 text-5xl font-bold text-gray-100 group-hover:text-[#0ea5e9]/20 transition-colors">
                  {step.num}
                </span>
                <div className="h-12 w-12 rounded-xl bg-[#0ea5e9]/10 flex items-center justify-center mb-4 group-hover:bg-[#0ea5e9] transition-colors">
                  <step.icon className="h-6 w-6 text-[#0ea5e9] group-hover:text-white transition-colors" />
                </div>
                <h3 className="font-bold text-lg text-gray-900 mb-2">{step.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ABOUT / SECURITY ───────────────────────────────────────────── */}
      <section id="about" className="py-24 bg-[#f8fcfc]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-4xl sm:text-5xl font-bold mb-6">
                Your Data <span className="text-[#0ea5e9]">Never Leaves</span> Your Machine
              </h2>
              <p className="text-gray-600 text-lg leading-relaxed mb-8">
                Every stage of processing happens locally. No cloud APIs, no data transfer, 
                no privacy concerns. Your patients&apos; information stays where it belongs.
              </p>

              <div className="grid grid-cols-2 gap-4">
                {[
                  { icon: Lock, label: "100% Local Processing" },
                  { icon: ShieldCheck, label: "HIPAA-Aware Design" },
                  { icon: Clock, label: "30-Second Processing" },
                  { icon: Zap, label: "Zero API Costs" },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-3 p-4 rounded-xl bg-white border border-gray-100">
                    <div className="h-10 w-10 rounded-lg bg-[#0ea5e9]/10 flex items-center justify-center shrink-0">
                      <item.icon className="h-5 w-5 text-[#0ea5e9]" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-4">
                  <div className="rounded-2xl overflow-hidden h-48">
                    <img src="https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?w=400&h=300&fit=crop" alt="Medical" className="w-full h-full object-cover" />
                  </div>
                  <div className="rounded-2xl overflow-hidden h-56">
                    <img src="https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&h=350&fit=crop" alt="Healthcare" className="w-full h-full object-cover" />
                  </div>
                </div>
                <div className="space-y-4 pt-8">
                  <div className="rounded-2xl overflow-hidden h-56">
                    <img src="https://images.unsplash.com/photo-1584982751601-97dcc096659c?w=400&h=350&fit=crop" alt="Medical team" className="w-full h-full object-cover" />
                  </div>
                  <div className="rounded-2xl bg-[#0ea5e9] p-6 text-white h-48 flex flex-col justify-center">
                    <div className="text-4xl font-bold mb-2">50+</div>
                    <div className="text-white/80">PHI types detected automatically</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ───────────────────────────────────────────────── */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold">
              Trusted by <span className="text-[#0ea5e9]">Clinicians</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              { quote: "Finally, a solution that keeps patient data where it belongs—on our own systems.", author: "Dr. Sarah Chen", role: "Chief Medical Officer" },
              { quote: "The AI-generated SOAP notes save me 20 minutes per patient. Game changer.", author: "Dr. Michael Torres", role: "Family Medicine" },
              { quote: "Risk scoring helps me prioritize which patients need immediate follow-up.", author: "Dr. Emily Parker", role: "Internal Medicine" },
            ].map((t, i) => (
              <Card key={i} className="border border-gray-100 shadow-sm hover:shadow-lg transition-shadow bg-white">
                <CardContent className="p-6">
                  <div className="flex gap-1 mb-4">
                    {[...Array(5)].map((_, j) => (
                      <Star key={j} className="h-5 w-5 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="text-gray-700 mb-6 leading-relaxed">&quot;{t.quote}&quot;</p>
                  <div className="flex items-center gap-3">
                    <div className="h-11 w-11 rounded-full bg-gradient-to-br from-[#0ea5e9] to-[#06b6d4] flex items-center justify-center text-sm font-bold text-white">
                      {t.author.split(" ").map(n => n[0]).join("")}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{t.author}</p>
                      <p className="text-sm text-gray-500">{t.role}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────── */}
      <section className="py-24 bg-[#0ea5e9]">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-4xl sm:text-5xl font-bold text-white mb-6">
            Ready to transform your practice?
          </h2>
          <p className="text-white/80 text-lg mb-10 max-w-2xl mx-auto">
            Join clinicians saving hours every day with AI-powered documentation.
          </p>
          <Link href="/login">
            <Button size="lg" className="bg-white text-[#0ea5e9] hover:bg-gray-100 rounded-lg h-14 px-10 text-base font-semibold gap-2 group shadow-xl">
              Get Started Free
              <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────── */}
      <footer className="py-12 bg-white border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <Image src="/logo.png" alt="MedSift AI" width={150} height={40} className="h-10 w-auto object-contain" />
            <div className="flex items-center gap-8 text-sm text-gray-500">
              <a href="#features" className="hover:text-[#0ea5e9] transition-colors">Features</a>
              <a href="#how-it-works" className="hover:text-[#0ea5e9] transition-colors">How it Works</a>
              <a href="#about" className="hover:text-[#0ea5e9] transition-colors">About</a>
            </div>
            <p className="text-sm text-gray-500">© 2026 MedSift AI · Hacklytics @ Georgia Tech</p>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-100">
            <p className="text-xs text-gray-400 text-center max-w-2xl mx-auto">
              <strong>Disclaimer:</strong> MedSift AI is for informational purposes only. It does not provide medical diagnoses.
            </p>
          </div>
        </div>
      </footer>

      {/* Animation keyframes */}
      <style jsx global>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}