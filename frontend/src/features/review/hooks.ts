import { useQuery } from "@tanstack/react-query";
import { reviewApi } from "../../services/api";

export function useReviewSummary(action?: string) {
  return useQuery({ queryKey: ["review-summary", action ?? "all"], queryFn: () => reviewApi.summary(action) });
}

export function useReviewOutcomes(action?: string) {
  return useQuery({ queryKey: ["review-outcomes", action ?? "all"], queryFn: () => reviewApi.outcomes(action) });
}
