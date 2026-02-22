"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getAnalytics } from "@/lib/api";
import { getMockAnalytics } from "@/lib/mockData";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import type { AnalyticsSummary } from "@/types";

const BLUE_PALETTE  = ["#1e40af", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe", "#dbeafe", "#eff6ff", "#f0f9ff"];
const MIXED_PALETTE = ["#1d4ed8", "#0d9488", "#7c3aed", "#db2777", "#ea580c", "#ca8a04", "#16a34a", "#0891b2"];

function StatCard({
  label, value, sub, color = "text-primary",
}: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">{label}</p>
        <p className={`text-3xl font-black ${color}`}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// Custom tooltip for charts
function ChartTooltip({ active, payload, label, suffix = "" }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color ?? p.fill }}>
          {p.name}: <span className="font-bold">{p.value}{suffix}</span>
        </p>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading]     = useState(true);
  const [usingMock, setUsingMock] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const a = await getAnalytics();
        setAnalytics(a);
      } catch {
        // Backend not running — fall back to rich mock data
        setAnalytics(getMockAnalytics() as any);
        setUsingMock(true);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // ── Loading skeleton ─────────────────────────────────────────────────────────
  if (loading) return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-2xl" />)}
      </div>
    </div>
  );

  if (!analytics) return (
    <div className="text-center py-24 text-muted-foreground">
      <p>No analytics data available yet.</p>
      <p className="text-sm mt-2">Process some visits first.</p>
    </div>
  );

  // ── Derived data ─────────────────────────────────────────────────────────────
  // weekly_visits (mock) or visits_over_time (backend)
  const timeData: { label: string; count: number }[] =
    (analytics as any).weekly_visits?.map((d: any) => ({ label: d.week, count: d.count })) ??
    (analytics as any).visits_over_time?.map((d: any) => ({ label: d.date, count: d.count })) ??
    [];

  // extraction_accuracy — mock or empty
  const accuracyData: { item_type: string; accuracy: number; correct: number; incorrect: number }[] =
    (analytics as any).extraction_accuracy ?? [];

  // visit_types — mock or empty
  const visitTypeData: { type: string; count: number }[] =
    (analytics as any).visit_types ?? [];

  // keyword boost score — stored as 0–100 in mock, 0–1 in backend
  const keywords = (analytics.top_boosted_keywords ?? []).map(kw => ({
    ...kw,
    boost_score: kw.boost_score > 1 ? kw.boost_score / 100 : kw.boost_score,
  }));

  // total visits computed from visit_types if available, else from field
  const totalVisits =
    visitTypeData.length > 0
      ? visitTypeData.reduce((s, d) => s + d.count, 0)
      : analytics.total_visits;

  // avg accuracy from extraction data
  const avgAccuracy =
    accuracyData.length > 0
      ? (accuracyData.reduce((s, d) => s + d.accuracy, 0) / accuracyData.length).toFixed(1)
      : null;

  // top condition
  const topCondition = analytics.top_conditions?.[0]?.condition ?? null;

  // peak week
  const peakWeek = timeData.reduce(
    (best, d) => (d.count > best.count ? d : best),
    { label: "—", count: 0 }
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* ── Header ── */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Aggregated insights across all visits and feedback.
            {usingMock && (
              <span className="ml-2 text-xs bg-amber-50 text-amber-600 border border-amber-200 px-2 py-0.5 rounded-full">
                Demo data
              </span>
            )}
          </p>
        </div>
        {/* Date range badge */}
        <div className="text-xs text-muted-foreground bg-gray-50 border rounded-lg px-3 py-1.5 hidden sm:block">
          Nov 2024 – Jan 2025
        </div>
      </div>

      {/* ── KPI stat cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Visits"    value={totalVisits.toLocaleString()} sub="Nov 2024 – Jan 2025" />
        {avgAccuracy && (
          <StatCard label="Avg AI Accuracy" value={`${avgAccuracy}%`} sub="across extraction types" color="text-teal-600" />
        )}
        {topCondition && (
          <StatCard label="Top Condition"   value={topCondition} sub={`${analytics.top_conditions[0].count} visits`} color="text-blue-700" />
        )}
        {peakWeek.count > 0 && (
          <StatCard label="Peak Week"       value={peakWeek.label} sub={`${peakWeek.count} visits`} color="text-violet-600" />
        )}
      </div>

      {/* ── Row 1: Visits Over Time + Visit Types ── */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">

        {/* Visits over time — line chart */}
        {timeData.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Visits Over Time</CardTitle>
              <p className="text-xs text-muted-foreground">Weekly volume, Nov 2024 – Jan 2025</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={timeData} margin={{ left: -10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Line
                    type="monotone" dataKey="count" name="Visits"
                    stroke="#1d4ed8" strokeWidth={2.5}
                    dot={{ r: 3, fill: "#1d4ed8" }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Visit type breakdown — pie / donut */}
        {visitTypeData.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Visit Types</CardTitle>
              <p className="text-xs text-muted-foreground">Distribution by category</p>
            </CardHeader>
            <CardContent className="flex items-center gap-4">
              <ResponsiveContainer width="55%" height={200}>
                <PieChart>
                  <Pie
                    data={visitTypeData} dataKey="count" nameKey="type"
                    cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                    paddingAngle={3}
                  >
                    {visitTypeData.map((_, i) => (
                      <Cell key={i} fill={MIXED_PALETTE[i % MIXED_PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v, n) => [v, n]} />
                </PieChart>
              </ResponsiveContainer>
              {/* Legend */}
              <div className="flex-1 space-y-1.5">
                {visitTypeData.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: MIXED_PALETTE[i % MIXED_PALETTE.length] }} />
                    <span className="text-gray-600 flex-1">{d.type}</span>
                    <span className="font-semibold text-gray-900">{d.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ── Row 2: Top Conditions + Top Medications ── */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">

        {/* Top Conditions — horizontal bar */}
        {(analytics.top_conditions?.length ?? 0) > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Top Conditions</CardTitle>
              <p className="text-xs text-muted-foreground">By frequency across all visits</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={analytics.top_conditions.slice(0, 8)}
                  layout="vertical" margin={{ left: 10, right: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="condition" tick={{ fontSize: 10 }} width={115} tickLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Visits" radius={[0, 4, 4, 0]}>
                    {analytics.top_conditions.slice(0, 8).map((_, i) => (
                      <Cell key={i} fill={BLUE_PALETTE[i % BLUE_PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Top Medications — vertical bar */}
        {(analytics.top_medications?.length ?? 0) > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Top Medications</CardTitle>
              <p className="text-xs text-muted-foreground">Most frequently prescribed</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={analytics.top_medications.slice(0, 8)}
                  margin={{ left: -10, right: 10, bottom: 30 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="medication" tick={{ fontSize: 9 }} tickLine={false}
                    angle={-35} textAnchor="end" interval={0}
                  />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="count" name="Prescriptions" radius={[4, 4, 0, 0]}>
                    {analytics.top_medications.slice(0, 8).map((_, i) => (
                      <Cell key={i} fill={MIXED_PALETTE[i % MIXED_PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ── Row 3: AI Extraction Accuracy ── */}
      {accuracyData.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">AI Extraction Accuracy by Category</CardTitle>
            <p className="text-xs text-muted-foreground">Based on clinician feedback — correct vs. flagged extractions</p>
          </CardHeader>
          <CardContent>
            <div className="grid lg:grid-cols-2 gap-6 items-center">
              {/* Bar chart */}
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={accuracyData} margin={{ left: -10, right: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="item_type" tick={{ fontSize: 10 }} tickLine={false}
                    angle={-20} textAnchor="end" interval={0}
                  />
                  <YAxis domain={[80, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
                  <Tooltip content={<ChartTooltip suffix="%" />} />
                  <Bar dataKey="accuracy" name="Accuracy" radius={[4, 4, 0, 0]}>
                    {accuracyData.map((_, i) => (
                      <Cell key={i} fill={MIXED_PALETTE[i % MIXED_PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              {/* Accuracy breakdown table */}
              <div className="space-y-3">
                {accuracyData.map((d, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-gray-700">{d.item_type}</span>
                      <span className="font-bold" style={{ color: MIXED_PALETTE[i % MIXED_PALETTE.length] }}>
                        {d.accuracy}%
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${d.accuracy}%`,
                          background: MIXED_PALETTE[i % MIXED_PALETTE.length],
                        }}
                      />
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {d.correct} correct · {d.incorrect} flagged
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Boosted Keywords Table ── */}
      {keywords.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">🚀 Top Boosted Keywords (Learning Loop)</CardTitle>
            <p className="text-xs text-muted-foreground">
              Keywords with high boost scores are automatically prioritised in future literature searches.
            </p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Keyword</th>
                    <th className="pb-3 pr-4 font-medium">👍 Positive</th>
                    <th className="pb-3 pr-4 font-medium">👎 Negative</th>
                    <th className="pb-3 font-medium">Boost Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {keywords.map((kw, i) => (
                    <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                      <td className="py-3 pr-4 font-medium text-gray-900">{kw.keyword}</td>
                      <td className="py-3 pr-4 text-green-600 font-semibold">{kw.positive_count}</td>
                      <td className="py-3 pr-4 text-red-500 font-semibold">{kw.negative_count}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-2 rounded-full bg-primary/10 w-28 overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full"
                              style={{ width: `${(kw.boost_score * 100).toFixed(0)}%` }}
                            />
                          </div>
                          <span className="text-xs font-semibold text-primary">
                            {(kw.boost_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}