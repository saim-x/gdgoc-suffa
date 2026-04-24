import { createContext, useContext, useEffect, useMemo, useState } from "react";
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
const DEFAULT_API_URL = Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";

const initialMainAgent: AgentConfig = {
  id: "main-agent-orion",
  name: "ORION",
  strategy: "Truth-layer event trading",
  assignedCapital: 50000,
  performance: 0,
  confidenceThreshold: 85,
  status: "paused",
};

function toTradeAction(direction: AnalyzeResponse["direction"]): TradeAction {
  if (direction === "bullish") return "buy";
  if (direction === "bearish") return "sell";
  return "hold";
}

function riskFraction(level: RiskLevel): number {
  if (level === "low") return 0.12;
  if (level === "high") return 0.3;
  return 0.2;
}

export function TradingProvider({ children }: { children: React.ReactNode }) {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [connectionStatus, setConnectionStatus] = useState<"idle" | "online" | "offline">("idle");
  const [checkingConnection, setCheckingConnection] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>("idle");
  const [analyzing, setAnalyzing] = useState(false);

  const [autonomousMode, setAutonomousMode] = useState(false);
  const [riskLevel, setRiskLevel] = useState<RiskLevel>("medium");
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

  const mainAgent = agents[0];

  useEffect(() => {
    void pingBackend();
  }, []);

  async function pingBackend() {
    setCheckingConnection(true);
    try {
      const response = await fetch(`${apiUrl}/health`);
      if (!response.ok) {
        throw new Error(`Health check failed (${response.status})`);
      }
      setConnectionStatus("online");
    } catch {
      setConnectionStatus("offline");
    } finally {
      setCheckingConnection(false);
    }
  }

  const updateAgent = (id: string, patch: Partial<AgentConfig>) => {
    setAgents((prev) => prev.map((agent) => (agent.id === id ? { ...agent, ...patch } : agent)));
  };

  const addActivity = (item: ActivityItem) => {
    setActivity((prev) => [item, ...prev].slice(0, 250));
  };

  const addActiveTrade = (record: SummaryRecord, action: TradeAction) => {
    const trade: ActiveTrade = {
      id: `trade-${Date.now()}`,
      asset: record.symbol,
      entryPrice: 0,
      currentPrice: 0,
      pnl: record.pnl,
      positionSize: record.position_size,
      openedAt: record.executed_at,
    };
    setActiveTrades((prev) => [trade, ...prev].slice(0, 40));
    addActivity({
      id: `activity-${Date.now()}`,
      timestamp: record.executed_at,
      type: "executed",
      asset: record.symbol,
      confidence: record.confidence_score,
      action,
      pnl: record.pnl,
      note: record.rationale,
    });
  };

  const resolvePendingTrade = (tradeId: string, accepted: boolean) => {
    const pending = pendingTrades.find((trade) => trade.id === tradeId);
    if (!pending) return;

    const now = new Date().toISOString();
    if (accepted) {
      const executionRecord: SummaryRecord = {
        agent_id: mainAgent.id,
        symbol: pending.symbol,
        source: pending.source,
        confidence_score: pending.confidence,
        action: "execute",
        rationale: `User approved pending trade. ${pending.rationale}`,
        pnl: 0,
        executed_at: now,
        position_size: pending.positionSize,
      };
      setSummaryRecords((prev) => [executionRecord, ...prev]);
      addActiveTrade(executionRecord, pending.suggestedAction);
      setSystemStatus("executing");
      setTimeout(() => setSystemStatus("idle"), 900);
    } else {
      addActivity({
        id: `activity-${Date.now()}`,
        timestamp: now,
        type: "rejected",
        asset: pending.symbol,
        confidence: pending.confidence,
        action: pending.suggestedAction,
        pnl: 0,
        note: "User rejected pending trade setup.",
      });
    }

    setPendingTrades((prev) => prev.filter((trade) => trade.id !== tradeId));
  };

  async function analyzeSignal(draft: SignalDraft) {
    if (mainAgent.status !== "active") {
      Alert.alert("Main agent paused", "Set ORION to live before running signal analysis.");
      return;
    }

    const usedCapital = activeTrades.reduce((sum, trade) => sum + trade.positionSize, 0);
    if (usedCapital > mainAgent.assignedCapital) {
      Alert.alert("Allocation exceeded", "Reduce active exposure or increase ORION capital allocation.");
      return;
    }

    setAnalyzing(true);
    setSystemStatus("analyzing");
    setDailySummary(null);

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
      const timestamp = new Date().toISOString();
      const action = toTradeAction(result.direction);

      setRecentSignals((prev) => [
        {
          id: `signal-${Date.now()}`,
          asset: result.symbol,
          confidence: result.confidence_score,
          action,
          timestamp,
          source: result.source === "truth_social" ? "truth_social" : "x",
        },
        ...prev,
      ]);

      const summaryRecord: SummaryRecord = {
        agent_id: result.agent_id,
        symbol: result.symbol,
        source: result.source,
        confidence_score: result.confidence_score,
        action: result.action,
        rationale: result.decision_rationale,
        pnl: 0,
        executed_at: timestamp,
        position_size: result.suggested_position_size,
      };

      setSummaryRecords((prev) => [summaryRecord, ...prev]);

      if (result.action === "execute") {
        addActiveTrade(summaryRecord, action);
        setSystemStatus("executing");
        setTimeout(() => setSystemStatus("idle"), 900);
      } else if (result.action === "request_approval") {
        setPendingTrades((prev) => [
          {
            id: `pending-${Date.now()}`,
            symbol: result.symbol,
            confidence: result.confidence_score,
            suggestedAction: action,
            rationale: result.decision_rationale,
            positionSize: result.suggested_position_size,
            expiresAt: Date.now() + 45_000,
            source: result.source === "truth_social" ? "truth_social" : "x",
          },
          ...prev,
        ]);
        addActivity({
          id: `activity-${Date.now()}`,
          timestamp,
          type: "pending",
          asset: result.symbol,
          confidence: result.confidence_score,
          action,
          pnl: 0,
          note: "Trade setup sent for user confirmation.",
        });
        setSystemStatus("idle");
      } else {
        addActivity({
          id: `activity-${Date.now()}`,
          timestamp,
          type: "rejected",
          asset: result.symbol,
          confidence: result.confidence_score,
          action,
          pnl: 0,
          note: result.action === "blocked" ? "Trade blocked by allocation guardrail." : "Signal below confidence threshold.",
        });
        setSystemStatus("idle");
      }
    } catch (error) {
      setConnectionStatus("offline");
      Alert.alert("Signal analysis failed", error instanceof Error ? error.message : "Unknown error");
      setSystemStatus("idle");
    } finally {
      setAnalyzing(false);
    }
  }

  async function buildDailySummary() {
    if (!summaryRecords.length) {
      Alert.alert("No records available", "Run a signal first to generate a daily summary.");
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/truth/summary/daily`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: new Date().toISOString().slice(0, 10),
          records: summaryRecords,
        }),
      });
      if (!response.ok) {
        const details = await response.text();
        throw new Error(details || `daily summary failed (${response.status})`);
      }
      setDailySummary((await response.json()) as DailySummaryResponse);
    } catch (error) {
      Alert.alert("Summary failed", error instanceof Error ? error.message : "Unknown error");
    }
  }

  useEffect(() => {
    if (!pendingTrades.length) return;
    const ticker = setInterval(() => {
      const now = Date.now();
      const expired = pendingTrades.filter((trade) => trade.expiresAt <= now);
      if (!expired.length) return;

      expired.forEach((trade) => {
        addActivity({
          id: `activity-${Date.now()}-${trade.id}`,
          timestamp: new Date().toISOString(),
          type: "rejected",
          asset: trade.symbol,
          confidence: trade.confidence,
          action: trade.suggestedAction,
          pnl: 0,
          note: "Pending trade expired before user confirmation.",
        });
      });
      setPendingTrades((prev) => prev.filter((trade) => trade.expiresAt > now));
    }, 1000);

    return () => clearInterval(ticker);
  }, [pendingTrades]);

  const filteredActivity = useMemo(() => {
    if (activityFilter === "all") return activity;
    if (activityFilter === "executed") return activity.filter((item) => item.type === "executed");
    if (activityFilter === "pending") return activity.filter((item) => item.type === "pending");
    return activity.filter((item) => item.type === "rejected");
  }, [activity, activityFilter]);

  const metrics = useMemo<TradingMetrics>(() => {
    const totalPnl = summaryRecords.reduce((sum, record) => sum + record.pnl, 0);
    const today = new Date().toISOString().slice(0, 10);
    const todayPnl = summaryRecords
      .filter((record) => record.executed_at.startsWith(today))
      .reduce((sum, record) => sum + record.pnl, 0);
    const activeCapital = activeTrades.reduce((sum, trade) => sum + trade.positionSize, 0);
    const restrictedCapital = mainAgent.assignedCapital;

    return {
      totalPnl: Number(totalPnl.toFixed(2)),
      todayPnl: Number(todayPnl.toFixed(2)),
      activeCapital: Number(activeCapital.toFixed(2)),
      restrictedCapital: Number(restrictedCapital.toFixed(2)),
    };
  }, [summaryRecords, activeTrades, mainAgent.assignedCapital]);

  const pastTrades = useMemo(() => summaryRecords.filter((record) => record.action === "execute"), [summaryRecords]);

  const value: TradingContextValue = {
    apiUrl,
    setApiUrl,
    connectionStatus,
    checkingConnection,
    pingBackend,
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
