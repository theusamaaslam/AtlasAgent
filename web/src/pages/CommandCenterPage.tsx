import { useEffect, useMemo, useState, type ComponentType, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Boxes,
  CalendarClock,
  Cpu,
  FolderOpen,
  MessageSquare,
  Package,
  Plug,
  Puzzle,
  Radio,
  ShieldCheck,
  Sparkles,
  Terminal,
  Wrench,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Typography } from "@nous-research/ui/ui/components/typography/index";
import { AtlasLogo } from "@/components/AtlasLogo";
import { useProfileScope } from "@/contexts/useProfileScope";
import { isDashboardEmbeddedChatEnabled } from "@/lib/dashboard-flags";
import { api } from "@/lib/api";
import type {
  McpServer,
  PluginManifestResponse,
  SessionInfo,
  SessionStoreStats,
  SkillInfo,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export default function CommandCenterPage() {
  const { profile } = useProfileScope();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<SessionStoreStats | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [mcpCatalogCount, setMcpCatalogCount] = useState<number | null>(null);
  const [plugins, setPlugins] = useState<PluginManifestResponse[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrors([]);

    Promise.allSettled([
      api.getSessionStats(profile),
      api.getSessions(5, 0, profile, "recent"),
      api.getSkills(profile || undefined),
      api.getMcpServers(),
      api.getMcpCatalog(),
      api.getPlugins(),
    ] as const)
      .then(([statsResult, sessionsResult, skillsResult, mcpResult, catalogResult, pluginsResult]) => {
        if (cancelled) return;

        const nextErrors: string[] = [];
        if (statsResult.status === "fulfilled") setStats(statsResult.value);
        else nextErrors.push("Session stats");

        if (sessionsResult.status === "fulfilled") setSessions(sessionsResult.value.sessions);
        else nextErrors.push("Recent sessions");

        if (skillsResult.status === "fulfilled") setSkills(skillsResult.value);
        else nextErrors.push("Skills");

        if (mcpResult.status === "fulfilled") setMcpServers(mcpResult.value.servers);
        else nextErrors.push("MCP servers");

        if (catalogResult.status === "fulfilled") setMcpCatalogCount(catalogResult.value.entries.length);
        else nextErrors.push("MCP catalog");

        if (pluginsResult.status === "fulfilled") setPlugins(pluginsResult.value);
        else nextErrors.push("Plugins");

        setErrors(nextErrors);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [profile]);

  const enabledSkills = useMemo(
    () => skills.filter((skill) => skill.enabled).length,
    [skills],
  );
  const activeMcpServers = useMemo(
    () => mcpServers.filter((server) => server.enabled).length,
    [mcpServers],
  );
  const visiblePlugins = useMemo(
    () => plugins.filter((plugin) => !plugin.tab.hidden).length,
    [plugins],
  );
  const skillCategories = useMemo(() => {
    const categories = new Set(skills.map((skill) => skill.category).filter(Boolean));
    return categories.size;
  }, [skills]);
  const embeddedChat = isDashboardEmbeddedChatEnabled();

  const primaryStats: StatCard[] = [
    {
      label: "Sessions",
      value: formatNumber(stats?.total ?? sessions.length),
      detail: `${formatNumber(stats?.messages ?? 0)} messages`,
      icon: MessageSquare,
      href: "/sessions",
      tone: "jade",
    },
    {
      label: "Skills",
      value: formatNumber(enabledSkills),
      detail: `${formatNumber(skills.length)} installed`,
      icon: Package,
      href: "/skills",
      tone: "amber",
    },
    {
      label: "MCP",
      value: formatNumber(activeMcpServers),
      detail: `${formatNumber(mcpCatalogCount ?? 0)} catalog entries`,
      icon: Plug,
      href: "/mcp",
      tone: "sky",
    },
    {
      label: "Plugins",
      value: formatNumber(visiblePlugins),
      detail: `${formatNumber(plugins.length)} discovered`,
      icon: Puzzle,
      href: "/plugins",
      tone: "coral",
    },
  ];

  return (
    <main className="mx-auto flex w-full max-w-[1360px] min-w-0 flex-col gap-6 text-[#1f1b2d]">
      <section className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(280px,0.55fr)]">
        <div className="relative overflow-hidden rounded-2xl border border-[#d8dcef] bg-white p-6 shadow-[0_18px_48px_rgba(41,35,70,0.08)] sm:p-7">
          <div
            aria-hidden
            className="absolute inset-x-6 top-0 h-1 rounded-b-full bg-[linear-gradient(90deg,#75e4b5,#f4c46d,#ff856f,#8fd8ff)]"
          />
          <div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex min-w-0 flex-col gap-5">
              <AtlasLogo markClassName="h-12 w-12" />
              <div>
                <Typography className="block text-3xl font-semibold leading-tight tracking-normal text-[#737bd7] sm:text-5xl">
                  Command center
                </Typography>
                <Typography className="mt-3 block max-w-2xl text-base leading-7 text-[#5f637f]">
                  Sessions, skills, MCP connectors, plugins, channels, schedules, files, models, and chat in one operational surface.
                </Typography>
              </div>
            </div>

            <div className="grid min-w-[280px] gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <QuickLink
                href={embeddedChat ? "/chat" : "/sessions"}
                icon={Terminal}
                label={embeddedChat ? "Open chat" : "Open sessions"}
                tone="jade"
              />
              <QuickLink href="/mcp" icon={Plug} label="Add connector" tone="sky" />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[#d2d6e8] bg-[#f4f5fb] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
          <div className="flex items-center justify-between gap-3">
            <Typography className="block text-xs font-semibold uppercase tracking-[0.16em] text-[#737bd7]">
              Live fabric
            </Typography>
            {loading && (
              <span className="inline-flex items-center gap-2 text-xs text-[#5f637f]">
                <Spinner /> Syncing
              </span>
            )}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3">
            <MiniMetric label="Skill categories" value={skillCategories} />
            <MiniMetric label="Active MCP" value={activeMcpServers} />
            <MiniMetric label="Visible plugins" value={visiblePlugins} />
            <MiniMetric label="Archived" value={stats?.archived ?? 0} />
          </div>

          {errors.length > 0 && (
            <div className="mt-4 rounded-lg border border-[#de5b5b]/35 bg-[#de5b5b]/10 px-3 py-2 text-xs text-[#8f2f2f]">
              Partial data: {errors.join(", ")}
            </div>
          )}
        </div>
      </section>

      <section className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {primaryStats.map((stat) => (
          <StatCardView key={stat.label} stat={stat} />
        ))}
      </section>

      <section className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.42fr)]">
        <div className="grid min-w-0 gap-5 lg:grid-cols-2">
          <Panel title="Recent sessions" href="/sessions" action="All sessions">
            <div className="flex flex-col divide-y divide-[#dfe2f1]">
              {sessions.length === 0 ? (
                <EmptyState label={loading ? "Loading sessions" : "No sessions yet"} />
              ) : (
                sessions.map((session) => (
                  <Link
                    key={session.id}
                    to={`/chat?resume=${encodeURIComponent(session.id)}`}
                    className="group flex min-w-0 items-center justify-between gap-3 overflow-hidden rounded-lg px-2 py-3 text-left transition-colors hover:bg-[#f4f5fb]"
                  >
                    <div className="grid min-w-0 flex-1 gap-1 overflow-hidden">
                      <Typography className="block truncate text-sm font-medium text-current">
                        {session.title || "Untitled session"}
                      </Typography>
                      <Typography className="block truncate text-xs leading-5 text-[#737bd7]">
                        {session.preview || session.model || session.id}
                      </Typography>
                    </div>
                    <Badge className="shrink-0 border-[#dfe2f1] bg-[#fffceb] text-[0.65rem] uppercase tracking-[0.08em] text-[#c89236]">
                      {formatRelative(session.last_active)}
                    </Badge>
                  </Link>
                ))
              )}
            </div>
          </Panel>

          <Panel title="Connector mesh" href="/mcp" action="Manage MCP">
            <div className="flex flex-col divide-y divide-[#dfe2f1]">
              {mcpServers.length === 0 ? (
                <EmptyState label={loading ? "Loading connectors" : "No MCP connectors configured"} />
              ) : (
                mcpServers.slice(0, 5).map((server) => (
                  <div key={server.name} className="flex min-w-0 items-center justify-between gap-3 overflow-hidden rounded-lg px-2 py-3">
                    <div className="grid min-w-0 flex-1 gap-1 overflow-hidden">
                      <Typography className="block truncate text-sm font-medium">
                        {server.name}
                      </Typography>
                      <Typography className="block truncate text-xs leading-5 text-[#737bd7]">
                        {server.transport} {server.tools ? `- ${server.tools.length} tools` : ""}
                      </Typography>
                    </div>
                    <Badge
                      className={cn(
                        "shrink-0 border-[#dfe2f1] bg-white text-[0.65rem] uppercase tracking-[0.08em]",
                        server.enabled ? "text-[#48a879]" : "text-[#74718a]",
                      )}
                    >
                      {server.enabled ? "Online" : "Off"}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </Panel>
        </div>

        <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-1">
          {WORKFLOW_LINKS.map((item) => (
            <WorkflowLink key={item.href} item={item} />
          ))}
        </div>
      </section>
    </main>
  );
}

function StatCardView({ stat }: { stat: StatCard }) {
  const Icon = stat.icon;
  return (
    <Link
      to={stat.href}
      className={cn(
        "group relative overflow-hidden rounded-xl border border-[#dfe2f1] bg-white p-5",
        "shadow-[0_12px_32px_rgba(41,35,70,0.06)] transition-colors hover:border-[#c9cde5] hover:bg-[#fbfbff]",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute inset-x-0 top-0 h-1",
          stat.tone === "jade" && "bg-[#75e4b5]",
          stat.tone === "amber" && "bg-[#f4c46d]",
          stat.tone === "sky" && "bg-[#8fd8ff]",
          stat.tone === "coral" && "bg-[#ff856f]",
        )}
      />
      <div className="flex items-start justify-between gap-3">
        <div>
          <Typography className="block text-xs font-semibold uppercase tracking-[0.14em] text-[#737bd7]">
            {stat.label}
          </Typography>
          <Typography className="mt-3 block text-3xl font-semibold leading-none text-[#737bd7]">
            {stat.value}
          </Typography>
          <Typography className="mt-2 block text-xs text-[#5f637f]">
            {stat.detail}
          </Typography>
        </div>
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[#dfe2f1] bg-[#f4f5fb] text-[#737bd7]">
          <Icon className="h-4 w-4" />
        </span>
      </div>
    </Link>
  );
}

function Panel({ action, children, href, title }: PanelProps) {
  return (
    <section className="rounded-xl border border-[#dfe2f1] bg-white p-5 shadow-[0_12px_32px_rgba(41,35,70,0.05)]">
      <div className="flex items-center justify-between gap-3 border-b border-[#dfe2f1] pb-3">
        <Typography className="block text-xs font-semibold uppercase tracking-[0.16em] text-[#737bd7]">
          {title}
        </Typography>
        <Link className="text-xs font-medium text-[#737bd7] hover:underline" to={href}>
          {action}
        </Link>
      </div>
      {children}
    </section>
  );
}

function QuickLink({ href, icon: Icon, label, tone }: QuickLinkProps) {
  return (
    <Link
      to={href}
      className={cn(
        "inline-flex min-h-13 items-center justify-between gap-3 rounded-lg border border-[#cfd3ea] px-4 py-3",
        "bg-[#f4f5fb] text-sm font-medium text-[#1f1b2d] transition-colors hover:border-[#bfc4ed] hover:bg-white",
      )}
    >
      <span className="inline-flex min-w-0 items-center gap-2">
        <Icon
          className={cn(
            "h-4 w-4 shrink-0",
            tone === "jade" && "text-[#48a879]",
            tone === "sky" && "text-[#8fd8ff]",
          )}
        />
        <span className="truncate">{label}</span>
      </span>
      <span className="text-[#9aa0d7]">/</span>
    </Link>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-[#dfe2f1] bg-white/72 px-4 py-3">
      <Typography className="block text-2xl font-semibold leading-none text-[#737bd7]">
        {formatNumber(value)}
      </Typography>
      <Typography className="mt-1 block truncate text-[0.68rem] uppercase tracking-[0.12em] text-[#737bd7]">
        {label}
      </Typography>
    </div>
  );
}

function WorkflowLink({ item }: { item: WorkflowItem }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.href}
      className="group flex min-h-22 min-w-0 items-center gap-4 overflow-hidden rounded-xl border border-[#dfe2f1] bg-white px-5 py-4 shadow-[0_12px_32px_rgba(41,35,70,0.04)] transition-colors hover:border-[#c9cde5] hover:bg-[#fbfbff]"
    >
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-[#dfe2f1] bg-[#f4f5fb] text-[#737bd7]">
        <Icon className="h-4 w-4" />
      </span>
      <span className="grid min-w-0 flex-1 gap-1 overflow-hidden">
        <Typography className="block truncate text-sm font-medium leading-5 text-[#1f1b2d]">{item.label}</Typography>
        <Typography className="block truncate text-xs leading-5 text-[#737bd7]">{item.detail}</Typography>
      </span>
    </Link>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex min-h-24 items-center justify-center py-6 text-sm text-[#737bd7]">
      {label}
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

function formatRelative(timestamp: number) {
  if (!timestamp) return "New";
  const seconds = Math.max(0, Math.round((Date.now() / 1000 - timestamp)));
  if (seconds < 60) return "Now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.round(hours / 24);
  return `${days}d`;
}

const WORKFLOW_LINKS: WorkflowItem[] = [
  { href: "/skills", label: "Skill forge", detail: "Create, edit, learn", icon: Sparkles },
  { href: "/channels", label: "Channels", detail: "Messaging gateways", icon: Radio },
  { href: "/cron", label: "Schedules", detail: "Recurring jobs", icon: CalendarClock },
  { href: "/models", label: "Models", detail: "Providers and routing", icon: Cpu },
  { href: "/files", label: "Files", detail: "Workspace access", icon: FolderOpen },
  { href: "/pairing", label: "Pairing", detail: "Secure device links", icon: ShieldCheck },
  { href: "/system", label: "System", detail: "Runtime status", icon: Wrench },
  { href: "/plugins", label: "Plugin bay", detail: "Installed extensions", icon: Boxes },
];

interface StatCard {
  detail: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  label: string;
  tone: "jade" | "amber" | "sky" | "coral";
  value: string;
}

interface PanelProps {
  action: string;
  children: ReactNode;
  href: string;
  title: string;
}

interface QuickLinkProps {
  href: string;
  icon: ComponentType<{ className?: string }>;
  label: string;
  tone: "jade" | "sky";
}

interface WorkflowItem {
  detail: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  label: string;
}
