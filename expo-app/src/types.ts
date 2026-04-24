export type TradeAction = "buy" | "sell" | "hold";
export type ExecutionAction = "execute" | "request_approval" | "no_action" | "blocked";
export type AgentStatus = "active" | "paused";
export type SystemStatus = "idle" | "analyzing" | "executing";
export type ActivityFilter = "all" | "executed" | "pending" | "rejected";
export type RiskLevel = "low" | "medium" | "high";
export type SignalSource = "x" | "truth_social";
export type TrendPeriod = "1D" | "1W" | "1M";

export type AnalyzeResponse = {
  workflow: string;
  agent_id: string;
  source: string;
  author: string;
  symbol: string;
  direction: "bullish" | "bearish" | "neutral";
  confidence_score: number;
  action: ExecutionAction;
  notification_required: boolean;
  suggested_position_size: number;
  remaining_allocated_capital: number;
  decision_rationale: string;
};

export type SummaryRecord = {
  agent_id: string;
  symbol: string;
  source: string;
  confidence_score: number;
  action: ExecutionAction;
  rationale: string;
  pnl: number;
  executed_at: string;
  position_size: number;
};

export type DailySummaryResponse = {
  date: string;
  records_analyzed: number;
  trades_executed: number;
  approval_requests: number;
  no_action_count: number;
  blocked_count: number;
  average_confidence: number;
  total_pnl: number;
  win_rate: number;
  by_agent: Record<string, { trades_executed: number; total_pnl: number; avg_confidence: number }>;
};

export type SignalInsight = {
  id: string;
  asset: string;
  confidence: number;
  action: TradeAction;
  timestamp: string;
  source: SignalSource;
};

export type ActiveTrade = {
  id: string;
  asset: string;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  positionSize: number;
  openedAt: string;
};

export type AgentConfig = {
  id: string;
  name: string;
  strategy: string;
  assignedCapital: number;
  performance: number;
  confidenceThreshold: number;
  status: AgentStatus;
};

export type ActivityItem = {
  id: string;
  timestamp: string;
  type: "executed" | "pending" | "rejected";
  asset: string;
  confidence: number;
  action: TradeAction;
  pnl: number;
  note: string;
};

export type SignalDraft = {
  source: SignalSource;
  author: string;
  symbol: string;
  content: string;
};

export type PendingDecision = {
  id: string;
  agentId: string;
  symbol: string;
  confidence: number;
  suggestedAction: TradeAction;
  rationale: string;
  positionSize: number;
  expiresAt: number;
  source: SignalSource;
};

export type TradingMetrics = {
  totalPnl: number;
  todayPnl: number;
  activeCapital: number;
  restrictedCapital: number;
};
