import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Brain,
  Check,
  Copy,
  Database,
  ExternalLink,
  FolderOpen,
  Maximize2,
  Pause,
  Play,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import ForceGraph2D from "react-force-graph-2d";
import type { ForceGraphMethods, NodeObject } from "react-force-graph-2d";
import { Badge } from "@atlas/ui/ui/components/badge";
import { Button } from "@atlas/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@atlas/ui/ui/components/card";
import { Input } from "@atlas/ui/ui/components/input";
import { Spinner } from "@atlas/ui/ui/components/spinner";
import { Toast } from "@atlas/ui/ui/components/toast";
import { useToast } from "@atlas/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type {
  MemoryFact,
  MemoryClaim,
  MemoryDossier,
  MemoryGraphNode,
  MemoryGraphResponse,
  MemoryRecallRawResult,
  MemorySearchResult,
  MemorySummary,
  MemoryLivingStatus,
  MemoryVaultStatus,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const KIND_STYLES: Record<string, { fill: string; stroke: string }> = {
  creator: { fill: "#8f95dc", stroke: "#6e74c9" },
  memory: { fill: "#5ee7b8", stroke: "#24b985" },
  user: { fill: "#8dd7ff", stroke: "#4fb6ee" },
  session: { fill: "#ffd36f", stroke: "#e4a82b" },
  interaction: { fill: "#ffffff", stroke: "#c7c9e8" },
  fact: { fill: "#b8a6ff", stroke: "#8f83e6" },
  claim: { fill: "#7f86df", stroke: "#5e65c5" },
  dossier: { fill: "#52d3aa", stroke: "#269b79" },
  person: { fill: "#ffb45f", stroke: "#dc8428" },
  project: { fill: "#73c7f1", stroke: "#3a9bc9" },
  organization: { fill: "#f68b9f", stroke: "#cd526b" },
  place: { fill: "#a7d36f", stroke: "#71a536" },
  other: { fill: "#c8cbe7", stroke: "#9096c3" },
  summary: { fill: "#7ddfc1", stroke: "#43b692" },
  topic: { fill: "#ff8a70", stroke: "#df654f" },
};

function formatSyncTime(value?: number | null): string {
  if (!value) return "Never";
  return new Date(value * 1000).toLocaleString();
}

function statEntries(status: MemoryVaultStatus | null): Array<[string, number]> {
  return Object.entries(status?.stats ?? {}).sort(([a], [b]) => a.localeCompare(b));
}

const GRAPH_NODE_KINDS = new Set([
  "creator", "summary", "fact", "topic", "claim", "dossier",
  "person", "project", "organization", "place", "other",
]);

interface GraphNodeDatum extends MemoryGraphNode {
  x?: number;
  y?: number;
}

interface GraphLinkDatum {
  source: string | GraphNodeDatum;
  target: string | GraphNodeDatum;
  type?: string;
}

function GraphPreview({
  graph,
  selected,
  onSelect,
}: {
  graph: MemoryGraphResponse | null;
  selected: string | null;
  onSelect: (node: MemoryGraphNode) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<ForceGraphMethods<GraphNodeDatum, GraphLinkDatum> | undefined>(undefined);
  const [playing, setPlaying] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 840, height: 500 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.max(320, Math.floor(entry.contentRect.width));
      setDimensions({ width, height: Math.max(420, Math.min(620, Math.floor(width * 0.58))) });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const visibleNodes = useMemo(() => {
    const graphNodes = graph?.nodes ?? [];
    const memoryNodes = graphNodes.filter(
      (node) => GRAPH_NODE_KINDS.has(node.kind) && (showHistory || node.status !== "stale"),
    );
    return (memoryNodes.length ? memoryNodes : graphNodes).slice(0, 400);
  }, [graph, showHistory]);
  const byId = useMemo(() => new Map(visibleNodes.map((node) => [node.id, node])), [visibleNodes]);
  const graphData = useMemo(() => ({
    nodes: visibleNodes.map((node) => ({ ...node } as GraphNodeDatum)),
    links: (graph?.edges ?? [])
      .filter((edge) => byId.has(edge.source) && byId.has(edge.target))
      .slice(0, 900)
      .map((edge) => ({ ...edge } as GraphLinkDatum)),
  }), [byId, graph, visibleNodes]);

  useEffect(() => {
    if (playing) graphRef.current?.resumeAnimation();
    else graphRef.current?.pauseAnimation();
  }, [playing]);

  if (!visibleNodes.length) {
    return <div className="flex h-[420px] items-center justify-center text-sm text-muted-foreground">Memory will appear here as Atlas learns.</div>;
  }

  return (
    <div ref={containerRef} className="relative min-h-[420px] overflow-hidden rounded-lg border border-border bg-[#f8f9ff]">
      <div className="absolute right-3 top-3 z-10 flex items-center gap-2 rounded-lg border border-border bg-white/90 p-1 shadow-sm backdrop-blur">
        <Button
          size="sm"
          ghost
          onClick={() => setShowHistory((value) => !value)}
        >
          {showHistory ? "History" : "Current"}
        </Button>
        <Button
          size="icon"
          ghost
          aria-label="Fit memory graph"
          title="Fit graph"
          onClick={() => graphRef.current?.zoomToFit(500, 44)}
        >
          <Maximize2 className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          ghost
          aria-label={playing ? "Pause graph" : "Resume graph"}
          title={playing ? "Pause graph" : "Resume graph"}
          onClick={() => setPlaying((value) => !value)}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
      </div>
      <ForceGraph2D<GraphNodeDatum, GraphLinkDatum>
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        backgroundColor="#f8f9ff"
        nodeId="id"
        nodeVal={(node) => node.kind === "creator" || node.kind === "dossier" ? 10 : node.kind === "person" || node.kind === "project" ? 7 : 4}
        nodeColor={(node) => (KIND_STYLES[node.kind] ?? KIND_STYLES.summary).fill}
        nodeLabel={(node) => `${node.title}${node.status ? ` · ${node.status}` : ""}`}
        linkColor={() => "rgba(111, 119, 205, 0.34)"}
        linkWidth={(link) => link.type === "superseded_by" ? 2.2 : 1.1}
        linkLineDash={(link) => link.type === "superseded_by" ? [4, 3] : null}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={0.92}
        linkLabel={(link) => link.type ?? "related"}
        d3AlphaDecay={0.018}
        d3VelocityDecay={0.28}
        cooldownTime={15000}
        minZoom={0.3}
        maxZoom={8}
        enableNodeDrag
        enablePanInteraction
        enableZoomInteraction
        onNodeClick={(node) => {
          onSelect(node);
          if (typeof node.x === "number" && typeof node.y === "number") {
            graphRef.current?.centerAt(node.x, node.y, 420);
            graphRef.current?.zoom(2.2, 420);
          }
        }}
        nodeCanvasObjectMode={() => "after"}
        nodeCanvasObject={(node: NodeObject<GraphNodeDatum>, context, globalScale) => {
          const active = selected === node.id;
          const alwaysLabel = active || ["creator", "person", "project", "dossier"].includes(node.kind);
          if (!alwaysLabel || typeof node.x !== "number" || typeof node.y !== "number") return;
          const label = node.title.slice(0, 42);
          const fontSize = Math.max(3.5, 12 / globalScale);
          context.font = `600 ${fontSize}px ui-sans-serif, system-ui`;
          context.textAlign = "left";
          context.textBaseline = "middle";
          context.fillStyle = "rgba(248, 249, 255, 0.9)";
          const width = context.measureText(label).width + fontSize;
          context.fillRect(node.x + 5, node.y - fontSize * 0.75, width, fontSize * 1.5);
          context.fillStyle = "#252238";
          context.fillText(label, node.x + 9, node.y);
        }}
      />
    </div>
  );
}

function ResultRow({ result }: { result: MemorySearchResult }) {
  return (
    <div className="min-w-0 rounded-xl border border-border bg-white/70 px-4 py-3 shadow-sm">
      <div className="flex min-w-0 items-center gap-2">
        <Badge tone="secondary">{result.kind}</Badge>
        <div className="min-w-0 truncate text-sm font-semibold text-foreground">
          {result.title}
        </div>
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
        {result.snippet}
      </p>
      <div className="mt-2 flex min-w-0 flex-wrap gap-2 text-[11px] text-muted-foreground">
        {result.session_id && <span className="font-mono">{result.session_id.slice(0, 12)}</span>}
        {result.topics.slice(0, 5).map((topic) => (
          <span key={topic}>#{topic}</span>
        ))}
      </div>
    </div>
  );
}

function FactRow({
  fact,
  actions,
}: {
  fact: MemoryFact;
  actions?: ReactNode;
}) {
  return (
    <div className="min-w-0 rounded-xl border border-border bg-white/80 px-4 py-3 shadow-sm">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Badge tone="secondary">{fact.kind.replace("_", " ")}</Badge>
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
              {fact.status}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-foreground">{fact.text}</p>
        </div>
        {actions && <div className="flex shrink-0 gap-1">{actions}</div>}
      </div>
      <div className="mt-2 flex min-w-0 flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span>importance {fact.importance.toFixed(2)}</span>
        <span>confidence {fact.confidence.toFixed(2)}</span>
        {fact.citation && <span className="font-mono">{fact.citation}</span>}
        {fact.source_session_id && !fact.citation && (
          <span className="font-mono">{fact.source_session_id.slice(0, 12)}</span>
        )}
        {fact.topics.slice(0, 5).map((topic) => (
          <span key={topic}>#{topic}</span>
        ))}
      </div>
    </div>
  );
}

function SummaryRow({
  summary,
  actions,
}: {
  summary: MemorySummary;
  actions?: ReactNode;
}) {
  return (
    <div className="min-w-0 rounded-xl border border-border bg-white/80 px-4 py-3 shadow-sm">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Badge tone="success">summary</Badge>
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
              {summary.status}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-foreground">{summary.text}</p>
        </div>
        {actions && <div className="flex shrink-0 gap-1">{actions}</div>}
      </div>
      <div className="mt-2 flex min-w-0 flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span>confidence {summary.confidence.toFixed(2)}</span>
        {summary.citation && <span className="font-mono">{summary.citation}</span>}
        {summary.source_session_id && !summary.citation && (
          <span className="font-mono">{summary.source_session_id.slice(0, 12)}</span>
        )}
        {summary.topics.slice(0, 5).map((topic) => (
          <span key={topic}>#{topic}</span>
        ))}
      </div>
    </div>
  );
}

function DossierRow({ dossier }: { dossier: MemoryDossier }) {
  return (
    <div className="min-w-0 border border-border bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center gap-2">
        <Badge tone="success">current dossier</Badge>
        <span className="truncate text-sm font-semibold text-foreground">{dossier.title}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-foreground">{dossier.text}</p>
      <div className="mt-2 text-[11px] text-muted-foreground">
        confidence {dossier.confidence.toFixed(2)} · {dossier.claim_ids.length} supporting claims
      </div>
    </div>
  );
}

function ClaimRow({ claim }: { claim: MemoryClaim }) {
  return (
    <div className="min-w-0 border border-border bg-white px-4 py-3 shadow-sm">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Badge tone="secondary">claim</Badge>
        <span className="text-xs font-semibold text-primary">{claim.subject}</span>
        <span className="text-[11px] text-muted-foreground">{claim.predicate.replaceAll("_", " ")}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-foreground">{claim.text}</p>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span>{claim.stateful ? "evolving state" : "durable"}</span>
        <span>confidence {claim.confidence.toFixed(2)}</span>
        {claim.citation && <span className="font-mono">{claim.citation}</span>}
      </div>
    </div>
  );
}

function RawRecallRow({ item }: { item: MemoryRecallRawResult }) {
  return (
    <div className="rounded-xl border border-border bg-white/60 px-4 py-3 text-sm">
      <div className="font-semibold text-foreground">{item.title}</div>
      <p className="mt-1 line-clamp-2 text-muted-foreground">{item.snippet}</p>
      {item.session_id && (
        <div className="mt-2 font-mono text-[11px] text-muted-foreground">
          {item.session_id.slice(0, 18)}
        </div>
      )}
    </div>
  );
}

export default function MemoryPage() {
  const { toast, showToast } = useToast();
  const [status, setStatus] = useState<MemoryVaultStatus | null>(null);
  const [livingStatus, setLivingStatus] = useState<MemoryLivingStatus | null>(null);
  const [graph, setGraph] = useState<MemoryGraphResponse | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [recallQuery, setRecallQuery] = useState("");
  const [recallCurated, setRecallCurated] = useState<MemorySearchResult[]>([]);
  const [recallDossiers, setRecallDossiers] = useState<MemoryDossier[]>([]);
  const [recallClaims, setRecallClaims] = useState<MemoryClaim[]>([]);
  const [recallFacts, setRecallFacts] = useState<MemoryFact[]>([]);
  const [recallSummaries, setRecallSummaries] = useState<MemorySummary[]>([]);
  const [recallRaw, setRecallRaw] = useState<MemoryRecallRawResult[]>([]);
  const [pendingFacts, setPendingFacts] = useState<MemoryFact[]>([]);
  const [pendingSummaries, setPendingSummaries] = useState<MemorySummary[]>([]);
  const [selectedNode, setSelectedNode] = useState<MemoryGraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [consolidating, setConsolidating] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [recalling, setRecalling] = useState(false);

  const loadPendingFacts = useCallback(async () => {
    try {
      const [factsRes, summariesRes] = await Promise.all([
        api.getPendingMemoryFacts(50),
        api.getMemorySummaries("", "pending", 50),
      ]);
      setPendingFacts(factsRes.facts);
      setPendingSummaries(summariesRes.summaries);
    } catch (error) {
      showToast(`Pending memory failed: ${error}`, "error");
    }
  }, [showToast]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, graphRes, livingRes] = await Promise.all([
        api.getMemoryVault(),
        api.getMemoryGraph(),
        api.getLivingMemoryStatus(),
      ]);
      setLivingStatus(livingRes);
      setGraph(graphRes);
      setStatus({
        ...statusRes,
        dirty: graphRes.dirty,
        exists: graphRes.exists,
        last_sync: graphRes.last_sync,
        stats: graphRes.stats,
      });
      setSelectedNode(graphRes.nodes.find((node) => node.kind === "creator") ?? graphRes.nodes[0] ?? null);
      void loadPendingFacts();
    } catch (error) {
      showToast(`Memory load failed: ${error}`, "error");
    } finally {
      setLoading(false);
    }
  }, [loadPendingFacts, showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void Promise.all([api.getMemoryGraph(), api.getLivingMemoryStatus()])
        .then(([graphRes, livingRes]) => {
          setGraph(graphRes);
          setLivingStatus(livingRes);
          setStatus((current) => current ? {
            ...current,
            dirty: graphRes.dirty,
            last_sync: graphRes.last_sync,
            stats: graphRes.stats,
          } : current);
        })
        .catch(() => undefined);
    }, 15000);
    return () => window.clearInterval(timer);
  }, []);

  const sync = async () => {
    setSyncing(true);
    try {
      const graphRes = await api.syncMemoryVault();
      setGraph(graphRes);
      setStatus({
        ok: graphRes.ok,
        vault_path: graphRes.vault_path,
        exists: true,
        dirty: false,
        last_sync: graphRes.last_sync,
        stats: graphRes.stats,
      });
      setSelectedNode(graphRes.nodes.find((node) => node.kind === "creator") ?? graphRes.nodes[0] ?? null);
      showToast("Memory vault synced", "success");
    } catch (error) {
      showToast(`Sync failed: ${error}`, "error");
    } finally {
      setSyncing(false);
    }
  };

  const runSearch = async () => {
    const clean = query.trim();
    if (!clean) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      const res = await api.searchMemory(clean, 30);
      setResults(res.results);
    } catch (error) {
      showToast(`Search failed: ${error}`, "error");
    } finally {
      setSearching(false);
    }
  };

  const runRecall = async () => {
    const clean = recallQuery.trim();
    if (!clean) {
      setRecallCurated([]);
      setRecallDossiers([]);
      setRecallClaims([]);
      setRecallFacts([]);
      setRecallSummaries([]);
      setRecallRaw([]);
      return;
    }
    setRecalling(true);
    try {
      const res = await api.recallMemory(clean, 8);
      setRecallCurated(res.curated ?? []);
      setRecallDossiers(res.dossiers ?? []);
      setRecallClaims(res.claims ?? []);
      setRecallFacts(res.facts);
      setRecallSummaries(res.summaries ?? []);
      setRecallRaw(res.raw_results);
    } catch (error) {
      showToast(`Recall failed: ${error}`, "error");
    } finally {
      setRecalling(false);
    }
  };

  const summarize = async () => {
    setSummarizing(true);
    try {
      const res = await api.summarizeMemory(500);
      showToast(
        `Summarized ${res.sessions} sessions: ${res.summaries} summaries, ${res.facts_created} facts`,
        "success",
      );
      await loadPendingFacts();
      const graphRes = await api.getMemoryGraph();
      setGraph(graphRes);
      setLivingStatus(await api.getLivingMemoryStatus());
      setStatus({
        ok: graphRes.ok,
        vault_path: graphRes.vault_path,
        exists: graphRes.exists,
        dirty: graphRes.dirty,
        last_sync: graphRes.last_sync,
        stats: graphRes.stats,
      });
    } catch (error) {
      showToast(`Summarize failed: ${error}`, "error");
    } finally {
      setSummarizing(false);
    }
  };

  const rebuildEmbeddings = async () => {
    try {
      const res = await api.rebuildMemoryEmbeddings();
      showToast(
        res.backend === "fastembed"
          ? `Local semantic index ready: ${res.embedded ?? 0} memories`
          : "Local model unavailable; Atlas is using FTS search",
        "success",
      );
      setLivingStatus(await api.getLivingMemoryStatus());
    } catch (error) {
      showToast(`Semantic rebuild failed: ${error}`, "error");
    }
  };

  const consolidate = async () => {
    setConsolidating(true);
    try {
      const res = await api.consolidateMemory(500);
      showToast(
        `Consolidated ${res.sessions} sessions: ${res.approved} approved, ${res.pending} pending`,
        "success",
      );
      await loadPendingFacts();
      const graphRes = await api.getMemoryGraph();
      setGraph(graphRes);
      setLivingStatus(await api.getLivingMemoryStatus());
      setStatus({
        ok: graphRes.ok,
        vault_path: graphRes.vault_path,
        exists: graphRes.exists,
        dirty: graphRes.dirty,
        last_sync: graphRes.last_sync,
        stats: graphRes.stats,
      });
    } catch (error) {
      showToast(`Consolidation failed: ${error}`, "error");
    } finally {
      setConsolidating(false);
    }
  };

  const actOnFact = async (fact: MemoryFact, action: "approve" | "reject" | "stale" | "delete") => {
    try {
      if (action === "approve") await api.approveMemoryFact(fact.id);
      if (action === "reject") await api.rejectMemoryFact(fact.id);
      if (action === "stale") await api.markMemoryFactStale(fact.id);
      if (action === "delete") await api.deleteMemoryFact(fact.id);
      setPendingFacts((items) => items.filter((item) => item.id !== fact.id));
      setRecallFacts((items) => items.filter((item) => item.id !== fact.id || action === "approve"));
      showToast(action === "approve" ? "Fact approved" : "Fact removed", "success");
    } catch (error) {
      showToast(`Fact update failed: ${error}`, "error");
    }
  };

  const actOnSummary = async (summary: MemorySummary, action: "approve" | "reject" | "delete") => {
    try {
      if (action === "approve") await api.approveMemorySummary(summary.id);
      if (action === "reject") await api.rejectMemorySummary(summary.id);
      if (action === "delete") await api.deleteMemorySummary(summary.id);
      setPendingSummaries((items) => items.filter((item) => item.id !== summary.id));
      setRecallSummaries((items) => items.filter((item) => item.id !== summary.id || action === "approve"));
      showToast(action === "approve" ? "Summary approved" : "Summary removed", "success");
    } catch (error) {
      showToast(`Summary update failed: ${error}`, "error");
    }
  };

  const copyPath = async () => {
    if (!status?.vault_path) return;
    await navigator.clipboard.writeText(status.vault_path);
    showToast("Vault path copied", "success");
  };

  const openVault = async () => {
    try {
      await api.openMemoryVault();
      showToast("Vault opened", "success");
    } catch (error) {
      showToast(`Open failed: ${error}`, "error");
    }
  };

  return (
    <main className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-5 py-5 lg:px-8">
      <Toast toast={toast} />
      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="flex items-center gap-2 text-2xl">
                <Brain className="h-6 w-6 text-primary" />
                Memory
              </CardTitle>
              <div className="mt-2 flex min-w-0 flex-wrap gap-2 text-xs text-muted-foreground">
                <Badge tone={status?.dirty ? "warning" : "success"}>
                  {status?.dirty ? "sync needed" : "current"}
                </Badge>
                <span>{formatSyncTime(status?.last_sync)}</span>
                <span className="min-w-0 truncate font-mono">{status?.vault_path}</span>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <Button
                size="sm"
                ghost
                prefix={<Copy className="h-3.5 w-3.5" />}
                onClick={() => void copyPath()}
                disabled={!status?.vault_path}
              >
                Copy
              </Button>
              <Button
                size="sm"
                ghost
                prefix={<FolderOpen className="h-3.5 w-3.5" />}
                onClick={() => void openVault()}
              >
                Open
              </Button>
              <Button
                size="sm"
                ghost
                prefix={consolidating ? <Spinner className="h-3.5 w-3.5" /> : <Database className="h-3.5 w-3.5" />}
                onClick={() => void consolidate()}
                disabled={consolidating}
              >
                Evolve
              </Button>
              <Button
                size="sm"
                ghost
                prefix={summarizing ? <Spinner className="h-3.5 w-3.5" /> : <Brain className="h-3.5 w-3.5" />}
                onClick={() => void summarize()}
                disabled={summarizing}
              >
                Summarize
              </Button>
              <Button
                size="sm"
                ghost
                prefix={<Search className="h-3.5 w-3.5" />}
                onClick={() => void rebuildEmbeddings()}
              >
                Semantic
              </Button>
              <Button
                size="sm"
                prefix={syncing ? <Spinner className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
                onClick={() => void sync()}
                disabled={syncing}
              >
                Sync
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex h-[420px] items-center justify-center">
                <Spinner />
              </div>
            ) : (
              <GraphPreview
                graph={graph}
                selected={selectedNode?.id ?? null}
                onSelect={setSelectedNode}
              />
            )}
          </CardContent>
        </Card>

        <div className="flex min-w-0 flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Vault</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              {statEntries(status).map(([key, value]) => (
                <div key={key} className="rounded-xl border border-border bg-white/70 p-3">
                  <div className="text-xs uppercase tracking-wider text-muted-foreground">
                    {key}
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-primary">
                    {value}
                  </div>
                </div>
              ))}
              {livingStatus && (
                <>
                  <div className="border border-border bg-white p-3">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">entities</div>
                    <div className="mt-1 text-2xl font-semibold text-primary">{livingStatus.entities}</div>
                  </div>
                  <div className="border border-border bg-white p-3">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">active claims</div>
                    <div className="mt-1 text-2xl font-semibold text-primary">{livingStatus.claims}</div>
                  </div>
                  <div className="border border-border bg-white p-3">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">dossiers</div>
                    <div className="mt-1 text-2xl font-semibold text-primary">{livingStatus.dossiers}</div>
                  </div>
                  <div className="border border-border bg-white p-3">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">retrieval</div>
                    <div className="mt-2 text-sm font-semibold text-primary">{livingStatus.backend}</div>
                  </div>
                </>
              )}
              {!statEntries(status).length && (
                <div className="col-span-2 text-sm text-muted-foreground">
                  No vault statistics yet.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="min-w-0">
            <CardHeader>
              <CardTitle>Selected</CardTitle>
            </CardHeader>
            <CardContent className="min-w-0">
              {selectedNode ? (
                <div className="min-w-0">
                  <div className="flex min-w-0 items-center gap-2">
                    <Badge tone="secondary">{selectedNode.kind}</Badge>
                    <div className="min-w-0 truncate font-semibold">
                      {selectedNode.title}
                    </div>
                  </div>
                  <p className="mt-3 line-clamp-6 text-sm text-muted-foreground">
                    {selectedNode.snippet || selectedNode.path}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                    {selectedNode.topics.slice(0, 8).map((topic) => (
                      <span key={topic}>#{topic}</span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No node selected.</div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Search</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void runSearch();
                }}
                placeholder="Search memory, sessions, topics"
              />
              <Button
                size="icon"
                aria-label="Search memory"
                onClick={() => void runSearch()}
                disabled={searching}
              >
                {searching ? <Spinner className="h-4 w-4" /> : <Search className="h-4 w-4" />}
              </Button>
            </div>
            <Button
              ghost
              size="sm"
              className="justify-start"
              prefix={<ExternalLink className="h-3.5 w-3.5" />}
              onClick={() => void openVault()}
            >
              Open Obsidian vault folder
            </Button>
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardContent className={cn("grid gap-3 py-4", results.length > 1 && "md:grid-cols-2")}>
            {results.length ? (
              results.map((result, index) => (
                <ResultRow key={`${result.path}-${index}`} result={result} />
              ))
            ) : (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No matches.
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Agent recall</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex gap-2">
              <Input
                value={recallQuery}
                onChange={(event) => setRecallQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void runRecall();
                }}
                placeholder="Ask what Atlas should remember"
              />
              <Button
                size="icon"
                aria-label="Recall memory"
                onClick={() => void runRecall()}
                disabled={recalling}
              >
                {recalling ? <Spinner className="h-4 w-4" /> : <Search className="h-4 w-4" />}
              </Button>
            </div>
            <div className="rounded-xl border border-border bg-white/70 p-3 text-xs leading-5 text-muted-foreground">
              Recall checks curated files, current dossiers and claims, episodic summaries, then the raw archive only when needed.
            </div>
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardContent className="grid gap-3 py-4">
            {recallCurated.map((item, index) => (
              <ResultRow key={`${item.path}-${index}`} result={item} />
            ))}
            {recallDossiers.map((dossier) => (
              <DossierRow key={dossier.id} dossier={dossier} />
            ))}
            {recallClaims.map((claim) => (
              <ClaimRow key={claim.id} claim={claim} />
            ))}
            {recallFacts.map((fact) => (
              <FactRow
                key={fact.id}
                fact={fact}
                actions={
                  <>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Mark fact stale"
                      onClick={() => void actOnFact(fact, "stale")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Delete fact"
                      onClick={() => void actOnFact(fact, "delete")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </>
                }
              />
            ))}
            {recallSummaries.map((summary) => (
              <SummaryRow
                key={summary.id}
                summary={summary}
                actions={
                  <>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Delete summary"
                      onClick={() => void actOnSummary(summary, "delete")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </>
                }
              />
            ))}
            {recallRaw.map((item, index) => (
              <RawRecallRow key={`${item.session_id}-${item.message_id}-${index}`} item={item} />
            ))}
            {!recallCurated.length && !recallDossiers.length && !recallClaims.length && !recallFacts.length && !recallSummaries.length && !recallRaw.length && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No recalled memory yet.
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section>
        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>Pending memory</CardTitle>
            <Button
              size="sm"
              ghost
              prefix={<RefreshCw className="h-3.5 w-3.5" />}
              onClick={() => void loadPendingFacts()}
            >
              Refresh
            </Button>
          </CardHeader>
          <CardContent className={cn("grid gap-3", pendingFacts.length > 1 && "xl:grid-cols-2")}>
            {pendingFacts.map((fact) => (
              <FactRow
                key={fact.id}
                fact={fact}
                actions={
                  <>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Approve fact"
                      onClick={() => void actOnFact(fact, "approve")}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Reject fact"
                      onClick={() => void actOnFact(fact, "reject")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Delete fact"
                      onClick={() => void actOnFact(fact, "delete")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </>
                }
              />
            ))}
            {pendingSummaries.map((summary) => (
              <SummaryRow
                key={summary.id}
                summary={summary}
                actions={
                  <>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Approve summary"
                      onClick={() => void actOnSummary(summary, "approve")}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Reject summary"
                      onClick={() => void actOnSummary(summary, "reject")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      ghost
                      aria-label="Delete summary"
                      onClick={() => void actOnSummary(summary, "delete")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </>
                }
              />
            ))}
            {!pendingFacts.length && !pendingSummaries.length && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No pending memory.
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
