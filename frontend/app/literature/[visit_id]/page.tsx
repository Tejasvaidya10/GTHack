"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getLiterature, getTrials, submitFeedback } from "@/lib/api";
import { ArrowLeft, RefreshCw, ThumbsUp, ThumbsDown, ExternalLink, BookOpen, FlaskConical } from "lucide-react";
import { toast } from "sonner";
import type { LiteratureResult, ClinicalTrial } from "@/types";

export default function LiteraturePage() {
  const { visit_id } = useParams<{ visit_id: string }>();
  const visitId = Number(visit_id);
  const [papers, setPapers] = useState<LiteratureResult[]>([]);
  const [trials, setTrials] = useState<ClinicalTrial[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [feedback, setFeedback] = useState<Record<string, "relevant" | "not_relevant">>({});

  const load = async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);
    try {
      const [lit, tri] = await Promise.all([
        getLiterature(visitId, refresh),
        getTrials(visitId),
      ]);
      setPapers(lit);
      setTrials(tri);
    } catch {
      setPapers([]);
      setTrials([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, [visitId]);

  const sendFeedback = async (key: string, itemType: "paper" | "trial", title: string, rating: "relevant" | "not_relevant", url?: string) => {
    setFeedback(f => ({ ...f, [key]: rating }));
    try {
      await submitFeedback({ visit_id: visitId, feedback_type: "literature_relevance", item_type: itemType, item_value: title, rating, paper_url: url });
      toast.success("Feedback recorded — this improves future searches!");
    } catch {
      toast.error("Feedback failed");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <Link href={`/visits/${visitId}`}>
            <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Research & Trials</h1>
            <p className="text-muted-foreground text-sm mt-0.5">Visit #{visitId} · AI-matched research from Semantic Scholar & ClinicalTrials.gov</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => load(true)} disabled={refreshing} className="gap-2">
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Refreshing…" : "Refresh Search"}
        </Button>
      </div>

      {loading ? (
        <div className="grid lg:grid-cols-2 gap-6">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-52 rounded-2xl" />)}
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-8">
          {/* ── Papers ─────────────────────────────────────────── */}
          <div>
            <h2 className="flex items-center gap-2 font-semibold mb-4 text-sm">
              <BookOpen className="h-4 w-4 text-primary" />
              Published Research
              <span className="text-muted-foreground font-normal">({papers.length} papers · sorted by impact)</span>
            </h2>
            {papers.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-sm border rounded-2xl">
                No papers found for this visit&apos;s conditions.
              </div>
            ) : (
              <div className="space-y-4">
                {papers.map((paper, i) => {
                  const key = `paper-${paper.paper_id}`;
                  const fb = feedback[key];
                  return (
                    <Card key={i} className={`transition-colors ${fb === "relevant" ? "border-green-300 bg-green-50/50" : fb === "not_relevant" ? "border-red-200 bg-red-50/30 opacity-70" : ""}`}>
                      <CardContent className="p-5">
                        {/* Citation rank badge */}
                        <div className="flex items-start gap-3">
                          <div className="shrink-0 h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                            #{i + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <a href={paper.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-sm hover:text-primary leading-snug block mb-1">
                              {paper.title} <ExternalLink className="h-3 w-3 inline ml-0.5 opacity-50" />
                            </a>
                            <p className="text-xs text-muted-foreground truncate">
                              {paper.authors.slice(0, 3).join(", ")}
                              {paper.authors.length > 3 && " et al."}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              {paper.journal && <span className="text-xs text-muted-foreground italic">{paper.journal}</span>}
                              {paper.year && <Badge variant="outline" className="text-[10px] px-1.5">{paper.year}</Badge>}
                              <Badge variant="secondary" className="text-[10px] px-1.5">⭐ {paper.influential_citation_count} influential</Badge>
                              <span className="text-[10px] text-muted-foreground">{paper.citation_count} citations</span>
                            </div>
                          </div>
                        </div>

                        {paper.abstract_snippet && (
                          <p className="text-xs text-muted-foreground mt-3 leading-relaxed line-clamp-3">{paper.abstract_snippet}</p>
                        )}

                        {paper.relevance_explanation && (
                          <p className="text-xs text-blue-600 mt-2 italic">💡 {paper.relevance_explanation}</p>
                        )}

                        {/* Feedback buttons */}
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t">
                          <span className="text-xs text-muted-foreground mr-1">Is this relevant?</span>
                          <button
                            onClick={() => sendFeedback(key, "paper", paper.title, "relevant", paper.url)}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                              fb === "relevant"
                                ? "bg-green-500 text-white border-green-500"
                                : "hover:bg-green-50 text-muted-foreground border-muted hover:border-green-400 hover:text-green-700"
                            }`}
                          >
                            <ThumbsUp className="h-3 w-3" /> Yes
                          </button>
                          <button
                            onClick={() => sendFeedback(key, "paper", paper.title, "not_relevant", paper.url)}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                              fb === "not_relevant"
                                ? "bg-red-500 text-white border-red-500"
                                : "hover:bg-red-50 text-muted-foreground border-muted hover:border-red-400 hover:text-red-700"
                            }`}
                          >
                            <ThumbsDown className="h-3 w-3" /> No
                          </button>
                          {fb && (
                            <span className="text-xs text-muted-foreground ml-1">
                              {fb === "relevant" ? "✓ Marked relevant" : "✗ Marked not relevant"}
                            </span>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* ── Clinical Trials ────────────────────────────────── */}
          <div>
            <h2 className="flex items-center gap-2 font-semibold mb-4 text-sm">
              <FlaskConical className="h-4 w-4 text-cyan-600" />
              Recruiting Clinical Trials
              <span className="text-muted-foreground font-normal">({trials.length} trials)</span>
            </h2>
            {trials.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-sm border rounded-2xl">
                No actively recruiting trials found for this visit&apos;s conditions.
              </div>
            ) : (
              <div className="space-y-4">
                {trials.map((trial, i) => {
                  const key = `trial-${trial.nct_id}`;
                  const fb = feedback[key];
                  return (
                    <Card key={i} className={`transition-colors ${fb === "relevant" ? "border-green-300 bg-green-50/50" : ""}`}>
                      <CardContent className="p-5">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <a href={trial.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-sm hover:text-primary leading-snug flex-1">
                            {trial.brief_title} <ExternalLink className="h-3 w-3 inline ml-0.5 opacity-50" />
                          </a>
                          <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 text-[10px] shrink-0">{trial.status}</Badge>
                        </div>

                        <p className="text-[10px] text-muted-foreground font-mono mb-2">{trial.nct_id}</p>

                        <div className="space-y-1 text-xs text-muted-foreground">
                          {trial.conditions?.length > 0 && (
                            <p><strong className="text-foreground">Conditions:</strong> {trial.conditions.join(", ")}</p>
                          )}
                          {trial.interventions?.length > 0 && (
                            <p><strong className="text-foreground">Interventions:</strong> {trial.interventions.slice(0, 3).join(", ")}</p>
                          )}
                          {trial.location && (
                            <p><strong className="text-foreground">Location:</strong> {trial.location}</p>
                          )}
                        </div>

                        {trial.why_it_matches && (
                          <p className="text-xs text-blue-600 mt-2 italic">💡 {trial.why_it_matches}</p>
                        )}

                        {/* Feedback */}
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t">
                          <span className="text-xs text-muted-foreground mr-1">Is this relevant?</span>
                          <button
                            onClick={() => sendFeedback(key, "trial", trial.brief_title, "relevant", trial.url)}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                              fb === "relevant" ? "bg-green-500 text-white border-green-500" : "hover:bg-green-50 text-muted-foreground border-muted hover:border-green-400 hover:text-green-700"
                            }`}
                          >
                            <ThumbsUp className="h-3 w-3" /> Yes
                          </button>
                          <button
                            onClick={() => sendFeedback(key, "trial", trial.brief_title, "not_relevant", trial.url)}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                              fb === "not_relevant" ? "bg-red-500 text-white border-red-500" : "hover:bg-red-50 text-muted-foreground border-muted hover:border-red-400 hover:text-red-700"
                            }`}
                          >
                            <ThumbsDown className="h-3 w-3" /> No
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Learning loop note */}
            <Card className="mt-4 bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <p className="text-xs text-blue-700 font-semibold mb-1">🧠 Learning Loop Active</p>
                <p className="text-xs text-blue-600">
                  Your feedback is stored and used to boost relevant keywords in future literature searches.
                  Over time, MedSift learns which papers and trials are most useful for similar cases.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
