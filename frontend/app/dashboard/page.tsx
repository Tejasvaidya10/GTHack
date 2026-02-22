"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getVisits, getAnalytics } from "@/lib/api";
import {
  Activity, FileText, BarChart3,
  Calendar, ArrowRight, TrendingUp, AlertTriangle, CheckCircle2,
  Upload, Clock, Pill, Bell, MessageSquare, PhoneOff,
} from "lucide-react";
import type { VisitRecord, AnalyticsSummary, AuthUser } from "@/types";
import { toast } from "sonner";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [visits, setVisits] = useState<VisitRecord[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingIds, setPendingIds] = useState<number[]>([]);
  const [approvedIds, setApprovedIds] = useState<number[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    if (!stored) { router.push("/login"); return; }
    const u = JSON.parse(stored) as AuthUser;
    setUser(u);

    const pending = JSON.parse(localStorage.getItem("medsift_pending") || "[]") as number[];
    const approved = JSON.parse(localStorage.getItem("medsift_approvals") || "[]") as number[];
    setPendingIds(pending);
    setApprovedIds(approved);

    async function load() {
      try {
        const [v, a] = await Promise.all([
          getVisits({ sort: "date" }),
          getAnalytics().catch(() => null),
        ]);
        setVisits(v);
        setAnalytics(a);
      } catch {
        // no-op — visits may be empty on first run
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  const isClinician = user?.role === "clinician";

  const visibleVisits = isClinician
    ? visits
    : visits.filter(v => approvedIds.includes(v.id) || !pendingIds.includes(v.id));

  const recentVisits = visibleVisits.slice(0, 5);

  const approveVisit = (visitId: number) => {
    const newApproved = [...approvedIds, visitId];
    const newPending = pendingIds.filter(id => id !== visitId);
    setApprovedIds(newApproved);
    setPendingIds(newPending);
    localStorage.setItem("medsift_approvals", JSON.stringify(newApproved));
    localStorage.setItem("medsift_pending", JSON.stringify(newPending));
    toast.success("Visit approved — now visible in patient portal");
  };

  return (
    <div className="p-6 lg:p-8 w-full max-w-screen-xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">
          {loading ? "Loading..." : `Welcome back, ${user?.name ?? "User"}`}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          {isClinician ? "Here's your clinical overview." : "Here's your health summary."}
        </p>
      </div>

      {/* Pending approvals banner */}
      {isClinician && pendingIds.length > 0 && (
        <div className="mb-6 flex items-start gap-3 p-4 rounded-xl border bg-amber-50 border-amber-200">
          <Bell className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-sm text-amber-800">
              {pendingIds.length} visit{pendingIds.length > 1 ? "s" : ""} awaiting approval
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              Review and approve before patients can view them.
            </p>
          </div>
          <Link href="/visits">
            <Button size="sm" className="bg-amber-600 hover:bg-amber-700 text-white gap-1.5 text-xs">
              Review <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      )}

      {/* Stats row — different layout for clinician vs patient */}
      {isClinician ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Total Visits</p>
                  <p className="text-2xl font-bold mt-1">{loading ? "—" : analytics?.total_visits ?? visits.length}</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Pending Approvals</p>
                  <p className="text-2xl font-bold mt-1 text-amber-600">{loading ? "—" : pendingIds.length}</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-amber-50 flex items-center justify-center">
                  <Bell className="h-5 w-5 text-amber-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Pending</p>
                  <p className="text-2xl font-bold mt-1 text-amber-600">{pendingIds.length}</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-amber-50 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-amber-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        /* Patient stat cards */
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">My Visits</p>
                  <p className="text-2xl font-bold mt-1">{loading ? "—" : visibleVisits.length}</p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">Medications</p>
                  <p className="text-2xl font-bold mt-1">
                    {loading ? "—" : visibleVisits.reduce((sum, v) => sum + (v.patient_summary?.medications?.length ?? 0), 0)}
                  </p>
                </div>
                <div className="h-10 w-10 rounded-xl bg-blue-50 flex items-center justify-center">
                  <Pill className="h-5 w-5 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="col-span-2 lg:col-span-1">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground font-medium">SMS Reminders</p>
                  <p className="text-sm font-bold mt-1">
                    {user?.sms_consent
                      ? <span className="text-green-600">Active</span>
                      : <span className="text-slate-400">Not set up</span>}
                  </p>
                </div>
                <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${user?.sms_consent ? "bg-green-50" : "bg-slate-100"}`}>
                  {user?.sms_consent
                    ? <MessageSquare className="h-5 w-5 text-green-600" />
                    : <PhoneOff className="h-5 w-5 text-slate-400" />}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Quick action — single upload button for clinician */}
      {isClinician && (
        <div className="mb-8">
          <Link href="/upload">
            <Card className="border-dashed border-2 border-primary/20 hover:border-primary/40 hover:bg-primary/[0.02] transition-colors cursor-pointer">
              <CardContent className="p-5 flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Upload className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="font-semibold text-sm">Upload or Record Audio</p>
                  <p className="text-xs text-muted-foreground">Upload an audio file or start a live recording to begin analysis</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground ml-auto" />
              </CardContent>
            </Card>
          </Link>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {/* Recent visits */}
        <div className="lg:col-span-2 xl:col-span-3">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-sm">{isClinician ? "Recent Visits" : "My Recent Visits"}</h2>
            <Link href="/visits" className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
            </div>
          ) : recentVisits.length === 0 ? (
            <Card className="py-12 text-center">
              <CardContent>
                {isClinician ? (
                  <>
                    <p className="text-muted-foreground text-sm mb-4">No visits yet.</p>
                    <Link href="/upload"><Button size="sm">Upload First Recording</Button></Link>
                  </>
                ) : (
                  <>
                    <p className="text-muted-foreground text-sm mb-2">No approved visit summaries yet.</p>
                    <p className="text-xs text-muted-foreground">Your clinician will approve your summaries before they appear here.</p>
                  </>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {recentVisits.map(visit => {
                const isPending = pendingIds.includes(visit.id);
                const firstMed = visit.patient_summary?.medications?.[0];
                const summary = visit.patient_summary?.visit_summary;

                return (
                  <Card key={visit.id} className={isPending ? "border-amber-200 bg-amber-50/30" : ""}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex items-start gap-3">
                          <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                            <Activity className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-sm capitalize">{visit.visit_type}</p>
                              {isPending && (
                                <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-[10px]">
                                  Pending
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                              <Calendar className="h-3 w-3" />
                              {new Date(visit.visit_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                            </p>
                          </div>
                        </div>
                      </div>

                      {summary && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mb-2 ml-12">{summary}</p>
                      )}

                      {firstMed && (
                        <div className="ml-12 flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Pill className="h-3 w-3 text-blue-500" />
                          <span>{firstMed.name} {firstMed.dose}</span>
                          {(visit.patient_summary?.medications?.length ?? 0) > 1 && (
                            <span className="text-muted-foreground/60">+{(visit.patient_summary?.medications?.length ?? 1) - 1} more</span>
                          )}
                        </div>
                      )}

                      {isClinician && isPending ? (
                        <div className="mt-3 ml-12 flex gap-2">
                          <Button
                            size="sm"
                            className="h-7 text-xs gap-1.5 bg-green-600 hover:bg-green-700 text-white"
                            onClick={() => approveVisit(visit.id)}
                          >
                            <CheckCircle2 className="h-3 w-3" /> Approve
                          </Button>
                          <Link href={`/visits/${visit.id}`}>
                            <Button size="sm" variant="outline" className="h-7 text-xs">Review</Button>
                          </Link>
                        </div>
                      ) : (
                        <Link href={`/visits/${visit.id}`} className="ml-12 mt-2 block">
                          <span className="text-xs text-primary hover:underline flex items-center gap-1">
                            View details <ArrowRight className="h-3 w-3" />
                          </span>
                        </Link>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Sidebar stats */}
        <div className="space-y-4">
          {analytics && (
            <>
              {/* Top conditions */}
              {analytics.top_conditions && analytics.top_conditions.length > 0 && isClinician && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Top Conditions</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {analytics.top_conditions.slice(0, 5).map((c, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground text-xs truncate">{c.condition}</span>
                        <Badge variant="outline" className="text-[10px] ml-2">{c.count}</Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* Learning loop */}
          {analytics?.top_boosted_keywords && analytics.top_boosted_keywords.length > 0 && isClinician && (
            <Card className="bg-blue-50 border-blue-100">
              <CardContent className="p-4 flex gap-3">
                <TrendingUp className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-blue-700">Learning loop active</p>
                  <p className="text-[11px] text-blue-600 mt-0.5">
                    {analytics.top_boosted_keywords.length} keywords boosted from feedback.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Quick links (clinician only) */}
          {isClinician && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Quick Links</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <Link href="/analytics" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground py-1.5 transition-colors">
                  <BarChart3 className="h-3.5 w-3.5" /> View Analytics
                </Link>
                <Link href="/visits" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground py-1.5 transition-colors">
                  <FileText className="h-3.5 w-3.5" /> All Visits
                </Link>
              </CardContent>
            </Card>
          )}

          {/* Patient: SMS reminders card */}
          {!isClinician && (
            <Card className={user?.sms_consent ? "border-green-200 bg-green-50/40" : "border-slate-200 bg-slate-50/60"}>
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 ${user?.sms_consent ? "bg-green-100" : "bg-slate-200"}`}>
                    <MessageSquare className={`h-4 w-4 ${user?.sms_consent ? "text-green-600" : "text-slate-400"}`} />
                  </div>
                  <div>
                    <p className={`text-sm font-semibold ${user?.sms_consent ? "text-green-800" : "text-slate-600"}`}>
                      {user?.sms_consent ? "SMS Reminders Active" : "SMS Reminders Off"}
                    </p>
                    {user?.sms_consent ? (
                      <>
                        <p className="text-[11px] text-green-700 mt-0.5 leading-relaxed">
                          You&apos;ll receive medication reminders at{" "}
                          <span className="font-semibold">{user.phone ?? "your registered number"}</span>.
                        </p>
                        <p className="text-[10px] text-green-600/70 mt-1">Reply STOP to any message to opt out.</p>
                      </>
                    ) : (
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                        Enable SMS reminders during sign-up to get medication alerts sent to your phone.
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Patient: quick links */}
          {!isClinician && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Quick Links</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <Link href="/medications" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground py-1.5 transition-colors">
                  <Pill className="h-3.5 w-3.5" /> My Medications
                </Link>
                <Link href="/visits" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground py-1.5 transition-colors">
                  <FileText className="h-3.5 w-3.5" /> All Visits
                </Link>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
