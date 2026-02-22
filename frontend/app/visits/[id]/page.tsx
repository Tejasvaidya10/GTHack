"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getVisit, submitFeedback, exportPDF, downloadPDF, getLiterature, getTrials, getGrounding
} from "@/lib/api";
import {
  ArrowLeft, Download, BookOpen, CheckCircle2, XCircle,
  ThumbsUp, ThumbsDown, AlertTriangle, Calendar, Clock,
  ShieldCheck, Bell, FileText, Pill, Stethoscope,
  Printer, Share2,
} from "lucide-react";
import { toast } from "sonner";
import type { VisitRecord, LiteratureResult, ClinicalTrial, AuthUser, GroundingReport } from "@/types";

export default function VisitDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const visitId = Number(id);

  const [visit, setVisit] = useState<VisitRecord | null>(null);
  const [literature, setLiterature] = useState<LiteratureResult[]>([]);
  const [trials, setTrials] = useState<ClinicalTrial[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"patient" | "soap" | "research" | "transcript">("patient");
  const [feedback, setFeedback] = useState<Record<string, "correct" | "incorrect" | "relevant" | "not_relevant">>({});
  const [exportLoading, setExportLoading] = useState(false);
  const [grounding, setGrounding] = useState<GroundingReport | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [isApproved, setIsApproved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    if (stored) setUser(JSON.parse(stored));

    const pending = JSON.parse(localStorage.getItem("medsift_pending") || "[]") as number[];
    const approved = JSON.parse(localStorage.getItem("medsift_approvals") || "[]") as number[];
    setIsPending(pending.includes(visitId));
    setIsApproved(approved.includes(visitId) || !pending.includes(visitId));

    async function load() {
      try {
        const [v, lit, tri, gr] = await Promise.all([
          getVisit(visitId),
          getLiterature(visitId).catch(() => []),
          getTrials(visitId).catch(() => []),
          getGrounding(visitId).catch(() => null),
        ]);
        setVisit(v);
        setLiterature(lit);
        setTrials(tri);
        setGrounding(gr);
      } catch {
        router.push("/visits");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [visitId, router]);

  const isClinician = user?.role === "clinician";

  const approveVisit = () => {
    const pending = JSON.parse(localStorage.getItem("medsift_pending") || "[]") as number[];
    const approved = JSON.parse(localStorage.getItem("medsift_approvals") || "[]") as number[];
    const newApproved = [...approved, visitId];
    const newPending = pending.filter(id => id !== visitId);
    localStorage.setItem("medsift_approvals", JSON.stringify(newApproved));
    localStorage.setItem("medsift_pending", JSON.stringify(newPending));
    setIsApproved(true);
    setIsPending(false);
    toast.success("Visit approved — now visible in patient portal");
  };

  const sendFeedback = async (
    key: string,
    itemType: string,
    itemValue: string,
    rating: string,
    feedbackType: "extraction_accuracy" | "literature_relevance",
    paperUrl?: string
  ) => {
    setFeedback(f => ({ ...f, [key]: rating as never }));
    try {
      await submitFeedback({
        visit_id: visitId,
        feedback_type: feedbackType,
        item_type: itemType,
        item_value: itemValue,
        rating: rating as never,
        paper_url: paperUrl,
      });
      toast.success("Feedback recorded");
    } catch {
      toast.error("Feedback failed");
    }
  };

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const blob = await exportPDF(visitId);
      downloadPDF(blob, `visit-${visitId}-summary.pdf`);
      toast.success("PDF downloaded successfully!");
    } catch {
      toast.error("PDF export failed. Please try again.");
    } finally {
      setExportLoading(false);
    }
  };

  const handlePrint = () => window.print();

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Visit Summary — ${visit?.visit_type}`,
          text: `My visit summary from ${new Date(visit?.visit_date || "").toLocaleDateString()}`,
          url: window.location.href,
        });
      } catch {
        // user cancelled
      }
    } else {
      await navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied to clipboard!");
    }
  };

  // ── Loading skeleton ─────────────────────────────────────────
  if (loading) return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-4">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );

  if (!visit) return null;

  // ── Tabs (no Risk Assessment tab) ───────────────────────────
  const clinicianTabs = [
    { key: "patient",    label: "Patient Summary", icon: FileText    },
    { key: "soap",       label: "SOAP Note",        icon: Stethoscope },
    { key: "research",   label: "Research",          icon: BookOpen    },
    { key: "transcript", label: "Transcript",        icon: FileText    },
  ] as const;

  const patientTabs = [
    { key: "patient", label: "My Summary", icon: FileText },
  ] as const;

  const tabs = isClinician ? clinicianTabs : patientTabs;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

      {/* ── Header ───────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div className="flex items-start gap-3">
          <Link href="/visits">
            <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold capitalize">{visit.visit_type}</h1>
              {isPending && (
                <Badge className="bg-amber-100 text-amber-700 border-amber-300">Pending Approval</Badge>
              )}
              {isApproved && !isPending && (
                <Badge className="bg-green-100 text-green-700 border-green-300 gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Approved
                </Badge>
              )}
              {grounding && (
                <Badge className={
                  grounding.overall_score >= 75 ? "bg-green-100 text-green-700 border-green-300 gap-1" :
                  grounding.overall_score >= 50 ? "bg-yellow-100 text-yellow-700 border-yellow-300 gap-1" :
                  "bg-red-100 text-red-700 border-red-300 gap-1"
                } title={grounding.grounded_count + " of " + grounding.total_items + " items grounded in transcript"}>
                  {grounding.overall_score >= 75 ? "✓" : grounding.overall_score >= 50 ? "~" : "⚠"} {grounding.overall_score}% Grounded
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {new Date(visit.visit_date).toLocaleDateString("en-US", {
                  month: "long", day: "numeric", year: "numeric",
                })}
              </span>
              {visit.audio_duration_seconds && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {(visit.audio_duration_seconds / 60).toFixed(1)} min
                </span>
              )}
            </div>
            <div className="flex gap-1 mt-2 flex-wrap">
              {visit.tags?.map(t => <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {!isClinician && isApproved && !isPending && (
            <div className="flex gap-2">
              <Button
                onClick={handleExport}
                disabled={exportLoading}
                className="gap-2 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white shadow-lg"
              >
                <Download className="h-4 w-4" />
                {exportLoading ? "Generating…" : "Download PDF"}
              </Button>
              <Button variant="outline" size="icon" onClick={handlePrint} title="Print">
                <Printer className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={handleShare} title="Share">
                <Share2 className="h-4 w-4" />
              </Button>
            </div>
          )}
          {isClinician && (
            <>
              <Button variant="outline" size="sm" onClick={handleExport} disabled={exportLoading} className="gap-1.5">
                <Download className="h-4 w-4" />{exportLoading ? "…" : "PDF"}
              </Button>
              <Link href={`/literature/${visitId}`}>
                <Button size="sm" className="gap-1.5">
                  <BookOpen className="h-4 w-4" /> Research
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>

      {/* ── Clinician approval banner ─────────────────────────── */}
      {isClinician && isPending && (
        <div className="mb-6 rounded-2xl border bg-amber-50 border-amber-300 overflow-hidden">
          <div className="flex items-start gap-3 p-4">
            <Bell className="h-5 w-5 text-amber-600 shrink-0 mt-0.5 animate-pulse" />
            <div className="flex-1">
              <p className="font-semibold text-amber-800">This visit needs your approval</p>
              <p className="text-sm text-amber-700 mt-0.5">
                Review the summary and grounding score below before approving.
              </p>
            </div>
          </div>
          {grounding && (
            <div className="px-4 pb-4">
              <div className={`flex items-center justify-between p-4 rounded-xl ${
                grounding.overall_score >= 75 ? "bg-green-100 border border-green-300" :
                grounding.overall_score >= 50 ? "bg-yellow-100 border border-yellow-300" :
                "bg-red-100 border border-red-300"
              }`}>
                <div className="flex items-center gap-4">
                  <div className={`h-14 w-14 rounded-xl flex items-center justify-center text-white font-bold text-lg ${
                    grounding.overall_score >= 75 ? "bg-green-600" :
                    grounding.overall_score >= 50 ? "bg-yellow-600" :
                    "bg-red-600"
                  }`}>
                    {grounding.overall_score}
                  </div>
                  <div>
                    <p className="font-bold">Evidence Grounding Score</p>
                    <p className="text-sm text-muted-foreground">
                      {grounding.grounded_count} of {grounding.total_items} items verified against transcript
                      {grounding.flagged_count > 0 && (
                        <span className="text-amber-700 font-medium"> &middot; {grounding.flagged_count} flagged for review</span>
                      )}
                    </p>
                  </div>
                </div>
                <Button onClick={approveVisit} className="bg-green-600 hover:bg-green-700 text-white gap-2 shrink-0">
                  <CheckCircle2 className="h-4 w-4" /> Approve &amp; Release
                </Button>
              </div>
            </div>
          )}
          {!grounding && (
            <div className="px-4 pb-4 flex justify-end">
              <Button onClick={approveVisit} className="bg-green-600 hover:bg-green-700 text-white gap-2">
                <CheckCircle2 className="h-4 w-4" /> Approve &amp; Release
              </Button>
            </div>
          )}
        </div>
      )}

      {/* ── Patient: pending notice ───────────────────────────── */}
      {!isClinician && isPending && (
        <div className="mb-6 flex items-start gap-3 p-4 rounded-2xl border bg-blue-50 border-blue-200">
          <ShieldCheck className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-blue-800">Summary under review</p>
            <p className="text-sm text-blue-700 mt-0.5">
              Your clinician is reviewing this visit summary. You&apos;ll be able to download it once approved.
            </p>
          </div>
        </div>
      )}

      {/* ── Patient: approved download banner ────────────────── */}
      {!isClinician && isApproved && !isPending && (
        <div className="mb-6 p-6 rounded-2xl bg-gradient-to-r from-cyan-50 to-emerald-50 border border-cyan-200">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
                <CheckCircle2 className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="font-bold text-gray-900">Your Visit Summary is Ready!</p>
                <p className="text-sm text-gray-600">Reviewed and approved by your clinician</p>
              </div>
            </div>
            <Button
              onClick={handleExport}
              disabled={exportLoading}
              size="lg"
              className="gap-2 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white shadow-lg w-full sm:w-auto"
            >
              <Download className="h-5 w-5" />
              {exportLoading ? "Generating PDF…" : "Download My Summary (PDF)"}
            </Button>
          </div>
        </div>
      )}

      {/* ── Tabs ─────────────────────────────────────────────── */}
      <div className="flex gap-0 border-b mb-6 overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px shrink-0 transition-colors flex items-center gap-2 ${
              activeTab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>


      {/* ── Patient Summary tab ───────────────────────────────── */}
      {activeTab === "patient" && visit.patient_summary && (
        <div className="space-y-4">
          {/* Visit summary */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">Visit Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{visit.patient_summary.visit_summary}</p>
            </CardContent>
          </Card>

          {/* Medications */}
          {(visit.patient_summary.medications?.length ?? 0) > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Pill className="h-4 w-4 text-blue-500" /> Medications
                </CardTitle>
              </CardHeader>
              <CardContent className="divide-y">
                {visit.patient_summary.medications?.map((med, i) => {
                  const key = `med-${i}`;
                  return (
                    <div key={i} className="py-3 flex items-start justify-between gap-3">
                      <div className="text-sm flex-1">
                        <p className="font-semibold">
                          {med.name}{" "}
                          <span className="font-normal text-muted-foreground">· {med.dose} · {med.frequency}</span>
                        </p>
                        {med.duration && <p className="text-xs text-muted-foreground">Duration: {med.duration}</p>}
                        {med.instructions && <p className="text-muted-foreground text-xs mt-0.5">{med.instructions}</p>}
                        {med.evidence && isClinician && (
                          <p className="text-xs text-blue-600 italic mt-1">&quot;{med.evidence}&quot;</p>
                        )}
                      </div>
                      {isClinician && (
                        <div className="flex gap-1 shrink-0">
                          <button
                            onClick={() => sendFeedback(key, "medication", `${med.name} ${med.dose}`, "correct", "extraction_accuracy")}
                            className={`p-1.5 rounded-lg border transition-colors ${feedback[key] === "correct" ? "bg-green-100 border-green-400 text-green-600" : "hover:bg-green-50 text-muted-foreground"}`}
                            title="Mark as correct"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => sendFeedback(key, "medication", `${med.name} ${med.dose}`, "incorrect", "extraction_accuracy")}
                            className={`p-1.5 rounded-lg border transition-colors ${feedback[key] === "incorrect" ? "bg-red-100 border-red-400 text-red-600" : "hover:bg-red-50 text-muted-foreground"}`}
                            title="Mark as incorrect"
                          >
                            <XCircle className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Tests ordered */}
          {(visit.patient_summary.tests_ordered?.length ?? 0) > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">🔬 Tests Ordered</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {visit.patient_summary.tests_ordered?.map((t, i) => {
                  const key = `test-${i}`;
                  return (
                    <div key={i} className="flex items-start justify-between border rounded-lg p-3">
                      <div className="text-sm">
                        <p className="font-semibold">{t.test_name}</p>
                        <p className="text-muted-foreground text-xs">{t.instructions} · {t.timeline}</p>
                      </div>
                      {isClinician && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => sendFeedback(key, "test_ordered", t.test_name, "correct", "extraction_accuracy")}
                            className={`p-1.5 rounded-lg border ${feedback[key] === "correct" ? "bg-green-100 border-green-400 text-green-600" : "text-muted-foreground hover:bg-green-50"}`}
                          >
                            <CheckCircle2 className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => sendFeedback(key, "test_ordered", t.test_name, "incorrect", "extraction_accuracy")}
                            className={`p-1.5 rounded-lg border ${feedback[key] === "incorrect" ? "bg-red-100 border-red-400 text-red-600" : "text-muted-foreground hover:bg-red-50"}`}
                          >
                            <XCircle className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Lifestyle recommendations */}
          {(visit.patient_summary.lifestyle_recommendations?.length ?? 0) > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">🌿 Lifestyle Recommendations</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {visit.patient_summary.lifestyle_recommendations?.map((lr, i) => (
                  <div key={i} className="border rounded-lg p-3 text-sm">
                    <p className="font-semibold">{lr.recommendation}</p>
                    {lr.details && <p className="text-muted-foreground text-xs mt-1">{lr.details}</p>}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Follow-up plan */}
          {(visit.patient_summary.follow_up_plan?.length ?? 0) > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">📅 Follow-up Plan</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {visit.patient_summary.follow_up_plan?.map((fu, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    <div>
                      <span>{fu.action}</span>
                      {fu.date_or_timeline && (
                        <span className="text-muted-foreground ml-2">· {fu.date_or_timeline}</span>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Red flags */}
          {(visit.patient_summary.red_flags_for_patient?.length ?? 0) > 0 && (
            <Card className="border-red-200 bg-red-50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-red-700 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" /> When to Seek Urgent Care
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {visit.patient_summary.red_flags_for_patient?.map((rf, i) => (
                  <p key={i} className="text-sm text-red-700">• {rf.warning}</p>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Q&A */}
          {(visit.patient_summary.questions_and_answers?.length ?? 0) > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">💬 Questions &amp; Answers</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {visit.patient_summary.questions_and_answers?.map((qa, i) => (
                  <div key={i} className="border rounded-lg p-3 text-sm">
                    <p className="font-semibold text-primary">Q: {qa.question}</p>
                    <p className="mt-1 text-muted-foreground">A: {qa.answer}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Patient: download section at bottom */}
          {!isClinician && isApproved && !isPending && (
            <Card className="border-2 border-dashed border-cyan-200 bg-gradient-to-r from-cyan-50/50 to-emerald-50/50">
              <CardContent className="py-6 text-center">
                <h3 className="font-bold text-lg mb-2">Save Your Visit Summary</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Keep a copy of your visit summary for your personal health records.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <Button
                    onClick={handleExport}
                    disabled={exportLoading}
                    size="lg"
                    className="gap-2 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500"
                  >
                    <Download className="h-5 w-5" />
                    {exportLoading ? "Generating…" : "Download PDF"}
                  </Button>
                  <Button variant="outline" onClick={handlePrint} className="gap-2">
                    <Printer className="h-4 w-4" /> Print
                  </Button>
                  <Button variant="outline" onClick={handleShare} className="gap-2">
                    <Share2 className="h-4 w-4" /> Share
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── SOAP Note tab (clinician only) ────────────────────── */}
      {activeTab === "soap" && visit.clinician_note && isClinician && (
        <div className="space-y-4">
          {(["subjective", "objective", "assessment", "plan"] as const).map(section => {
            const data = visit.clinician_note!.soap_note[section];
            const findings = data.findings ?? [];
            const hasAnyContent = findings.length > 0;
            return (
              <Card key={section} className={!hasAnyContent ? "border-red-200 bg-red-50/30" : ""}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground flex items-center gap-2">
                    {section === "subjective" ? "S — Subjective"
                      : section === "objective" ? "O — Objective"
                      : section === "assessment" ? "A — Assessment"
                      : "P — Plan"}
                    {!hasAnyContent && (
                      <span className="text-red-500 text-[10px] font-bold normal-case tracking-normal border border-red-300 bg-red-100 rounded px-1.5">
                        No data extracted
                      </span>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2">
                  {hasAnyContent ? (
                    <ul className="list-disc list-inside space-y-1">
                      {findings.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  ) : (
                    <p className="text-muted-foreground italic">No findings extracted for this section.</p>
                  )}
                  {data.evidence && data.evidence.length > 0 && (
                    <div className="text-xs text-blue-600 italic border-t pt-2 space-y-0.5">
                      {data.evidence.slice(0, 3).map((e, i) => <p key={i}>&quot;{e}&quot;</p>)}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
          {(visit.clinician_note.problem_list?.length ?? 0) > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Problem List</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {visit.clinician_note.problem_list?.map((p, i) => (
                  <Badge key={i} variant="secondary">{p}</Badge>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Research tab (clinician only) ─────────────────────── */}
      {activeTab === "research" && isClinician && (
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h2 className="font-semibold text-sm mb-3">📚 Published Research</h2>
            {literature.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No papers found.{" "}
                <Link href={`/literature/${visitId}`} className="text-primary underline">
                  Refresh search →
                </Link>
              </p>
            ) : (
              <div className="space-y-3">
                {literature.slice(0, 5).map((p, i) => {
                  const key = `paper-${p.paper_id}`;
                  return (
                    <Card key={i} className="p-4">
                      <p className="font-semibold text-sm leading-snug mb-1">
                        <a href={p.url} target="_blank" rel="noopener noreferrer" className="hover:text-primary">
                          {p.title}
                        </a>
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {p.authors.slice(0, 2).join(", ")} · {p.year} · {p.journal}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">{p.citation_count} citations</p>
                      <div className="flex gap-1 mt-2">
                        <button
                          onClick={() => sendFeedback(key, "paper", p.title, "relevant", "literature_relevance", p.url)}
                          className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border transition-colors ${feedback[key] === "relevant" ? "bg-green-100 border-green-400 text-green-700" : "text-muted-foreground hover:bg-green-50"}`}
                        >
                          <ThumbsUp className="h-3 w-3" /> Relevant
                        </button>
                        <button
                          onClick={() => sendFeedback(key, "paper", p.title, "not_relevant", "literature_relevance", p.url)}
                          className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border transition-colors ${feedback[key] === "not_relevant" ? "bg-red-100 border-red-400 text-red-700" : "text-muted-foreground hover:bg-red-50"}`}
                        >
                          <ThumbsDown className="h-3 w-3" /> Not relevant
                        </button>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
          <div>
            <h2 className="font-semibold text-sm mb-3">🔬 Clinical Trials</h2>
            {trials.length === 0 ? (
              <p className="text-sm text-muted-foreground">No trials found.</p>
            ) : (
              <div className="space-y-3">
                {trials.map((t, i) => (
                  <Card key={i} className="p-4">
                    <p className="font-semibold text-sm leading-snug mb-1">
                      <a href={t.url} target="_blank" rel="noopener noreferrer" className="hover:text-primary">
                        {t.brief_title}
                      </a>
                    </p>
                    <Badge className="bg-green-100 text-green-700 border-green-200 text-[10px] mb-2">{t.status}</Badge>
                    <p className="text-xs text-muted-foreground">{t.conditions?.slice(0, 3).join(", ")}</p>
                    {t.why_it_matches && <p className="text-xs text-blue-600 mt-1">{t.why_it_matches}</p>}
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Transcript tab (clinician only) ───────────────────── */}
      {activeTab === "transcript" && isClinician && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground max-h-[60vh] overflow-y-auto">
              {visit.raw_transcript || "No transcript available."}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}