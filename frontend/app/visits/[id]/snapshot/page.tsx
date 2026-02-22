"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { getVisit, exportPDF, downloadPDF } from "@/lib/api";
import {
  ArrowLeft, Download, CheckCircle2, Pencil, Save, X,
  AlertTriangle, Calendar, Clock, Pill, FlaskConical,
  FileText, Activity, Stethoscope, ClipboardList,
} from "lucide-react";
import { toast } from "sonner";
import type { VisitRecord, AuthUser } from "@/types";

const RISK_COLOR: Record<string, string> = {
  low: "text-green-600 bg-green-50 border-green-200",
  medium: "text-amber-600 bg-amber-50 border-amber-200",
  high: "text-red-600 bg-red-50 border-red-200",
};

const RISK_BG: Record<string, string> = {
  low: "#16a34a",
  medium: "#d97706",
  high: "#dc2626",
};

type EditableSection =
  | "visit_summary"
  | "medications"
  | "tests"
  | "follow_up"
  | "soap_s"
  | "soap_o"
  | "soap_a"
  | "soap_p"
  | null;

interface SnapshotEdits {
  visit_summary?: string;
  medications?: string;
  tests?: string;
  follow_up?: string;
  soap_s?: string;
  soap_o?: string;
  soap_a?: string;
  soap_p?: string;
}

function formatMedications(visit: VisitRecord): string {
  return (
    visit.patient_summary?.medications
      ?.map(
        (m) =>
          `${m.name} — ${m.dose}, ${m.frequency}${m.duration ? `, ${m.duration}` : ""}${m.instructions ? `\n  Instructions: ${m.instructions}` : ""}`
      )
      .join("\n\n") || "No medications recorded."
  );
}

function formatTests(visit: VisitRecord): string {
  return (
    visit.patient_summary?.tests_ordered
      ?.map(
        (t) =>
          `${t.test_name}${t.instructions ? ` — ${t.instructions}` : ""}${t.timeline ? ` (${t.timeline})` : ""}`
      )
      .join("\n") || "No tests ordered."
  );
}

function formatFollowUp(visit: VisitRecord): string {
  return (
    visit.patient_summary?.follow_up_plan
      ?.map(
        (f) =>
          `${f.action}${f.date_or_timeline ? ` — ${f.date_or_timeline}` : ""}`
      )
      .join("\n") || "No follow-up items."
  );
}

function formatSOAP(visit: VisitRecord, section: "subjective" | "objective" | "assessment" | "plan"): string {
  const data = visit.clinician_note?.soap_note?.[section];
  if (!data) return "Not available.";

  const parts: string[] = [];
  if (section === "subjective") {
    if (data.chief_complaint) parts.push(`Chief Complaint: ${data.chief_complaint}`);
    if (data.history_of_present_illness) parts.push(`HPI: ${data.history_of_present_illness}`);
    if (data.review_of_systems) parts.push(`ROS: ${data.review_of_systems}`);
  } else if (section === "objective") {
    if (data.vitals) parts.push(`Vitals: ${data.vitals}`);
    if (data.physical_exam_findings) parts.push(`PE: ${data.physical_exam_findings}`);
  } else if (section === "assessment") {
    if (data.diagnoses?.length) parts.push(`Diagnoses: ${data.diagnoses.join(", ")}`);
    if (data.clinical_impression) parts.push(`Impression: ${data.clinical_impression}`);
  } else if (section === "plan") {
    if (data.follow_up) parts.push(`Follow-up: ${data.follow_up}`);
    if (data.patient_education) parts.push(`Education: ${data.patient_education}`);
  }
  return parts.join("\n") || "Not available.";
}

export default function SnapshotPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const visitId = Number(id);
  const printRef = useRef<HTMLDivElement>(null);

  const [visit, setVisit] = useState<VisitRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  // Editing state
  const [editing, setEditing] = useState<EditableSection>(null);
  const [edits, setEdits] = useState<SnapshotEdits>({});
  const [draftValue, setDraftValue] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    if (!stored) { router.push("/login"); return; }
    setUser(JSON.parse(stored));

    const pending = JSON.parse(localStorage.getItem("medsift_pending") || "[]") as number[];
    const approved = JSON.parse(localStorage.getItem("medsift_approvals") || "[]") as number[];
    setIsPending(pending.includes(visitId));
    setIsApproved(approved.includes(visitId) || !pending.includes(visitId));

    // Load saved edits
    const savedEdits = localStorage.getItem(`medsift_snapshot_${visitId}`);
    if (savedEdits) setEdits(JSON.parse(savedEdits));

    async function load() {
      try {
        const v = await getVisit(visitId);
        setVisit(v);
      } catch {
        router.push("/visits");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [visitId, router]);

  const isClinician = user?.role === "clinician";

  const startEdit = (section: EditableSection) => {
    if (!section || !visit) return;
    const current = getDisplayValue(section);
    setDraftValue(current);
    setEditing(section);
  };

  const saveEdit = () => {
    if (!editing) return;
    const newEdits = { ...edits, [editing]: draftValue };
    setEdits(newEdits);
    localStorage.setItem(`medsift_snapshot_${visitId}`, JSON.stringify(newEdits));
    setEditing(null);
    toast.success("Changes saved");
  };

  const cancelEdit = () => {
    setEditing(null);
    setDraftValue("");
  };

  const getDisplayValue = (section: NonNullable<EditableSection>): string => {
    if (edits[section]) return edits[section]!;
    if (!visit) return "";
    switch (section) {
      case "visit_summary": return visit.patient_summary?.visit_summary || "No summary available.";
      case "medications": return formatMedications(visit);
      case "tests": return formatTests(visit);
      case "follow_up": return formatFollowUp(visit);
      case "soap_s": return formatSOAP(visit, "subjective");
      case "soap_o": return formatSOAP(visit, "objective");
      case "soap_a": return formatSOAP(visit, "assessment");
      case "soap_p": return formatSOAP(visit, "plan");
      default: return "";
    }
  };

  const approveVisit = () => {
    const pending = JSON.parse(localStorage.getItem("medsift_pending") || "[]") as number[];
    const approved = JSON.parse(localStorage.getItem("medsift_approvals") || "[]") as number[];
    const newApproved = [...approved, visitId];
    const newPending = pending.filter((pid) => pid !== visitId);
    localStorage.setItem("medsift_approvals", JSON.stringify(newApproved));
    localStorage.setItem("medsift_pending", JSON.stringify(newPending));
    setIsApproved(true);
    setIsPending(false);
    toast.success("Visit approved — snapshot is now available for download");
  };

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const blob = await exportPDF(visitId);
      downloadPDF(blob, `visit-${visitId}-snapshot.pdf`);
      toast.success("Snapshot PDF downloaded");
    } catch {
      toast.error("PDF export failed — backend may be offline");
    } finally {
      setExportLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-60 w-full" />
      </div>
    );
  }

  if (!visit) return null;

  const riskLevel = visit.risk_assessment?.risk_level ?? "low";

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Link href={`/visits/${visitId}`}>
            <Button variant="ghost" size="icon" className="shrink-0">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Visit Snapshot</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Summary generated from audio transcription
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isPending && (
            <Badge className="bg-amber-100 text-amber-700 border-amber-300">
              Pending Approval
            </Badge>
          )}
          {isApproved && !isPending && (
            <Badge className="bg-green-100 text-green-700 border-green-300 gap-1">
              <CheckCircle2 className="h-3 w-3" /> Approved
            </Badge>
          )}
        </div>
      </div>

      {/* Document */}
      <div ref={printRef} className="space-y-5">
        {/* Document header card */}
        <Card className="overflow-hidden">
          <div
            className="px-6 py-5 text-white"
            style={{
              background: "linear-gradient(135deg, #0d2352 0%, #1565c0 100%)",
            }}
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="relative w-[120px] h-[36px] shrink-0">
                  <Image
                    src="/logo.png"
                    alt="MedSift AI"
                    fill
                    className="object-cover object-center brightness-0 invert"
                  />
                </div>
                <div className="h-8 w-px bg-white/20" />
                <div>
                  <p className="text-sm font-bold capitalize">
                    {visit.visit_type} Visit
                  </p>
                  <div className="flex items-center gap-3 text-xs text-white/70 mt-0.5">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(visit.visit_date).toLocaleDateString("en-US", {
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                    {visit.audio_duration_seconds > 0 && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {(visit.audio_duration_seconds / 60).toFixed(1)} min
                      </span>
                    )}
                  </div>
                </div>
              </div>
              {visit.risk_assessment && (
                <div
                  className="px-3 py-1.5 rounded-lg text-sm font-bold text-white"
                  style={{ background: RISK_BG[riskLevel] }}
                >
                  Risk {visit.risk_assessment.risk_score}/100
                </div>
              )}
            </div>
          </div>
          {visit.tags?.length > 0 && (
            <div className="px-6 py-3 bg-slate-50 border-t flex gap-1.5 flex-wrap">
              {visit.tags.map((t) => (
                <Badge key={t} variant="outline" className="text-xs">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </Card>

        {/* Visit Summary */}
        <SnapshotSection
          icon={<FileText className="h-4 w-4 text-primary" />}
          title="Visit Summary"
          sectionKey="visit_summary"
          value={getDisplayValue("visit_summary")}
          editing={editing}
          draftValue={draftValue}
          isClinician={isClinician}
          onEdit={() => startEdit("visit_summary")}
          onSave={saveEdit}
          onCancel={cancelEdit}
          onDraftChange={setDraftValue}
        />

        {/* Medications */}
        <SnapshotSection
          icon={<Pill className="h-4 w-4 text-blue-600" />}
          title="Medications"
          sectionKey="medications"
          value={getDisplayValue("medications")}
          editing={editing}
          draftValue={draftValue}
          isClinician={isClinician}
          onEdit={() => startEdit("medications")}
          onSave={saveEdit}
          onCancel={cancelEdit}
          onDraftChange={setDraftValue}
        />

        {/* Tests Ordered */}
        <SnapshotSection
          icon={<FlaskConical className="h-4 w-4 text-purple-600" />}
          title="Tests Ordered"
          sectionKey="tests"
          value={getDisplayValue("tests")}
          editing={editing}
          draftValue={draftValue}
          isClinician={isClinician}
          onEdit={() => startEdit("tests")}
          onSave={saveEdit}
          onCancel={cancelEdit}
          onDraftChange={setDraftValue}
        />

        {/* Follow-up Plan */}
        <SnapshotSection
          icon={<ClipboardList className="h-4 w-4 text-green-600" />}
          title="Follow-up Plan"
          sectionKey="follow_up"
          value={getDisplayValue("follow_up")}
          editing={editing}
          draftValue={draftValue}
          isClinician={isClinician}
          onEdit={() => startEdit("follow_up")}
          onSave={saveEdit}
          onCancel={cancelEdit}
          onDraftChange={setDraftValue}
        />

        {/* Risk Assessment (read-only) */}
        {visit.risk_assessment && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Activity className="h-4 w-4 text-red-500" />
                Risk Assessment
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 mb-3">
                <div
                  className="text-4xl font-black"
                  style={{ color: RISK_BG[riskLevel] }}
                >
                  {visit.risk_assessment.risk_score}
                </div>
                <div>
                  <p
                    className="text-sm font-bold capitalize"
                    style={{ color: RISK_BG[riskLevel] }}
                  >
                    {riskLevel} Risk
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {visit.risk_assessment.total_factors_detected} factors
                    detected
                  </p>
                </div>
              </div>

              {(visit.risk_assessment.red_flags?.length ?? 0) > 0 && (
                <div className="space-y-2 mt-3 pt-3 border-t">
                  <p className="text-xs font-semibold text-red-600 flex items-center gap-1">
                    <AlertTriangle className="h-3.5 w-3.5" /> Red Flags
                  </p>
                  {visit.risk_assessment.red_flags.map((rf, i) => (
                    <div
                      key={i}
                      className="text-xs p-2.5 rounded-lg bg-red-50 border border-red-100"
                    >
                      <p className="font-medium text-red-700">{rf.flag}</p>
                      <p className="text-red-600/70 mt-0.5">
                        {rf.recommended_action}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* SOAP Note */}
        {visit.clinician_note?.soap_note && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Stethoscope className="h-4 w-4 text-primary" />
                SOAP Note
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {(
                [
                  ["soap_s", "S — Subjective"],
                  ["soap_o", "O — Objective"],
                  ["soap_a", "A — Assessment"],
                  ["soap_p", "P — Plan"],
                ] as const
              ).map(([key, label]) => (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                      {label}
                    </p>
                    {isClinician && editing !== key && (
                      <button
                        onClick={() => startEdit(key)}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                  {editing === key ? (
                    <div className="space-y-2">
                      <Textarea
                        value={draftValue}
                        onChange={(e) => setDraftValue(e.target.value)}
                        className="min-h-[80px] text-sm"
                        autoFocus
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={saveEdit}
                          className="gap-1.5 h-7 text-xs"
                        >
                          <Save className="h-3 w-3" /> Save
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={cancelEdit}
                          className="gap-1.5 h-7 text-xs"
                        >
                          <X className="h-3 w-3" /> Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                      {getDisplayValue(key)}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Red flags for patient */}
        {(visit.patient_summary?.red_flags_for_patient?.length ?? 0) > 0 && (
          <Card className="border-red-200 bg-red-50/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-red-700 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> When to Seek Urgent Care
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {visit.patient_summary.red_flags_for_patient.map((rf, i) => (
                <p key={i} className="text-sm text-red-700">
                  • {rf.warning}
                </p>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Action bar */}
      <div className="mt-8 space-y-3">
        {/* Clinician: Approve button */}
        {isClinician && isPending && (
          <Button
            onClick={approveVisit}
            size="lg"
            className="w-full gap-2 bg-green-600 hover:bg-green-700 text-white"
          >
            <CheckCircle2 className="h-5 w-5" /> Approve & Release to Patient
          </Button>
        )}

        {/* Download button — both roles can download after approval */}
        <Button
          onClick={handleExport}
          disabled={exportLoading || (!isApproved && !isClinician)}
          size="lg"
          variant={isApproved ? "default" : "outline"}
          className="w-full gap-2"
        >
          <Download className="h-5 w-5" />
          {exportLoading
            ? "Generating PDF..."
            : !isApproved && !isClinician
              ? "PDF available after approval"
              : "Download Snapshot (PDF)"}
        </Button>

        {!isApproved && !isClinician && (
          <p className="text-xs text-center text-muted-foreground">
            Your clinician needs to review and approve this snapshot before you
            can download it.
          </p>
        )}

        <p className="text-[10px] text-center text-muted-foreground mt-2">
          This snapshot was generated by MedSift AI and reviewed by a clinician.
          It is for informational purposes only and does not replace professional
          medical advice.
        </p>
      </div>
    </div>
  );
}

/* ── Reusable editable section ──────────────────────────────────────────────── */

function SnapshotSection({
  icon,
  title,
  sectionKey,
  value,
  editing,
  draftValue,
  isClinician,
  onEdit,
  onSave,
  onCancel,
  onDraftChange,
}: {
  icon: React.ReactNode;
  title: string;
  sectionKey: NonNullable<EditableSection>;
  value: string;
  editing: EditableSection;
  draftValue: string;
  isClinician: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onDraftChange: (v: string) => void;
}) {
  const isEditing = editing === sectionKey;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            {icon}
            {title}
          </CardTitle>
          {isClinician && !isEditing && (
            <button
              onClick={onEdit}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <Pencil className="h-3.5 w-3.5" /> Edit
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isEditing ? (
          <div className="space-y-2">
            <Textarea
              value={draftValue}
              onChange={(e) => onDraftChange(e.target.value)}
              className="min-h-[120px] text-sm font-mono"
              autoFocus
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={onSave} className="gap-1.5 h-7 text-xs">
                <Save className="h-3 w-3" /> Save
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={onCancel}
                className="gap-1.5 h-7 text-xs"
              >
                <X className="h-3 w-3" /> Cancel
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {value}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
