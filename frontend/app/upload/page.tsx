"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Upload, CheckCircle2, Circle, Loader2, AlertTriangle,
  FileAudio, Mic, ShieldCheck, Brain, Activity, FileText,
  ArrowRight, Download, Eye, Square, Radio, Clock, Play
} from "lucide-react";
import { transcribeAudio, analyzeTranscript, exportPDF, downloadPDF } from "@/lib/api";
import { toast } from "sonner";
import type { TranscribeResponse, AnalyzeResponse, AuthUser } from "@/types";

type Stage = "idle" | "uploading" | "transcribing" | "redacting" | "extracting" | "scoring" | "done" | "error";
type Mode = "file" | "live" | "demo";

// Demo audio samples with pre-defined transcripts for instant demo
const DEMO_SAMPLES = [
  {
    id: "annual-physical",
    title: "Annual Physical",
    description: "Routine checkup with diabetes and hypertension management",
    duration: "3:24",
    tags: ["wellness", "preventive", "chronic"],
    transcript: `Doctor: Good morning! How have you been feeling since our last visit?
Patient: Really good, doctor. I've been walking every day like you suggested, about 30 minutes each morning.
Doctor: That's excellent! I can see your blood pressure is much better today - 128 over 82. Last time it was 138 over 88.
Patient: Oh that's great news! The lisinopril seems to be working well.
Doctor: Yes, let's keep you on the 10mg once daily. How about the metformin for your diabetes?
Patient: No problems with it. I take it with breakfast and dinner like you said.
Doctor: Perfect. Your last HbA1c came back at 6.8%, down from 7.2%. That's really good progress.
Patient: I've been watching my carbs more carefully too.
Doctor: It shows. I'd like to continue the current medications - lisinopril 10mg daily, metformin 500mg twice daily, and atorvastatin 20mg at bedtime for your cholesterol.
Patient: Sounds good, doctor.
Doctor: Let's get some labs done - a complete metabolic panel, lipid panel, and another HbA1c in about a month. Any questions?
Patient: No, I think I understand everything. Thank you!
Doctor: Great. I'll see you in 6 months for your next checkup. Keep up the good work with the walking!`,
  },
  {
    id: "urgent-respiratory",
    title: "Respiratory Infection",
    description: "Urgent care visit for cough, fever, and pneumonia diagnosis",
    duration: "4:12",
    tags: ["respiratory", "acute", "urgent"],
    transcript: `Doctor: What brings you in today?
Patient: I've had this terrible cough for three days now. It's getting worse, and I had a fever last night.
Doctor: I'm sorry to hear that. How high was the fever?
Patient: It got up to 101 degrees. I've also been really tired and have some chest discomfort when I take deep breaths.
Doctor: Are you coughing anything up?
Patient: Yes, yellow-green mucus. It's pretty thick.
Doctor: Let me listen to your lungs. Take some deep breaths for me... I'm hearing some decreased breath sounds and crackles on your right side.
Patient: That doesn't sound good.
Doctor: I'd like to get a chest X-ray to take a closer look. Your oxygen level is at 94%, which is a bit lower than we'd like.
[After X-ray]
Doctor: The X-ray confirms what I suspected - you have pneumonia in your right lower lobe.
Patient: Pneumonia? Is that serious?
Doctor: It can be, but we caught it early. I'm going to prescribe azithromycin - 500mg today, then 250mg for the next 4 days. Also benzonatate for the cough, and you can take acetaminophen for the fever.
Patient: Okay. Should I be worried?
Doctor: I want you to rest, drink plenty of fluids, and watch for warning signs - if your breathing gets worse, fever goes above 103, or you cough up blood, go to the ER immediately. Otherwise, come back in 3 days so I can check on you.`,
  },
  {
    id: "mental-health",
    title: "Mental Health Follow-up",
    description: "Depression and anxiety medication check with PHQ-9 improvement",
    duration: "2:58",
    tags: ["mental-health", "medication-check"],
    transcript: `Doctor: How have you been doing since we started the sertraline 6 weeks ago?
Patient: Honestly, so much better. I finally feel like myself again.
Doctor: That's wonderful to hear. Tell me more about what's improved.
Patient: My mood is much more stable. I'm sleeping better - about 7 to 8 hours a night now instead of waking up constantly. And I actually have energy to do things.
Doctor: Have you been able to return to work?
Patient: Yes, I went back full-time two weeks ago. It's been going well.
Doctor: That's great progress. Any side effects from the medication?
Patient: A little bit of nausea the first week, but that went away. No other issues.
Doctor: Good. I have your PHQ-9 score here - it's come down from 18 to 8, which is a significant improvement. Your anxiety score also improved, from 15 to 6.
Patient: I can definitely feel the difference.
Doctor: I'd like to keep you on the sertraline 100mg. You also have the hydroxyzine for breakthrough anxiety - how often are you using that?
Patient: Maybe 2 or 3 times a week when I feel anxious. It helps me calm down.
Doctor: That's appropriate use. Are you still seeing your therapist?
Patient: Yes, every two weeks. The CBT has been really helpful.
Doctor: Excellent. Let's continue everything as is and follow up in 3 months. Remember, even when you're feeling well, it's important to keep taking the medication. And if you ever have thoughts of self-harm, please reach out immediately.
Patient: I understand. Thank you, doctor.`,
  },
  {
    id: "heart-failure",
    title: "Heart Failure Follow-up",
    description: "Cardiology visit showing improved ejection fraction",
    duration: "3:45",
    tags: ["cardiology", "chronic"],
    transcript: `Doctor: How have you been feeling since we adjusted your medications?
Patient: So much better! I can actually walk to the mailbox now without getting winded.
Doctor: That's excellent progress. How many blocks can you walk now?
Patient: About 4 blocks before I need to rest. That's way better than before when I couldn't even make it down the driveway.
Doctor: Any chest pain or shortness of breath when lying flat?
Patient: No chest pain at all. And I can sleep flat now - no extra pillows needed.
Doctor: Great. Any swelling in your ankles?
Patient: None that I've noticed. I've been checking every day.
Doctor: Good. I see your weight has been stable at 185 pounds. Your blood pressure today is 110 over 68, heart rate 68 - both excellent.
Patient: The new medications seem to be working.
Doctor: Your echocardiogram results came back. Your ejection fraction has improved from 35% to 42%.
Patient: Is that good?
Doctor: It's very good - it means your heart is pumping more efficiently. Your BNP levels also dropped from 450 to 180, another positive sign.
Patient: That's a relief.
Doctor: Let's continue the current regimen - Entresto 97/103mg twice daily, carvedilol 25mg twice daily, furosemide 40mg in the morning, and spironolactone 25mg daily. Keep monitoring your weight daily and call if you gain more than 3 pounds in a day.
Patient: I will. Thank you, doctor.
Doctor: You're doing great. See you in 3 months!`,
  },
];

const STAGES: { key: Stage; label: string; icon: React.ElementType; sub: string }[] = [
  { key: "uploading",    label: "Uploading audio",       icon: Upload,       sub: "Sending file to backend" },
  { key: "transcribing", label: "Transcribing (Whisper)", icon: Mic,          sub: "Local speech-to-text" },
  { key: "redacting",    label: "Redacting PHI",          icon: ShieldCheck,  sub: "Presidio anonymization" },
  { key: "extracting",   label: "Extracting care plan",   icon: Brain,        sub: "LLaMA 3 structured extraction" },
  { key: "scoring",      label: "Scoring risk",           icon: Activity,     sub: "Rule-based + LLM analysis" },
];

const STAGE_ORDER: Stage[] = ["uploading", "transcribing", "redacting", "extracting", "scoring", "done"];

function stageIndex(s: Stage) { return STAGE_ORDER.indexOf(s); }

export default function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  const [mode, setMode] = useState<Mode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [selectedDemo, setSelectedDemo] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [recording, setRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [waveformData, setWaveformData] = useState<number[]>(new Array(64).fill(0));
  const [visitDate, setVisitDate] = useState(new Date().toISOString().split("T")[0]);
  const [visitType, setVisitType] = useState("routine checkup");
  const [tags, setTags] = useState("");
  const [transcribeResult, setTranscribeResult] = useState<TranscribeResponse | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"care-plan" | "soap" | "risk" | "transcript">("care-plan");
  const [errorMsg, setErrorMsg] = useState("");
  const [exportLoading, setExportLoading] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("medsift_user");
    if (!stored) { router.push("/login"); return; }
    const u = JSON.parse(stored) as AuthUser;
    setUser(u);
    // Patients cannot upload recordings — redirect to dashboard
    if (u.role === "patient") {
      toast.error("Patients cannot upload recordings. Only clinicians can process audio.");
      router.push("/dashboard");
    }
  }, [router]);

  // ── Recording timer ───────────────────────────────────────────
  useEffect(() => {
    if (!recording) { setRecordSeconds(0); return; }
    const iv = setInterval(() => setRecordSeconds(s => s + 1), 1000);
    return () => clearInterval(iv);
  }, [recording]);

  // ── Dropzone ──────────────────────────────────────────────────
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && /\.(mp3|wav|m4a|webm|ogg)$/i.test(f.name)) setFile(f);
    else toast.error("Please upload an audio file (.mp3, .wav, .m4a, .webm)");
  }, []);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  // ── Live Recording with Waveform ─────────────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Set up audio analyzer for waveform
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      analyser.fftSize = 128;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      
      // Start waveform animation
      const updateWaveform = () => {
        if (analyserRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
          analyserRef.current.getByteFrequencyData(dataArray);
          const normalized = Array.from(dataArray).slice(0, 64).map(v => v / 255);
          setWaveformData(normalized);
        }
        animationRef.current = requestAnimationFrame(updateWaveform);
      };
      updateWaveform();
      
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const f = new File([blob], `live-recording-${Date.now()}.webm`, { type: "audio/webm" });
        setFile(f);
        stream.getTracks().forEach(t => t.stop());
        toast.success("Recording saved — ready to process");
      };
      mr.start(100);
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch {
      toast.error("Microphone access denied. Please allow microphone access.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
    
    // Clean up audio context and animation
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setWaveformData(new Array(64).fill(0));
  };

  // ── Process pipeline ──────────────────────────────────────────
  const process = async () => {
    // For demo mode, use the selected demo sample's transcript
    const isDemo = mode === "demo" && selectedDemo;
    const demoSample = isDemo ? DEMO_SAMPLES.find(s => s.id === selectedDemo) : null;
    
    if (!file && !isDemo) return;
    setErrorMsg("");
    
    try {
      setStage("uploading");
      await new Promise(r => setTimeout(r, 600));
      
      setStage("transcribing");
      
      let tr: TranscribeResponse;
      
      if (isDemo && demoSample) {
        // Simulate transcription for demo
        await new Promise(r => setTimeout(r, 1200));
        tr = {
          transcript: demoSample.transcript,
          redacted_transcript: demoSample.transcript.replace(/\b(John|Jane|Smith|Johnson|Dr\.?\s+\w+)\b/gi, "[REDACTED]"),
          redaction_log: [
            { entity_type: "PERSON", start: 0, end: 10, replacement: "[REDACTED]" },
          ],
          segments: [],
          duration: 180,
        };
      } else {
        tr = await transcribeAudio(file!);
      }
      setTranscribeResult(tr);

      setStage("redacting");
      await new Promise(r => setTimeout(r, 800));

      setStage("extracting");
      const ar = await analyzeTranscript({
        transcript: tr.redacted_transcript,
        visit_date: visitDate,
        visit_type: visitType,
        tags: tags.split(",").map(t => t.trim()).filter(Boolean),
      });
      setAnalyzeResult(ar);

      setStage("scoring");
      await new Promise(r => setTimeout(r, 600));

      setStage("done");

      // Add to pending approvals queue (clinician must approve before patient sees it)
      const pending = JSON.parse(localStorage.getItem("medsift_pending") || "[]") as number[];
      if (!pending.includes(ar.visit_id)) {
        pending.push(ar.visit_id);
        localStorage.setItem("medsift_pending", JSON.stringify(pending));
      }

      toast.success("Processing complete! Awaiting clinician approval.");
    } catch (err) {
      setStage("error");
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      toast.error("Processing failed: " + msg);
    }
  };

  const handleExportPDF = async () => {
    if (!analyzeResult) return;
    setExportLoading(true);
    try {
      const blob = await exportPDF(analyzeResult.visit_id);
      downloadPDF(blob, `visit-${analyzeResult.visit_id}-summary.pdf`);
      toast.success("PDF downloaded!");
    } catch {
      toast.error("PDF export failed");
    } finally {
      setExportLoading(false);
    }
  };

  const riskColor = analyzeResult?.risk_assessment?.risk_level === "high"
    ? "text-red-600" : analyzeResult?.risk_assessment?.risk_level === "medium"
    ? "text-amber-600" : "text-green-600";

  const riskBg = analyzeResult?.risk_assessment?.risk_level === "high"
    ? "bg-red-50 border-red-200" : analyzeResult?.risk_assessment?.risk_level === "medium"
    ? "bg-amber-50 border-amber-200" : "bg-green-50 border-green-200";

  const fmtTime = (s: number) => `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Process New Recording</h1>
        <p className="text-muted-foreground text-sm mt-1">Upload a file or use live recording to run the full MedSift pipeline.</p>
      </div>

      {stage === "idle" && (
        <>
          {/* Mode toggle */}
          <div className="inline-flex rounded-xl border bg-muted p-1 mb-6">
            <button
              onClick={() => { setMode("file"); setFile(null); setSelectedDemo(null); }}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${mode === "file" ? "bg-white shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              <span className="flex items-center gap-2"><Upload className="h-4 w-4" /> Upload File</span>
            </button>
            <button
              onClick={() => { setMode("live"); setFile(null); setSelectedDemo(null); }}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${mode === "live" ? "bg-white shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              <span className="flex items-center gap-2"><Mic className="h-4 w-4" /> Live Recording</span>
            </button>
            <button
              onClick={() => { setMode("demo"); setFile(null); setSelectedDemo(null); }}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${mode === "demo" ? "bg-white shadow text-foreground" : "text-muted-foreground hover:text-foreground"}`}
            >
              <span className="flex items-center gap-2"><Play className="h-4 w-4" /> Demo Samples</span>
            </button>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* File upload dropzone */}
            {mode === "file" && (
              <div className="md:col-span-2">
                <div
                  onDrop={onDrop}
                  onDragOver={e => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onClick={() => inputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center cursor-pointer transition-colors ${
                    dragging ? "border-primary bg-primary/5" : file ? "border-green-400 bg-green-50" : "border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/50"
                  }`}
                >
                  <input ref={inputRef} type="file" accept=".mp3,.wav,.m4a,.webm,.ogg" className="hidden" onChange={onFileChange} />
                  {file ? (
                    <>
                      <FileAudio className="h-12 w-12 text-green-500 mb-3" />
                      <p className="font-semibold text-green-700">{file.name}</p>
                      <p className="text-sm text-muted-foreground mt-1">{(file.size / 1024 / 1024).toFixed(1)} MB · Click to change</p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-12 w-12 text-muted-foreground mb-3" />
                      <p className="font-semibold">Drop audio file here</p>
                      <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
                      <p className="text-xs text-muted-foreground/70 mt-3">.mp3 · .wav · .m4a · .webm</p>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Live recording panel */}
            {mode === "live" && (
              <div className="md:col-span-2">
                <div className="border-2 rounded-2xl p-8 flex flex-col items-center justify-center gap-6"
                  style={{ borderColor: recording ? "#dc2626" : "#e2e8f0", background: recording ? "rgba(220,38,38,0.03)" : "transparent" }}>

                  {/* Recording indicator */}
                  {recording && (
                    <div className="flex items-center gap-2 text-red-600 font-semibold animate-pulse">
                      <Radio className="h-5 w-5" />
                      <span>Recording in progress</span>
                    </div>
                  )}

                  {/* Live Waveform Visualization */}
                  <div className="w-full max-w-md h-24 flex items-center justify-center gap-[2px] px-4">
                    {waveformData.map((value, index) => (
                      <div
                        key={index}
                        className="w-[2px] rounded-full transition-all duration-75"
                        style={{
                          height: recording ? `${Math.max(4, value * 100)}%` : '4%',
                          backgroundColor: recording ? '#dc2626' : '#e2e8f0',
                          opacity: recording ? 0.7 + value * 0.3 : 0.3,
                        }}
                      />
                    ))}
                  </div>

                  {/* Timer */}
                  <div className="text-5xl font-black font-mono" style={{ color: recording ? "#dc2626" : "#94a3b8" }}>
                    {fmtTime(recordSeconds)}
                  </div>

                  {/* Record / Stop button */}
                  {!recording ? (
                    <Button
                      size="lg"
                      onClick={startRecording}
                      className="gap-2 px-8 text-white"
                      style={{ background: "#dc2626", boxShadow: "0 4px 16px rgba(220,38,38,0.3)" }}
                    >
                      <Mic className="h-5 w-5" /> Start Recording
                    </Button>
                  ) : (
                    <Button
                      size="lg"
                      onClick={stopRecording}
                      variant="outline"
                      className="gap-2 px-8 border-red-400 text-red-600 hover:bg-red-50"
                    >
                      <Square className="h-5 w-5 fill-current" /> Stop Recording
                    </Button>
                  )}

                  {/* Recorded file ready indicator */}
                  {file && !recording && (
                    <div className="flex items-center gap-2 text-green-600 text-sm font-medium bg-green-50 border border-green-200 rounded-xl px-4 py-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Recorded: {file.name} ({(file.size / 1024).toFixed(0)} KB)</span>
                    </div>
                  )}

                  {!recording && !file && (
                    <p className="text-sm text-muted-foreground">Press the button above to start recording the consultation</p>
                  )}
                </div>
              </div>
            )}

            {/* Demo samples panel */}
            {mode === "demo" && (
              <div className="md:col-span-2">
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground mb-4">
                    Select a pre-recorded demo sample to test the MedSift pipeline without uploading your own audio.
                  </p>
                  {DEMO_SAMPLES.map((sample) => (
                    <div
                      key={sample.id}
                      onClick={() => {
                        setSelectedDemo(sample.id);
                        setVisitType(sample.title.toLowerCase().includes("urgent") ? "emergency" : 
                                    sample.title.toLowerCase().includes("follow") ? "follow-up" : "routine checkup");
                        setTags(sample.tags.join(", "));
                      }}
                      className={`border-2 rounded-2xl p-4 cursor-pointer transition-all ${
                        selectedDemo === sample.id 
                          ? "border-[#0ea5e9] bg-[#0ea5e9]/5 shadow-md" 
                          : "border-gray-200 hover:border-[#0ea5e9]/50 hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-gray-900">{sample.title}</h3>
                            {selectedDemo === sample.id && (
                              <CheckCircle2 className="h-5 w-5 text-[#0ea5e9]" />
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{sample.description}</p>
                          <div className="flex items-center gap-3">
                            <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                              <Clock className="h-3 w-3" />
                              {sample.duration}
                            </span>
                            <div className="flex gap-1.5">
                              {sample.tags.slice(0, 2).map((tag) => (
                                <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="shrink-0">
                          <Button
                            size="sm"
                            variant={selectedDemo === sample.id ? "default" : "outline"}
                            className={`gap-1.5 ${selectedDemo === sample.id ? "bg-[#0ea5e9] hover:bg-[#0284c7]" : ""}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedDemo(sample.id);
                              setVisitType(sample.title.toLowerCase().includes("urgent") ? "emergency" : 
                                          sample.title.toLowerCase().includes("follow") ? "follow-up" : "routine checkup");
                              setTags(sample.tags.join(", "));
                            }}
                          >
                            <Play className="h-3 w-3" />
                            {selectedDemo === sample.id ? "Selected" : "Select"}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata + submit */}
            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Visit Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <Label className="text-xs">Visit Date</Label>
                    <Input type="date" value={visitDate} onChange={e => setVisitDate(e.target.value)} className="mt-1 text-sm" />
                  </div>
                  <div>
                    <Label className="text-xs">Visit Type</Label>
                    <select
                      value={visitType}
                      onChange={e => setVisitType(e.target.value)}
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option>routine checkup</option>
                      <option>follow-up</option>
                      <option>specialist</option>
                      <option>emergency</option>
                      <option>telehealth</option>
                    </select>
                  </div>
                  <div>
                    <Label className="text-xs">Tags (comma-separated)</Label>
                    <Input
                      placeholder="diabetes, hypertension"
                      value={tags}
                      onChange={e => setTags(e.target.value)}
                      className="mt-1 text-sm"
                    />
                  </div>
                </CardContent>
              </Card>

              <Button
                onClick={process}
                disabled={(mode !== "demo" && !file) || recording || (mode === "demo" && !selectedDemo)}
                className="w-full gap-2 bg-[#0ea5e9] hover:bg-[#0284c7]"
              >
                <Brain className="h-4 w-4" /> 
                {mode === "demo" ? "Run Demo Pipeline" : "Run Pipeline"}
              </Button>

              {/* Selected demo indicator */}
              {mode === "demo" && selectedDemo && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-[#0ea5e9]/10 border border-[#0ea5e9]/20">
                  <CheckCircle2 className="h-4 w-4 text-[#0ea5e9]" />
                  <span className="text-sm text-[#0ea5e9] font-medium">
                    Ready: {DEMO_SAMPLES.find(s => s.id === selectedDemo)?.title}
                  </span>
                </div>
              )}

              {/* How it works sidebar */}
              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="p-4">
                  <p className="text-xs font-bold text-blue-800 mb-2">How it works:</p>
                  <ol className="text-xs text-blue-700 space-y-1.5 list-decimal list-inside">
                    <li>Audio → Whisper transcribes it</li>
                    <li>PHI is automatically redacted</li>
                    <li>LLM extracts care plan + SOAP note</li>
                    <li>Risk scoring identifies red flags</li>
                    <li>Clinical trials &amp; literature are searched</li>
                  </ol>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}

      {/* ── Processing stages - Horizontal Timeline ──────────────────────────────────── */}
      {stage !== "idle" && stage !== "done" && stage !== "error" && (
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Processing Your Recording</h2>
            <p className="text-gray-500">Running MedSift AI pipeline...</p>
          </div>

          {/* Horizontal Timeline */}
          <div className="relative">
            {/* Progress bar background */}
            <div className="absolute top-8 left-0 right-0 h-1 bg-gray-200 rounded-full mx-12" />
            
            {/* Progress bar fill */}
            <div 
              className="absolute top-8 left-0 h-1 bg-[#0ea5e9] rounded-full mx-12 transition-all duration-700 ease-out"
              style={{ width: `calc(${((stageIndex(stage) + 1) / STAGES.length) * 100}% - 96px)` }}
            />

            {/* Timeline steps */}
            <div className="relative flex justify-between">
              {STAGES.map((s, i) => {
                const idx = stageIndex(s.key);
                const cur = stageIndex(stage);
                const isDone = cur > idx;
                const isActive = cur === idx;
                
                return (
                  <div key={s.key} className="flex flex-col items-center" style={{ width: `${100 / STAGES.length}%` }}>
                    {/* Step indicator dot */}
                    <div className={`relative z-10 h-16 w-16 rounded-full flex items-center justify-center transition-all duration-500 ${
                      isDone 
                        ? "bg-[#0ea5e9]" 
                        : isActive 
                          ? "bg-[#0ea5e9] ring-4 ring-[#0ea5e9]/20" 
                          : "bg-gray-100 border-2 border-gray-200"
                    }`}>
                      {isDone ? (
                        <CheckCircle2 className="h-7 w-7 text-white" />
                      ) : isActive ? (
                        <div className="relative">
                          <s.icon className="h-7 w-7 text-white" />
                          <div className="absolute -inset-1 animate-ping opacity-30">
                            <div className="h-full w-full rounded-full bg-white" />
                          </div>
                        </div>
                      ) : (
                        <s.icon className="h-7 w-7 text-gray-400" />
                      )}
                    </div>

                    {/* Step label */}
                    <div className="mt-4 text-center">
                      <p className={`text-xs font-semibold mb-1 ${
                        isDone ? "text-[#0ea5e9]" : isActive ? "text-[#0ea5e9]" : "text-gray-400"
                      }`}>
                        Step {String(i + 1).padStart(2, '0')}
                      </p>
                      <p className={`font-semibold text-sm mb-1 ${
                        isDone || isActive ? "text-gray-900" : "text-gray-400"
                      }`}>
                        {s.label.split(' ')[0]}
                      </p>
                      <p className={`text-xs leading-tight max-w-[120px] mx-auto ${
                        isDone || isActive ? "text-gray-500" : "text-gray-300"
                      }`}>
                        {s.sub}
                      </p>
                      
                      {/* Status indicator */}
                      {isActive && (
                        <div className="mt-2 flex items-center justify-center gap-1">
                          <div className="flex gap-0.5">
                            <div className="h-1.5 w-1.5 rounded-full bg-[#0ea5e9] animate-bounce" style={{ animationDelay: "0ms" }} />
                            <div className="h-1.5 w-1.5 rounded-full bg-[#0ea5e9] animate-bounce" style={{ animationDelay: "150ms" }} />
                            <div className="h-1.5 w-1.5 rounded-full bg-[#0ea5e9] animate-bounce" style={{ animationDelay: "300ms" }} />
                          </div>
                        </div>
                      )}
                      {isDone && (
                        <p className="mt-2 text-xs text-green-600 font-medium">Complete</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Bottom info card */}
          <Card className="mt-12 border-gray-100">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <ShieldCheck className="h-4 w-4 text-green-500" />
                    <span>All processing happens locally</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span>Secure</span>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {Math.round(((stageIndex(stage) + 1) / STAGES.length) * 100)}% complete • ~{Math.max(0, (STAGES.length - stageIndex(stage) - 1) * 5)}s remaining
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Shimmer animation style */}
      <style jsx global>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>

      {/* ── Error ─────────────────────────────────────────────── */}
      {stage === "error" && (
        <Card className="max-w-xl mx-auto border-red-200 bg-red-50">
          <CardContent className="pt-6 flex gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-red-700">Processing failed</p>
              <p className="text-sm text-red-600 mt-1">{errorMsg}</p>
              <Button variant="outline" className="mt-4" onClick={() => setStage("idle")}>Try again</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Results ───────────────────────────────────────────── */}
      {stage === "done" && analyzeResult && transcribeResult && (
        <div className="space-y-6">
          {/* Approval notice banner */}
          <div className="flex items-start gap-3 p-4 rounded-2xl border bg-amber-50 border-amber-200">
            <Clock className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-amber-800">Awaiting clinician approval</p>
              <p className="text-sm text-amber-700 mt-0.5">
                This summary has been processed and is pending review. Once a clinician approves it, the patient will be able to view it in their portal.
              </p>
            </div>
          </div>

          {/* Summary header */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl border bg-card">
            <div className="flex items-center gap-4">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
              <div>
                <p className="font-semibold">Processing complete</p>
                <p className="text-sm text-muted-foreground">
                  {transcribeResult.duration.toFixed(0)}s audio · {transcribeResult.redaction_log.length} PHI items redacted
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`px-4 py-2 rounded-xl border text-sm font-bold ${riskBg} ${riskColor}`}>
                Risk: {analyzeResult.risk_assessment.risk_score}/100 · {analyzeResult.risk_assessment.risk_level.toUpperCase()}
              </div>
              <Button variant="outline" size="sm" onClick={handleExportPDF} disabled={exportLoading} className="gap-1.5">
                <Download className="h-4 w-4" /> {exportLoading ? "Generating…" : "PDF"}
              </Button>
              <Button size="sm" className="gap-1.5" onClick={() => router.push(`/visits/${analyzeResult.visit_id}`)}>
                <Eye className="h-4 w-4" /> Full Details
              </Button>
            </div>
          </div>

          {/* Result tabs */}
          <div className="flex gap-2 border-b pb-0">
            {(["care-plan", "soap", "risk", "transcript"] as const).map(t => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {t === "care-plan" ? "Care Plan" : t === "soap" ? "SOAP Note" : t === "risk" ? "Risk Assessment" : "Transcript"}
              </button>
            ))}
          </div>

          {/* Care Plan tab */}
          {activeTab === "care-plan" && (
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="md:col-span-2">
                <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">Visit Summary</CardTitle></CardHeader>
                <CardContent><p className="text-sm leading-relaxed">{analyzeResult.patient_summary.visit_summary}</p></CardContent>
              </Card>
              {analyzeResult.patient_summary.medications.length > 0 && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">💊 Medications</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    {analyzeResult.patient_summary.medications.map((med, i) => (
                      <div key={i} className="border rounded-lg p-3 text-sm">
                        <p className="font-semibold">{med.name} <span className="font-normal text-muted-foreground">· {med.dose} · {med.frequency}</span></p>
                        <p className="text-muted-foreground mt-1">{med.instructions}</p>
                        {med.evidence && <p className="text-xs text-blue-600 mt-1 italic">"{med.evidence}"</p>}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
              {analyzeResult.patient_summary.tests_ordered.length > 0 && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">🔬 Tests Ordered</CardTitle></CardHeader>
                  <CardContent className="space-y-2">
                    {analyzeResult.patient_summary.tests_ordered.map((t, i) => (
                      <div key={i} className="border rounded-lg p-3 text-sm">
                        <p className="font-semibold">{t.test_name}</p>
                        <p className="text-muted-foreground">{t.instructions} · {t.timeline}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
              {analyzeResult.patient_summary.red_flags_for_patient.length > 0 && (
                <Card className="border-red-200 bg-red-50 md:col-span-2">
                  <CardHeader className="pb-2"><CardTitle className="text-sm text-red-700">⚠️ When to Seek Urgent Care</CardTitle></CardHeader>
                  <CardContent className="space-y-2">
                    {analyzeResult.patient_summary.red_flags_for_patient.map((rf, i) => (
                      <p key={i} className="text-sm text-red-700 font-medium">• {rf.warning}</p>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* SOAP Note tab */}
          {activeTab === "soap" && (
            <div className="grid md:grid-cols-2 gap-4">
              {(["subjective", "objective", "assessment", "plan"] as const).map((section) => {
                const data = analyzeResult.clinician_note.soap_note[section];
                const fields = {
                  subjective: [
                    { label: "CC", val: data.chief_complaint },
                    { label: "HPI", val: data.history_of_present_illness },
                    { label: "ROS", val: data.review_of_systems },
                  ],
                  objective: [
                    { label: "Vitals", val: data.vitals },
                    { label: "PE", val: data.physical_exam_findings },
                  ],
                  assessment: [
                    { label: "Diagnoses", val: data.diagnoses?.join(", ") },
                    { label: "Impression", val: data.clinical_impression },
                  ],
                  plan: [
                    { label: "Follow-up", val: data.follow_up },
                    { label: "Education", val: data.patient_education },
                  ],
                }[section];
                return (
                  <Card key={section}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
                        {section === "subjective" ? "S — Subjective" : section === "objective" ? "O — Objective" : section === "assessment" ? "A — Assessment" : "P — Plan"}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-2">
                      {fields.map(({ label, val }) => (
                        <p key={label}>
                          <strong>{label}:</strong>{" "}
                          {val ? (
                            <span>{val}</span>
                          ) : (
                            <span className="text-red-500 italic font-medium">Not provided</span>
                          )}
                        </p>
                      ))}
                      {data.evidence && data.evidence.length > 0 && (
                        <div className="text-xs text-blue-600 italic space-y-1 border-t pt-2 mt-2">
                          {data.evidence.slice(0, 2).map((e, i) => <p key={i}>"{e}"</p>)}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Risk tab */}
          {activeTab === "risk" && (
            <div className="space-y-4">
              <Card className={`border ${riskBg}`}>
                <CardContent className="pt-6 flex items-center gap-6">
                  <div className="text-center">
                    <div className={`text-5xl font-black ${riskColor}`}>{analyzeResult.risk_assessment.risk_score}</div>
                    <div className="text-xs text-muted-foreground mt-1">/ 100</div>
                  </div>
                  <Separator orientation="vertical" className="h-16" />
                  <div>
                    <p className={`text-xl font-bold ${riskColor} capitalize`}>{analyzeResult.risk_assessment.risk_level} Risk</p>
                    <p className="text-sm text-muted-foreground">{analyzeResult.risk_assessment.total_factors_detected} risk factors detected</p>
                    <p className="text-xs text-muted-foreground mt-2">⚠️ This is not a medical diagnosis.</p>
                  </div>
                </CardContent>
              </Card>
              {analyzeResult.risk_assessment.red_flags.length > 0 && (
                <Card className="border-red-200">
                  <CardHeader className="pb-2"><CardTitle className="text-sm text-red-700">🚨 Red Flags</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    {analyzeResult.risk_assessment.red_flags.map((rf, i) => (
                      <div key={i} className="border border-red-200 rounded-lg p-3 bg-red-50">
                        <p className="text-sm font-semibold text-red-700">{rf.flag}</p>
                        <p className="text-xs text-muted-foreground mt-1">{rf.recommended_action}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Risk Factors</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {analyzeResult.risk_assessment.risk_factors.map((rf, i) => (
                    <div key={i} className="flex items-start justify-between gap-2 text-sm">
                      <span>{rf.factor}</span>
                      <Badge variant="outline">+{rf.points}</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Transcript tab */}
          {activeTab === "transcript" && (
            <div className="grid md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Original Transcript</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">{transcribeResult.transcript}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-green-500" /> De-identified Transcript
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">{transcribeResult.redacted_transcript}</p>
                  <div className="mt-3 pt-3 border-t">
                    <p className="text-xs text-muted-foreground">Redacted: {transcribeResult.redaction_log.length} items</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button variant="outline" onClick={() => { setStage("idle"); setFile(null); setTranscribeResult(null); setAnalyzeResult(null); }}>
              Process another
            </Button>
            {user?.role === "clinician" && (
              <Button onClick={() => router.push(`/visits/${analyzeResult.visit_id}`)} className="gap-2">
                <Eye className="h-4 w-4" /> Review &amp; Approve <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}