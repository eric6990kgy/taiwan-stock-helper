import { useQuery } from "@tanstack/react-query";
import { agentPerformanceApi } from "../../services/api";
import type { AgentRole } from "../../types/api";

export function useAgentPerformance(role?: AgentRole) {
  return useQuery({
    queryKey: ["agent-performance-summary", role ?? "all"],
    queryFn: () => agentPerformanceApi.summary(role),
  });
}
