import { useQuery } from "@tanstack/react-query";
import { analyticsApi, portfolioApi } from "../../services/api";

export function usePortfolioSummary() {
  return useQuery({ queryKey: ["portfolio", "summary"], queryFn: portfolioApi.summary });
}

export function useHoldings(accountId?: number) {
  return useQuery({
    queryKey: ["portfolio", "holdings", accountId ?? "all"],
    queryFn: () => portfolioApi.holdings(accountId),
  });
}

export function useAllocation() {
  return useQuery({ queryKey: ["analytics", "allocation"], queryFn: analyticsApi.allocation });
}

export function usePerformance() {
  return useQuery({ queryKey: ["analytics", "performance"], queryFn: analyticsApi.performance });
}

export function useRisk() {
  return useQuery({ queryKey: ["analytics", "risk"], queryFn: analyticsApi.risk });
}
