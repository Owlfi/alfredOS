"use client";

import React, { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Search,
  Bug,
  Activity,
  Brain,
  Database,
  Target,
  FileText,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  TerminalSquare,
} from "lucide-react";

type SystemState = {
  appName: string;
  mode: string;
  llmStatus: string;
  model: string;
  lastUpdated: string;
};

type LatestExchange = {
  source: string;
  userMessage: string;
  assistantReply: string;
  timestamp: string;
};

type ProcessorState = {
  rawMessage: string;
  simplifiedMessage: string;
  category: string;
  relevanceScore: number;
  strategicImportance: number;
  route: string;
};

type MemoryState = {
  rawJournalPath: string;
  processedJournalPath: string;
  currentFocusPath: string;
  longTermMemoryPath: string;
  taskListPath: string;
  systemModePath: string;
  goalSessionPath: string;
};

type GoalModeState = {
  active: boolean;
  capturedMessages: string[];
};

type DashboardState = {
  system: SystemState;
  latestExchange: LatestExchange;
  processor: ProcessorState;
  memory: MemoryState;
  goalMode: GoalModeState;
  logs: string[];
};

const fallbackState: DashboardState = {
  system: {
    appName: "AI-fie V1.1",
    mode: "unknown",
    llmStatus: "unknown",
    model: "llama3.1:8b",
    lastUpdated: new Date().toISOString(),
  },
  latestExchange: {
    source: "web",
    userMessage: "No live prompt loaded yet.",
    assistantReply: "Connect the debug endpoints to load live data.",
    timestamp: new Date().toISOString(),
  },
  processor: {
    rawMessage: "No processor data loaded yet.",
    simplifiedMessage: "No processor data loaded yet.",
    category: "general",
    relevanceScore: 0,
    strategicImportance: 0,
    route: "ignore",
  },
  memory: {
    rawJournalPath: "data/journal/raw_journal.jsonl",
    processedJournalPath: "data/memory/processed_journal.jsonl",
    currentFocusPath: "data/memory/current-focus.md",
    longTermMemoryPath: "data/memory/long-term-memory.md",
    taskListPath: "data/memory/task-list.md",
    systemModePath: "data/memory/system_mode.json",
    goalSessionPath: "data/memory/goal_update_session.json",
  },
  goalMode: {
    active: false,
    capturedMessages: [],
  },
  logs: ["[DASHBOARD] Waiting for live logs..."],
};

function StatusBadge({ value }: { value: string }) {
  const tone =
    value === "connected" || value === "normal"
      ? "bg-green-100 text-green-800 border-green-200"
      : value === "goal_update"
      ? "bg-amber-100 text-amber-800 border-amber-200"
      : "bg-slate-100 text-slate-800 border-slate-200";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-medium ${tone}`}
    >
      {value}
    </span>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
}) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm text-slate-500">{title}</div>
            <div className="mt-1 text-2xl font-semibold tracking-tight">{value}</div>
            {subtitle ? <div className="mt-1 text-xs text-slate-500">{subtitle}</div> : null}
          </div>
          <div className="rounded-2xl bg-slate-100 p-2">
            <Icon className="h-5 w-5 text-slate-700" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-xs text-slate-100">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export default function AIFieDebugDashboard() {
  const [state, setState] = useState<DashboardState>(fallbackState);
  const [search, setSearch] = useState<string>("");
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const loadDashboardData = async () => {
    setLoading(true);
    setError("");

    try {
      const [stateRes, latestRes, logsRes] = await Promise.all([
        fetch("http://127.0.0.1:8000/debug/state"),
        fetch("http://127.0.0.1:8000/debug/latest"),
        fetch("http://127.0.0.1:8000/debug/logs"),
      ]);

      if (!stateRes.ok || !latestRes.ok || !logsRes.ok) {
        throw new Error("One or more debug endpoints failed to load.");
      }

      const stateData = await stateRes.json();
      const latestData = await latestRes.json();
      const logsData = await logsRes.json();

      setState({
        system: stateData.system ?? fallbackState.system,
        latestExchange: latestData.latestExchange ?? fallbackState.latestExchange,
        processor: latestData.processor ?? fallbackState.processor,
        memory: stateData.memory ?? fallbackState.memory,
        goalMode: stateData.goalMode ?? fallbackState.goalMode,
        logs: logsData.logs ?? fallbackState.logs,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboardData();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      void loadDashboardData();
    }, 4000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const filteredLogs = useMemo(() => {
    if (!search.trim()) return state.logs;
    return state.logs.filter((line) =>
      line.toLowerCase().includes(search.toLowerCase())
    );
  }, [search, state.logs]);

  const lastPromptResponse = {
    prompt: state.latestExchange.userMessage,
    response: state.latestExchange.assistantReply,
    source: state.latestExchange.source,
    timestamp: state.latestExchange.timestamp,
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
              AI-fie V1.1 Debug Dashboard
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              A clean view of the latest exchange, processor output, memory routing,
              and debug details.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="rounded-full px-3 py-1 text-xs">
              Model: {state.system.model}
            </Badge>
            <StatusBadge value={state.system.mode} />
            <StatusBadge value={state.system.llmStatus} />
            <Button variant="outline" className="rounded-2xl" onClick={() => void loadDashboardData()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh Now
            </Button>
            <Button
              variant="outline"
              className="rounded-2xl"
              onClick={() => setAutoRefresh((v) => !v)}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {autoRefresh ? "Stop Refresh" : "Auto Refresh"}
            </Button>
          </div>
        </div>

        {error ? (
          <Alert className="rounded-2xl border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Dashboard load issue</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            title="System Mode"
            value={state.system.mode}
            subtitle="Current control state"
            icon={Target}
          />
          <MetricCard
            title="LLM Status"
            value={state.system.llmStatus}
            subtitle={loading ? "Refreshing..." : "Ollama connection"}
            icon={Brain}
          />
          <MetricCard
            title="Latest Source"
            value={state.latestExchange.source}
            subtitle={state.latestExchange.timestamp}
            icon={Activity}
          />
          <MetricCard
            title="Goal Messages"
            value={String(state.goalMode.capturedMessages.length)}
            subtitle="Messages in current session"
            icon={Database}
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-900">
                <FileText className="h-5 w-5" />
                Latest Prompt and Response
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border bg-white p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-sm font-medium text-slate-700">Latest Prompt</div>
                  <Badge variant="secondary" className="rounded-full">
                    {lastPromptResponse.source}
                  </Badge>
                </div>
                <p className="text-sm leading-7 text-slate-800">
                  {lastPromptResponse.prompt}
                </p>
              </div>
              <div className="rounded-2xl border bg-white p-4">
                <div className="mb-2 text-sm font-medium text-slate-700">
                  Latest Response
                </div>
                <p className="text-sm leading-7 text-slate-800">
                  {lastPromptResponse.response}
                </p>
              </div>
              <div className="text-xs text-slate-500">
                Last updated: {state.system.lastUpdated}
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-900">
                <Bug className="h-5 w-5" />
                Quick Debug Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Alert className="rounded-2xl border-green-200 bg-green-50">
                <CheckCircle2 className="h-4 w-4" />
                <AlertTitle>What is working</AlertTitle>
                <AlertDescription>
                  Chat route is active, journaling is writing, and the LLM status is
                  visible here.
                </AlertDescription>
              </Alert>
              <Alert className="rounded-2xl border-amber-200 bg-amber-50">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>What to watch</AlertTitle>
                <AlertDescription>
                  Goal mode can intentionally bypass parts of the normal pipeline. That
                  is expected while updating goals.
                </AlertDescription>
              </Alert>
              <div className="rounded-2xl border bg-white p-4">
                <div className="font-medium text-slate-800">Current route</div>
                <div className="mt-1 text-slate-600">{state.processor.route}</div>
              </div>
              <div className="rounded-2xl border bg-white p-4">
                <div className="font-medium text-slate-800">Current category</div>
                <div className="mt-1 text-slate-600">{state.processor.category}</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="processor" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4 rounded-2xl bg-white shadow-sm">
            <TabsTrigger value="processor" className="rounded-2xl">
              Processor
            </TabsTrigger>
            <TabsTrigger value="memory" className="rounded-2xl">
              Memory
            </TabsTrigger>
            <TabsTrigger value="goal" className="rounded-2xl">
              Goal Mode
            </TabsTrigger>
            <TabsTrigger value="logs" className="rounded-2xl">
              Logs
            </TabsTrigger>
          </TabsList>

          <TabsContent value="processor">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5" />
                    Processor Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="rounded-2xl border bg-white p-4">
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Raw Message
                    </div>
                    <p className="mt-2 leading-7 text-slate-800">
                      {state.processor.rawMessage}
                    </p>
                  </div>
                  <div className="rounded-2xl border bg-white p-4">
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Simplified Message
                    </div>
                    <p className="mt-2 leading-7 text-slate-800">
                      {state.processor.simplifiedMessage}
                    </p>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-2xl border bg-white p-4">
                      <div className="text-xs text-slate-500">Category</div>
                      <div className="mt-2 font-medium text-slate-900">
                        {state.processor.category}
                      </div>
                    </div>
                    <div className="rounded-2xl border bg-white p-4">
                      <div className="text-xs text-slate-500">Relevance</div>
                      <div className="mt-2 font-medium text-slate-900">
                        {state.processor.relevanceScore}
                      </div>
                    </div>
                    <div className="rounded-2xl border bg-white p-4">
                      <div className="text-xs text-slate-500">Importance</div>
                      <div className="mt-2 font-medium text-slate-900">
                        {state.processor.strategicImportance}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle>Processor JSON</CardTitle>
                </CardHeader>
                <CardContent>
                  <JsonBlock data={state.processor} />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="memory">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Memory Files
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {Object.entries(state.memory).map(([key, value]) => (
                    <div key={key} className="rounded-2xl border bg-white p-4">
                      <div className="text-xs uppercase tracking-wide text-slate-500">
                        {key}
                      </div>
                      <div className="mt-2 font-mono text-xs text-slate-800">
                        {value}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle>Routing Overview</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="rounded-2xl border bg-white p-4">
                    <div className="font-medium text-slate-900">Current Decision</div>
                    <p className="mt-2 text-slate-700">
                      This message has been classified as{" "}
                      <strong>{state.processor.category}</strong> and routed to{" "}
                      <strong>{state.processor.route}</strong>.
                    </p>
                  </div>
                  <Accordion type="single" collapsible className="w-full">
                    <AccordionItem value="raw">
                      <AccordionTrigger>What each file is for</AccordionTrigger>
                      <AccordionContent className="space-y-2 text-slate-600">
                        <p>
                          <strong>raw_journal.jsonl</strong> stores the untouched source
                          of truth.
                        </p>
                        <p>
                          <strong>processed_journal.jsonl</strong> stores the processor's
                          structured result.
                        </p>
                        <p>
                          <strong>current-focus.md</strong> stores live priorities and
                          direction.
                        </p>
                        <p>
                          <strong>long-term-memory.md</strong> stores durable ideas and
                          reflections.
                        </p>
                        <p>
                          <strong>task-list.md</strong> stores actionable items.
                        </p>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="goal">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5" />
                    Goal Mode Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="rounded-2xl border bg-white p-4">
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Active
                    </div>
                    <div className="mt-2 font-medium text-slate-900">
                      {String(state.goalMode.active)}
                    </div>
                  </div>
                  <div className="rounded-2xl border bg-white p-4">
                    <div className="text-xs uppercase tracking-wide text-slate-500">
                      Captured messages
                    </div>
                    <div className="mt-3 space-y-2">
                      {state.goalMode.capturedMessages.length > 0 ? (
                        state.goalMode.capturedMessages.map((msg, idx) => (
                          <div key={idx} className="rounded-xl bg-slate-50 p-3 text-slate-700">
                            {msg}
                          </div>
                        ))
                      ) : (
                        <div className="rounded-xl bg-slate-50 p-3 text-slate-500">
                          No active goal session messages.
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle>System Mode JSON</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <JsonBlock data={{ mode: state.system.mode }} />
                  <JsonBlock data={state.goalMode} />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="logs">
            <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Search className="h-5 w-5" />
                    Log Search
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input
                    value={search}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      setSearch(e.target.value)
                    }
                    placeholder="Search logs..."
                    className="rounded-2xl"
                  />
                  <Separator />
                  <div className="text-sm text-slate-600">
                    Showing {filteredLogs.length} of {state.logs.length} log lines.
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-2xl shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TerminalSquare className="h-5 w-5" />
                    Debug Logs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[420px] rounded-2xl bg-slate-950 p-4">
                    <div className="space-y-2 font-mono text-xs text-slate-100">
                      {filteredLogs.map((line, idx) => (
                        <div key={idx}>{line}</div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}