"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getVisits, deleteVisit } from "@/lib/api";
import { Search, Calendar, Clock, Trash2, ArrowRight, Plus } from "lucide-react";
import { toast } from "sonner";
import type { VisitRecord, AuthUser } from "@/types";

export default function VisitsPage() {
  const [visits, setVisits] = useState<VisitRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeTag, setActiveTag] = useState("");
  const [isClinician, setIsClinician] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    if (stored) {
      const u = JSON.parse(stored) as AuthUser;
      setIsClinician(u.role === "clinician");
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getVisits({ search: search || undefined, tag: activeTag || undefined });
      setVisits(data);
    } catch {
      setVisits([]);
    } finally {
      setLoading(false);
    }
  }, [search, activeTag]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    if (!confirm("Delete this visit? This cannot be undone.")) return;
    try {
      await deleteVisit(id);
      setVisits(v => v.filter(x => x.id !== id));
      toast.success("Visit deleted");
    } catch {
      toast.error("Delete failed");
    }
  };

  // Collect all unique tags from loaded visits
  const allTags = Array.from(new Set(visits.flatMap(v => v.tags ?? [])));

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Visit History</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{visits.length} visit{visits.length !== 1 ? "s" : ""} recorded</p>
        </div>
        {isClinician && (
          <Link href="/upload">
            <Button className="gap-2"><Plus className="h-4 w-4" /> New Recording</Button>
          </Link>
        )}
      </div>

      {/* Search + tag filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search visits…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {allTags.map(tag => (
            <button
              key={tag}
              onClick={() => setActiveTag(activeTag === tag ? "" : tag)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                activeTag === tag
                  ? "bg-primary text-white border-primary"
                  : "bg-white text-muted-foreground border-muted hover:border-primary/50"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Visit grid */}
      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-2xl" />
          ))}
        </div>
      ) : visits.length === 0 ? (
        <div className="text-center py-24 text-muted-foreground">
          <p className="text-lg font-medium mb-2">No visits yet</p>
          {isClinician ? (
            <>
              <p className="text-sm mb-6">Upload a recording to get started.</p>
              <Link href="/upload"><Button>Upload First Recording</Button></Link>
            </>
          ) : (
            <p className="text-sm">No approved visit summaries yet. Your clinician will approve them before they appear here.</p>
          )}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visits.map(visit => (
            <Link key={visit.id} href={`/visits/${visit.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full group">
                <CardContent className="p-5 flex flex-col h-full">
                  {/* Top row */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <p className="font-semibold text-sm capitalize">{visit.visit_type}</p>
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
                        <Calendar className="h-3 w-3" />
                        {new Date(visit.visit_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </div>
                    </div>
                  </div>

                  {/* Summary snippet */}
                  {visit.patient_summary?.visit_summary && (
                    <p className="text-xs text-muted-foreground line-clamp-3 flex-1">
                      {visit.patient_summary.visit_summary}
                    </p>
                  )}

                  {/* Footer */}
                  <div className="mt-3 pt-3 border-t flex items-center justify-between">
                    <div className="flex gap-1 flex-wrap">
                      {(visit.tags ?? []).slice(0, 3).map(tag => (
                        <Badge key={tag} variant="outline" className="text-[10px] px-1.5 py-0">{tag}</Badge>
                      ))}
                    </div>
                    <div className="flex items-center gap-2">
                      {visit.audio_duration_seconds && (
                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />{(visit.audio_duration_seconds / 60).toFixed(1)}m
                        </span>
                      )}
                      {isClinician && (
                        <button
                          onClick={e => handleDelete(visit.id, e)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-50 text-red-400 hover:text-red-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
