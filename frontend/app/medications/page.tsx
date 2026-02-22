"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getVisits } from "@/lib/api";
import {
  Pill, Clock, RefreshCw, Search, ChevronRight,
  CheckCircle2, XCircle, AlertCircle, Calendar,
} from "lucide-react";
import type { Medication, VisitRecord, AuthUser } from "@/types";

interface MedEntry {
  med: Medication;
  visitId: number;
  visitDate: string;
  visitType: string;
  status: "active" | "review" | "stopped";
}

function inferStatus(med: Medication): "active" | "review" | "stopped" {
  // Use the status field from the medication if available
  if (med.status) return med.status;
  
  // Fallback to inferring from duration
  const d = (med.duration || "").toLowerCase();
  if (!d || d === "ongoing" || d.includes("indefinitely") || d.includes("long-term")) return "active";
  if (d.includes("discontinu") || d.includes("stopped") || d.includes("completed")) return "stopped";
  // if duration looks like "X days / weeks" parse roughly
  const match = d.match(/(\d+)\s*(day|week|month)/);
  if (match) {
    return "active"; // short-term but still active
  }
  return "review";
}

const STATUS_STYLES = {
  active:  { bg: "bg-green-50 border-green-200",  text: "text-green-700",  dot: "bg-green-500",  label: "Active"  },
  review:  { bg: "bg-amber-50 border-amber-200",  text: "text-amber-700",  dot: "bg-amber-500",  label: "Review"  },
  stopped: { bg: "bg-red-50 border-red-200",      text: "text-red-700",    dot: "bg-red-500",    label: "Stopped" },
};

const FILTER_TABS = ["All", "Active", "Review", "Stopped"] as const;
type FilterTab = typeof FILTER_TABS[number];

export default function MedicationsPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [entries, setEntries] = useState<MedEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<FilterTab>("All");

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    if (!stored) { router.push("/login"); return; }
    setUser(JSON.parse(stored));

    const approvals = JSON.parse(localStorage.getItem("medsift_approvals") || "[]") as number[];
    const pending   = JSON.parse(localStorage.getItem("medsift_pending")   || "[]") as number[];

    async function load() {
      try {
        const visits: VisitRecord[] = await getVisits({ sort: "date" });
        const all: MedEntry[] = [];
        for (const v of visits) {
          const isApproved = approvals.includes(v.id) || !pending.includes(v.id);
          if (!isApproved) continue;
          const meds = v.patient_summary?.medications ?? [];
          for (const med of meds) {
            all.push({
              med,
              visitId: v.id,
              visitDate: v.visit_date,
              visitType: v.visit_type,
              status: inferStatus(med),
            });
          }
        }
        setEntries(all);
      } catch {
        // backend may not be up — show empty state
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      const matchTab =
        activeTab === "All" ? true :
        activeTab === "Active"  ? e.status === "active" :
        activeTab === "Review"  ? e.status === "review" :
        activeTab === "Stopped" ? e.status === "stopped" :
        true;
      const q = search.toLowerCase();
      const matchSearch = !q ||
        e.med.name.toLowerCase().includes(q) ||
        e.med.dose.toLowerCase().includes(q) ||
        e.visitType.toLowerCase().includes(q);
      return matchTab && matchSearch;
    });
  }, [entries, activeTab, search]);

  const counts = useMemo(() => ({
    All:     entries.length,
    Active:  entries.filter(e => e.status === "active").length,
    Review:  entries.filter(e => e.status === "review").length,
    Stopped: entries.filter(e => e.status === "stopped").length,
  }), [entries]);

  return (
    <div className="min-h-screen p-6 sm:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="h-10 w-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center">
            <Pill className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-900">Medications</h1>
            <p className="text-sm text-slate-500">Your complete medication history across all visits</p>
          </div>
        </div>
      </div>

      {/* Stats row */}
      {!loading && entries.length > 0 && (
        <div className="grid grid-cols-4 gap-3 mb-7">
          {[
            { label: "Total",      value: counts.All,     icon: Pill,          color: "text-blue-600",   bg: "bg-blue-50 border-blue-100"  },
            { label: "Active",     value: counts.Active,  icon: CheckCircle2,  color: "text-green-600",  bg: "bg-green-50 border-green-100" },
            { label: "For Review", value: counts.Review,  icon: AlertCircle,   color: "text-amber-600",  bg: "bg-amber-50 border-amber-100" },
            { label: "Stopped",    value: counts.Stopped, icon: XCircle,       color: "text-red-600",    bg: "bg-red-50 border-red-100" },
          ].map(s => (
            <div key={s.label} className={`rounded-xl border p-4 flex items-center gap-3 ${s.bg}`}>
              <s.icon className={`h-5 w-5 shrink-0 ${s.color}`} />
              <div>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs text-slate-500">{s.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Search + filter */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search medications…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
          />
        </div>
        <div className="flex gap-1 p-1 bg-slate-100 rounded-xl">
          {FILTER_TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === tab
                  ? "bg-white shadow text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {tab}
              {counts[tab] > 0 && (
                <span className={`ml-1.5 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  activeTab === tab ? "bg-blue-100 text-blue-700" : "bg-slate-200 text-slate-500"
                }`}>{counts[tab]}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-2xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          {entries.length === 0 ? (
            <>
              <div className="h-16 w-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-4">
                <Pill className="h-8 w-8 text-blue-300" />
              </div>
              <p className="text-slate-600 font-semibold mb-1">No medications yet</p>
              <p className="text-sm text-slate-400 max-w-xs">
                Medications will appear here once your clinician processes and approves a visit summary.
              </p>
            </>
          ) : (
            <>
              <XCircle className="h-10 w-10 text-slate-300 mb-3" />
              <p className="text-slate-500 text-sm">No medications match your search or filter.</p>
              <button onClick={() => { setSearch(""); setActiveTab("All"); }}
                className="mt-2 text-xs text-blue-600 hover:underline flex items-center gap-1">
                <RefreshCw className="h-3 w-3" /> Clear filters
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((entry, idx) => {
            const s = STATUS_STYLES[entry.status];
            return (
              <div
                key={idx}
                className={`rounded-2xl border p-5 transition-all hover:shadow-md ${s.bg}`}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: drug info */}
                  <div className="flex items-start gap-4 min-w-0">
                    {/* Icon */}
                    <div className="h-11 w-11 rounded-xl bg-white border border-slate-100 shadow-sm flex items-center justify-center shrink-0">
                      <Pill className="h-5 w-5 text-blue-500" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="font-bold text-slate-900 text-base">{entry.med.name}</h3>
                        <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${s.text}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                          {s.label}
                        </span>
                      </div>

                      {/* Dosage pills */}
                      <div className="flex flex-wrap gap-2 mb-2">
                        {entry.med.dose && (
                          <span className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-lg font-medium">
                            <span className="text-[10px] text-slate-400 uppercase font-bold">Dose</span>
                            {entry.med.dose}
                          </span>
                        )}
                        {entry.med.frequency && (
                          <span className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-lg font-medium">
                            <Clock className="h-3 w-3 text-slate-400" />
                            {entry.med.frequency}
                          </span>
                        )}
                        {entry.med.duration && (
                          <span className="inline-flex items-center gap-1 text-xs bg-white border border-slate-200 text-slate-700 px-2.5 py-1 rounded-lg font-medium">
                            <span className="text-[10px] text-slate-400 uppercase font-bold">Duration</span>
                            {entry.med.duration}
                          </span>
                        )}
                      </div>

                      {entry.med.instructions && (
                        <p className="text-xs text-slate-500 italic leading-relaxed line-clamp-2">
                          {entry.med.instructions}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Right: visit link */}
                  <div className="shrink-0 text-right">
                    <div className="flex items-center gap-1 text-xs text-slate-400 mb-2 justify-end">
                      <Calendar className="h-3 w-3" />
                      {new Date(entry.visitDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </div>
                    <Badge variant="outline" className="text-[10px] text-slate-500 border-slate-200 mb-2">
                      {entry.visitType}
                    </Badge>
                    <Link href={`/visits/${entry.visitId}`}>
                      <Button variant="ghost" size="sm"
                        className="h-7 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 gap-1 flex items-center">
                        View visit <ChevronRight className="h-3 w-3" />
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}