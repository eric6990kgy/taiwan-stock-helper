import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { recommendationsApi, strategyApi } from "../../services/api";

export function useRecommendations(since?: string) {
  return useQuery({
    queryKey: ["recommendations", since ?? "all"],
    queryFn: () => recommendationsApi.list(since),
  });
}

export function useStrategyVersions() {
  return useQuery({ queryKey: ["strategy-versions"], queryFn: strategyApi.listVersions });
}

export function usePendingStrategyChanges(status?: string) {
  return useQuery({
    queryKey: ["strategy-pending", status ?? "all"],
    queryFn: () => strategyApi.listPending(status),
  });
}

function useInvalidateStrategy() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["strategy-versions"] });
    queryClient.invalidateQueries({ queryKey: ["strategy-pending"] });
  };
}

export function useProposeStrategyChange() {
  const invalidate = useInvalidateStrategy();
  return useMutation({ mutationFn: strategyApi.proposeChange, onSuccess: invalidate });
}

export function useConfirmPendingChange() {
  const invalidate = useInvalidateStrategy();
  return useMutation({ mutationFn: strategyApi.confirmPending, onSuccess: invalidate });
}

export function useRejectPendingChange() {
  const invalidate = useInvalidateStrategy();
  return useMutation({ mutationFn: strategyApi.rejectPending, onSuccess: invalidate });
}
