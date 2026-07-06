import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Brain,
  Check,
  Copy,
  Database,
  ExternalLink,
  FolderOpen,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Input } from "@nous-research/ui/ui/components/input";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type {
  MemoryFact,
  MemoryGraphNode,
  MemoryGraphResponse,
  MemoryRecallRawResult,
  MemorySearchResult,
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
  topic: { fill: "#ff8a70", stroke: "#df654f" },
};

function formatSyncTime(value?: number | null): string {
  if (!value) return "Never";
  return new Date(value * 1000).toLocaleString();
}

function statEntries(status: MemoryVaultStatus | null): Array<[string, number]> {
  return Object.entries(status?.stats ?? {}).sort(([a], [b]) => a.localeCompare(b));
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
  const nodes = useMemo(() => (graph?.nodes ?? []).slice(0, 140), [graph]);
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const layout = useMemo(() => {
    const centerX = 420;
    const centerY = 250;
    const radius = 185;
    return nodes.map((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1);
      const kindOffset =
        node.kind === "creator" ? 0 : node.kind === "topic" ? 42 : node.kind === "interaction" ? 18 : -18;
      return {
        node,
        x: centerX + Math.cos(angle) * (radius + kindOffset),
        y: centerY + Math.sin(angle) * (radius + kindOffset),
      };
    });
  }, [nodes]);
  const position = useMemo(
    () => new Map(layout.map((item) => [item.node.id, item])),
    [layout],
  );
  const edges = useMemo(
    () =>
      (graph?.edges ?? [])
        .filter((edge) => byId.has(edge.source) && byId.has(edge.target))
        .slice(0, 260),
    [byId, graph],
  );

  if (!nodes.length) {
    return (
      <div className="flex h-[420px] items-center justify-center text-sm text-muted-foreground">
        Sync the vault to draw the graph.
      </div>
    );
  }

  return (
    <svg
      role="img"
      aria-label="Memory graph"
      viewBox="0 0 840 500"
      className="h-[420px] w-full max-w-full"
    >
      <defs>
        <radialGradient id="memoryGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#eef0fb" stopOpacity="0.35" />
        </radialGradient>
      </defs>
      <rect width="840" height="500" rx="22" fill="url(#memoryGlow)" />
      {edges.map((edge, index) => {
        const a = position.get(edge.source);
        const b = position.get(edge.target);
        if (!a || !b) return null;
        return (
          <line
            key={`${edge.source}-${edge.target}-${index}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="#b5b9e8"
            strokeOpacity="0.38"
            strokeWidth="1"
          />
        );
      })}
      {layout.map(({ node, x, y }) => {
        const style = KIND_STYLES[node.kind] ?? KIND_STYLES.interaction;
        const active = selected === node.id;
        const size = node.kind === "creator" ? 15 : node.kind === "topic" ? 10 : 8;
        return (
          <g
            key={node.id}
            className="cursor-pointer"
            onClick={() => onSelect(node)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") onSelect(node);
            }}
            tabIndex={0}
            role="button"
            aria-label={node.title}
          >
            <circle
              cx={x}
              cy={y}
              r={active ? size + 5 : size}
              fill={style.fill}
              stroke={style.stroke}
              strokeWidth={active ? 4 : 2}
              opacity={node.kind === "interaction" ? 0.78 : 0.96}
            />
            {(active || node.kind === "creator") && (
              <text
                x={x + 14}
                y={y + 5}
                fill="#252238"
                fontSize="13"
                fontFamily="ui-sans-serif, system-ui"
              >
                {node.title.slice(0, 34)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
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
  const [graph, setGraph] = useState<MemoryGraphResponse | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [recallQuery, setRecallQuery] = useState("");
  const [recallFacts, setRecallFacts] = useState<MemoryFact[]>([]);
  const [recallRaw, setRecallRaw] = useState<MemoryRecallRawResult[]>([]);
  const [pendingFacts, setPendingFacts] = useState<MemoryFact[]>([]);
  const [selectedNode, setSelectedNode] = useState<MemoryGraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [consolidating, setConsolidating] = useState(false);
  const [searching, setSearching] = useState(false);
  const [recalling, setRecalling] = useState(false);

  const loadPendingFacts = useCallback(async () => {
    try {
      const res = await api.getPendingMemoryFacts(50);
      setPendingFacts(res.facts);
    } catch (error) {
      showToast(`Pending facts failed: ${error}`, "error");
    }
  }, [showToast]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, graphRes] = await Promise.all([
        api.getMemoryVault(),
        api.getMemoryGraph(),
      ]);
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
      setRecallFacts([]);
      setRecallRaw([]);
      return;
    }
    setRecalling(true);
    try {
      const res = await api.recallMemory(clean, 8);
      setRecallFacts(res.facts);
      setRecallRaw(res.raw_results);
    } catch (error) {
      showToast(`Recall failed: ${error}`, "error");
    } finally {
      setRecalling(false);
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
                Consolidate
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
              Recall ranks promoted facts first, then falls back to matching raw interactions.
            </div>
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardContent className="grid gap-3 py-4">
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
            {recallRaw.map((item, index) => (
              <RawRecallRow key={`${item.session_id}-${item.message_id}-${index}`} item={item} />
            ))}
            {!recallFacts.length && !recallRaw.length && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No recalled facts yet.
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section>
        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>Pending facts</CardTitle>
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
            {!pendingFacts.length && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No pending facts.
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
