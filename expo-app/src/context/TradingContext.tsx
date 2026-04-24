import { createContext, useContext, useCallback, useEffect, useMemo, useState, useRef } from "react";
import Constants from "expo-constants";
import { Alert, Platform } from "react-native";
import type {
  ActivityFilter,
  ActivityItem,
  ActiveTrade,
  AgentConfig,
  AnalyzeResponse,
  DailySummaryResponse,
  PendingDecision,
  RiskLevel,
  SignalDraft,
  SignalInsight,
  SummaryRecord,
  SystemStatus,
  TradeAction,
  TradingMetrics,
  TrendPeriod,
} from "../types";

type TradingContextValue = {
  apiUrl: string;
  setApiUrl: (url: string) => void;
  connectionStatus: "idle" | "online" | "offline";
  checkingConnection: boolean;
  pingBackend: () => Promise<void>;
  resettingData: boolean;
  resetAllTradingData: () => Promise<boolean>;
  systemStatus: SystemStatus;
  analyzing: boolean;
  autonomousMode: boolean;
  setAutonomousMode: (enabled: boolean) => void;
  riskLevel: RiskLevel;
  setRiskLevel: (level: RiskLevel) => void;
  biometricLock: boolean;
  setBiometricLock: (enabled: boolean) => void;
  notificationsEnabled: boolean;
  setNotificationsEnabled: (enabled: boolean) => void;
  capitalLimit: number;
  setCapitalLimit: (value: number) => void;
  defaultConfidenceThreshold: number;
  setDefaultConfidenceThreshold: (value: number) => void;
  agents: AgentConfig[];
  updateAgent: (id: string, patch: Partial<AgentConfig>) => void;
  mainAgent: AgentConfig;
  recentSignals: SignalInsight[];
  activeTrades: ActiveTrade[];
  pastTrades: SummaryRecord[];
  activity: ActivityItem[];
  activityFilter: ActivityFilter;
  setActivityFilter: (filter: ActivityFilter) => void;
  filteredActivity: ActivityItem[];
  summaryRecords: SummaryRecord[];
  dailySummary: DailySummaryResponse | null;
  buildDailySummary: () => Promise<void>;
  pendingTrades: PendingDecision[];
  resolvePendingTrade: (tradeId: string, accepted: boolean) => void;
  analyzeSignal: (draft: SignalDraft) => Promise<void>;
  metrics: TradingMetrics;
  trendPeriod: TrendPeriod;
  setTrendPeriod: (period: TrendPeriod) => void;
};

const TradingContext = createContext<TradingContextValue | null>(null);

// Resolve backend URL: extract dev machine IP from Expo, fallback to LAN IP
function getDefaultApiUrl(): string {
  try {
    // Try multiple Expo Constants paths to find the dev machine IP
    const candidates: (string | undefined)[] = [
      Constants.expoGoConfig?.debuggerHost,
      Constants.expoConfig?.hostUri,
      (Constants as any).manifest?.debuggerHost,
      (Constants as any).manifest2?.extra?.expoGo?.debuggerHost,
    ];
    for (const host of candidates) {
      if (host && typeof host === "string" && host.includes(":")) {
        const ip = host.split(":")[0];
        if (ip && ip !== "127.0.0.1" && ip !== "localhost") {
          const url = `http://${ip}:8000`;
          console.log("[TradingContext] Auto-detected backend URL:", url);
          return url;
        }
      }
    }
  } catch {}
  // Hardcoded LAN IP fallback (your machine's IP)
  const fallback = Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://192.168.0.105:8000";
  console.log("[TradingContext] Using fallback URL:", fallback);
  return fallback;
}
const DEFAULT_API_URL = getDefaultApiUrl();

const POLL_INTERVAL = 8_000; // 8 seconds

const initialMainAgent: AgentConfig = {
  id: "agent-orion",
  name: "ORION",
  strategy: "Event-driven signal trading",
  assignedCapital: 200000,
  performance: 0,
  confidenceThreshold: 85,
  status: "active",
};

function toTradeAction(direction: string): TradeAction {
  if (direction === "bullish" || direction === "buy") return "buy";
  if (direction === "bearish" || direction === "sell") return "sell";
  return "hold";
}

function riskFraction(level: RiskLevel): number {
  if (level === "low") return 0.12;
  if (level === "high") return 0.3;
  return 0.2;
}

function toTimestampMs(value: string): number {
  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function dedupeActivityItems(items: ActivityItem[]): ActivityItem[] {
  const sorted = [...items].sort((a, b) => toTimestampMs(b.timestamp) - toTimestampMs(a.timestamp));
  const seenById = new Set<string>();
  const seenFingerprintAt = new Map<string, number>();
  const deduped: ActivityItem[] = [];

  for (const item of sorted) {
    if (seenById.has(item.id)) continue;
    seenById.add(item.id);

    const normalizedNote = item.note.trim().toLowerCase().replace(/\s+/g, " ");
    const fingerprint = `${item.type}|${item.asset}|${item.action}|${item.confidence}|${normalizedNote}`;
    const ts = toTimestampMs(item.timestamp);
    const previousTs = seenFingerprintAt.get(fingerprint);

    // Collapse near-identical bursts that appear as duplicates/triplets in feed.
    if (previousTs !== undefined && Math.abs(previousTs - ts) <= 120000) continue;

    seenFingerprintAt.set(fingerprint, ts);
    deduped.push(item);
  }

  return deduped;
}

export function TradingProvider({ children }: { children: React.ReactNode }) {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [connectionStatus, setConnectionStatus] = useState<"idle" | "online" | "offline">("idle");
  const [checkingConnection, setCheckingConnection] = useState(false);
  const [resettingData, setResettingData] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>("idle");
  const [analyzing, setAnalyzing] = useState(false);

  const [autonomousMode, setAutonomousModeLocal] = useState(false);
  const [riskLevel, setRiskLevelLocal] = useState<RiskLevel>("medium");
  const [biometricLock, setBiometricLock] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [capitalLimit, setCapitalLimit] = useState(500000);
  const [defaultConfidenceThreshold, setDefaultConfidenceThreshold] = useState(85);
  const [agents, setAgents] = useState<AgentConfig[]>([initialMainAgent]);

  const [recentSignals, setRecentSignals] = useState<SignalInsight[]>([]);
  const [activeTrades, setActiveTrades] = useState<ActiveTrade[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");
  const [summaryRecords, setSummaryRecords] = useState<SummaryRecord[]>([]);
  const [dailySummary, setDailySummary] = useState<DailySummaryResponse | null>(null);
  const [pendingTrades, setPendingTrades] = useState<PendingDecision[]>([]);
  const [trendPeriod, setTrendPeriod] = useState<TrendPeriod>("1D");
  const [portfolioState, setPortfolioState] = useState<any>(null);

  const mainAgent = useMemo(
    () => agents.find((agent) => agent.id === "agent-orion") ?? agents[0] ?? initialMainAgent,
    [agents]
  );
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Ping backend ───────────────────────────────────────────────────
  const pingBackend = useCallback(async () => {
    setCheckingConnection(true);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      console.log("[TradingContext] Pinging backend at", apiUrl);
      const response = await fetch(`${apiUrl}/health`, { signal: controller.signal });
      clearTimeout(timeout);
      if (!response.ok) throw new Error(`Health check failed (${response.status})`);
      console.log("[TradingContext] Backend ONLINE");
      setConnectionStatus("online");
    } catch (err) {
      clearTimeout(timeout);
      console.warn("[TradingContext] Backend OFFLINE:", err instanceof Error ? err.message : err);
      setConnectionStatus("offline");
    } finally {
      setCheckingConnection(false);
    }
  }, [apiUrl]);

  // ── Poll backend data ──────────────────────────────────────────────
  const pollData = useCallback(async () => {
    try {
      const makeFetch = (path: string) => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);
        return fetch(`${apiUrl}${path}`, { signal: controller.signal }).finally(() => clearTimeout(timeout));
      };

      const [signalsRes, agentsRes, portfolioRes, activityRes, pendingRes, tradesRes] = await Promise.allSettled([
        makeFetch("/signals?limit=30"),
        makeFetch("/agents"),
        makeFetch("/portfolio"),
        makeFetch("/activity?limit=100"),
        makeFetch("/pending?limit=40"),
        makeFetch("/trades?limit=50"),
      ]);

      // Process signals
      if (signalsRes.status === "fulfilled" && signalsRes.value.ok) {
        const data = await signalsRes.value.json();
        const mapped: SignalInsight[] = (data.signals || []).map((s: any) => ({
          id: s.id,
          asset: s.asset,
          confidence: s.confidence_score,
          action: toTradeAction(s.signal),
          timestamp: s.created_at,
          source: "x" as const,
        }));
        setRecentSignals(mapped);
      }

      // Process agents
      if (agentsRes.status === "fulfilled" && agentsRes.value.ok) {
        const data = await agentsRes.value.json();
        const mapped: AgentConfig[] = (data.agents || []).map((a: any) => ({
          id: a.id,
          name: a.name,
          strategy: a.strategy,
          assignedCapital: a.assigned_capital,
          performance: a.performance,
          confidenceThreshold: a.confidence_threshold,
          status: a.status === "active" ? "active" : "paused",
        }));
        if (mapped.length > 0) setAgents(mapped);
      }

      // Process portfolio
      if (portfolioRes.status === "fulfilled" && portfolioRes.value.ok) {
        const data = await portfolioRes.value.json();
        setPortfolioState(data);
        setAutonomousModeLocal(data.autonomous_mode ?? false);
        setRiskLevelLocal(data.risk_level ?? "medium");

        // Map active positions to ActiveTrade[]
        const mapped: ActiveTrade[] = (data.active_positions || []).map((p: any) => ({
          id: p.id,
          asset: p.asset,
          entryPrice: p.entry_price,
          currentPrice: p.current_price,
          pnl: p.pnl,
          positionSize: p.position_size,
          openedAt: p.opened_at,
        }));
        setActiveTrades(mapped);
      }

      // Process activity
      if (activityRes.status === "fulfilled" && activityRes.value.ok) {
        const data = await activityRes.value.json();
        const mapped: ActivityItem[] = (data.activity || []).map((a: any) => ({
          id: a.id,
          timestamp: a.timestamp,
          type: a.type === "executed" ? "executed" : a.type === "pending" ? "pending" : "rejected",
          asset: a.asset,
          confidence: a.confidence,
          action: toTradeAction(a.action),
          pnl: a.pnl,
          note: a.note,
        }));
        setActivity(dedupeActivityItems(mapped));
      }

      // Process pending
      if (pendingRes.status === "fulfilled" && pendingRes.value.ok) {
        const data = await pendingRes.value.json();
        const mapped: PendingDecision[] = (data.pending || []).map((p: any) => ({
          id: p.id,
          agentId: p.agent_id,
          symbol: p.asset,
          confidence: p.confidence,
          suggestedAction: toTradeAction(p.direction),
          rationale: p.rationale,
          positionSize: p.position_size,
          expiresAt: new Date(p.expires_at).getTime(),
          source: "x" as const,
        }));

        const deduped = Array.from(new Map(mapped.map((item) => [item.id, item])).values());
        deduped.sort((a, b) => {
          const expiryOrder = a.expiresAt - b.expiresAt;
          if (expiryOrder !== 0) return expiryOrder;
          return b.confidence - a.confidence;
        });
        setPendingTrades(deduped);
      }

      // Process trades (for summary records)
      if (tradesRes.status === "fulfilled" && tradesRes.value.ok) {
        const data = await tradesRes.value.json();
        const closedTrades = (data.trades || []).filter((t: any) => t.status === "closed");
        const uniqueClosedTrades = Array.from(new Map(closedTrades.map((t: any) => [t.id, t])).values());

        const mapped: SummaryRecord[] = uniqueClosedTrades
          .map((t: any) => ({
            trade_id: t.id,
            agent_id: t.agent_id,
            symbol: t.asset,
            source: "system",
            confidence_score: t.confidence,
            action: "execute" as const,
            rationale: "",
            pnl: Number(t.pnl ?? 0),
            executed_at: t.closed_at || t.opened_at,
            position_size: Number(t.position_size ?? 0),
          }))
          .sort((a, b) => toTimestampMs(b.executed_at) - toTimestampMs(a.executed_at));

        setSummaryRecords(mapped);
      }

      setConnectionStatus("online");
    } catch (err) {
      console.warn("[TradingContext] Poll error:", err instanceof Error ? err.message : err);
    }
  }, [apiUrl]);

  const resetAllTradingData = useCallback(async () => {
    setResettingData(true);
    try {
      const response = await fetch(`${apiUrl}/settings/reset-data`, { method: "POST" });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Reset failed (${response.status})`);
      }
      setDailySummary(null);
      await pollData();
      return true;
    } catch (err) {
      Alert.alert("Reset failed", err instanceof Error ? err.message : "Unknown error");
      return false;
    } finally {
      setResettingData(false);
    }
  }, [apiUrl, pollData]);

  // ── Start polling ──────────────────────────────────────────────────
  useEffect(() => {
    void pingBackend();
    void pollData();

    pollRef.current = setInterval(() => {
      void pollData();
    }, POLL_INTERVAL);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [apiUrl]);

  // ── Agent update ───────────────────────────────────────────────────
  const updateAgent = useCallback(async (id: string, patch: Partial<AgentConfig>) => {
    // Optimistic local update
    setAgents((prev) => prev.map((a) => (a.id === id ? { ...a, ...patch } : a)));

    // Sync to backend
    try {
      const body: any = {};
      if (patch.assignedCapital !== undefined) body.assigned_capital = patch.assignedCapital;
      if (patch.confidenceThreshold !== undefined) body.confidence_threshold = patch.confidenceThreshold;
      if (patch.status !== undefined) body.status = patch.status;
      if (patch.name !== undefined) body.name = patch.name;

      await fetch(`${apiUrl}/agents/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch {
      // Silently fail — optimistic update stays
    }
  }, [apiUrl]);

  // ── Autonomous mode toggle ─────────────────────────────────────────
  const setAutonomousMode = useCallback(async (enabled: boolean) => {
    setAutonomousModeLocal(enabled);
    try {
      await fetch(`${apiUrl}/settings/autonomous`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
    } catch {
      // Silently fail
    }
  }, [apiUrl]);

  // ── Risk level ─────────────────────────────────────────────────────
  const setRiskLevel = useCallback(async (level: RiskLevel) => {
    setRiskLevelLocal(level);
    try {
      await fetch(`${apiUrl}/settings/risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level }),
      });
    } catch {
      // Silently fail
    }
  }, [apiUrl]);

  // ── Resolve pending trade ──────────────────────────────────────────
  const resolvePendingTrade = useCallback(async (tradeId: string, accepted: boolean) => {
    const action = accepted ? "approve" : "reject";
    try {
      const response = await fetch(`${apiUrl}/pending/${tradeId}/${action}`, { method: "POST" });
      if (!response.ok) throw new Error(`Failed to ${action} trade`);
      // Remove from local state immediately
      setPendingTrades((prev) => prev.filter((t) => t.id !== tradeId));
      // Re-poll to get updated data
      void pollData();
    } catch (error) {
      Alert.alert("Action failed", error instanceof Error ? error.message : "Unknown error");
    }
  }, [apiUrl, pollData]);

  // ── Analyze signal (legacy truth workflow) ─────────────────────────
  async function analyzeSignal(draft: SignalDraft) {
    if (mainAgent.status !== "active") {
      Alert.alert("Main agent paused", "Set ORION to live before running signal analysis.");
      return;
    }

    setAnalyzing(true);
    setSystemStatus("analyzing");
    setDailySummary(null);

    const usedCapital = activeTrades.reduce((sum, trade) => sum + trade.positionSize, 0);

    const payload = {
      source: draft.source,
      author: draft.author.trim() || "Unknown source",
      content: draft.content.trim(),
      symbol: draft.symbol.trim().toUpperCase(),
      agent_id: mainAgent.id,
      total_capital: capitalLimit,
      allocated_capital: mainAgent.assignedCapital,
      used_capital: Number(usedCapital.toFixed(2)),
      autonomous_mode: autonomousMode,
      autonomous_min_confidence: mainAgent.confidenceThreshold || defaultConfidenceThreshold,
      max_position_fraction: riskFraction(riskLevel),
    };

    try {
      const response = await fetch(`${apiUrl}/truth/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || `truth analyze failed (${response.status})`);
      }

      setConnectionStatus("online");
      const result = (await response.json()) as AnalyzeResponse;

      setSystemStatus(result.action === "execute" ? "executing" : "idle");
      if (result.action === "execute") {
        setTimeout(() => setSystemStatus("idle"), 900);
      }

      // Re-poll to get fresh data
      setTimeout(() => void pollData(), 500);
    } catch (error) {
      setConnectionStatus("offline");
      Alert.alert("Signal analysis failed", error instanceof Error ? error.message : "Unknown error");
      setSystemStatus("idle");
    } finally {
      setAnalyzing(false);
    }
  }

  // ── Build daily summary ────────────────────────────────────────────
  async function buildDailySummary() {
    try {
      const response = await fetch(`${apiUrl}/summary/daily`, { method: "POST" });
      if (!response.ok) throw new Error(`Daily summary failed (${response.status})`);
      const data = await response.json();

      // Map to frontend's expected DailySummaryResponse shape
      setDailySummary({
        date: data.date || new Date().toISOString().slice(0, 10),
        records_analyzed: data.trades_executed || 0,
        trades_executed: data.trades_executed || 0,
        approval_requests: 0,
        no_action_count: 0,
        blocked_count: 0,
        average_confidence: data.avg_confidence || 0,
        total_pnl: data.total_pnl || 0,
        win_rate: data.win_rate || 0,
        by_agent: {},
      });
    } catch (error) {
      Alert.alert("Summary failed", error instanceof Error ? error.message : "Unknown error");
    }
  }

  // ── Pending trade expiry ───────────────────────────────────────────
  useEffect(() => {
    if (!pendingTrades.length) return;
    const ticker = setInterval(() => {
      const now = Date.now();
      setPendingTrades((prev) => prev.filter((trade) => trade.expiresAt > now));
    }, 5000);
    return () => clearInterval(ticker);
  }, [pendingTrades.length]);

  // ── Derived state ──────────────────────────────────────────────────
  const filteredActivity = useMemo(() => {
    if (activityFilter === "all") return activity;
    if (activityFilter === "executed") return activity.filter((item) => item.type === "executed");
    if (activityFilter === "pending") return activity.filter((item) => item.type === "pending");
    return activity.filter((item) => item.type === "rejected");
  }, [activity, activityFilter]);

  const metrics = useMemo<TradingMetrics>(() => {
    if (portfolioState) {
      return {
        totalPnl: portfolioState.total_pnl ?? 0,
        todayPnl: portfolioState.today_pnl ?? 0,
        activeCapital: portfolioState.total_used ?? 0,
        restrictedCapital: portfolioState.total_allocated ?? mainAgent.assignedCapital,
      };
    }
    return { totalPnl: 0, todayPnl: 0, activeCapital: 0, restrictedCapital: mainAgent.assignedCapital };
  }, [portfolioState, mainAgent.assignedCapital]);

  const pastTrades = useMemo(
    () => summaryRecords.filter((record) => record.action === "execute"),
    [summaryRecords],
  );

  const value: TradingContextValue = {
    apiUrl,
    setApiUrl,
    connectionStatus,
    checkingConnection,
    pingBackend,
    resetAllTradingData,
    resettingData,
    systemStatus,
    analyzing,
    autonomousMode,
    setAutonomousMode,
    riskLevel,
    setRiskLevel,
    biometricLock,
    setBiometricLock,
    notificationsEnabled,
    setNotificationsEnabled,
    capitalLimit,
    setCapitalLimit,
    defaultConfidenceThreshold,
    setDefaultConfidenceThreshold,
    agents,
    updateAgent,
    mainAgent,
    recentSignals,
    activeTrades,
    pastTrades,
    activity,
    activityFilter,
    setActivityFilter,
    filteredActivity,
    summaryRecords,
    dailySummary,
    buildDailySummary,
    pendingTrades,
    resolvePendingTrade,
    analyzeSignal,
    metrics,
    trendPeriod,
    setTrendPeriod,
  };

  return <TradingContext.Provider value={value}>{children}</TradingContext.Provider>;
}

export function useTrading() {
  const context = useContext(TradingContext);
  if (!context) {
    throw new Error("useTrading must be used within TradingProvider.");
  }
  return context;
}
