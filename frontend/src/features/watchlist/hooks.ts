import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { watchlistApi } from "../../services/api";

export function useWatchlist(status?: string) {
  return useQuery({ queryKey: ["watchlist", status ?? "all"], queryFn: () => watchlistApi.list(status) });
}

function useInvalidateWatchlist() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["watchlist"] });
}

export function useCreateWatchlistEntry() {
  const invalidate = useInvalidateWatchlist();
  return useMutation({ mutationFn: watchlistApi.create, onSuccess: invalidate });
}

export function useUpdateWatchlistEntry() {
  const invalidate = useInvalidateWatchlist();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof watchlistApi.update>[1] }) =>
      watchlistApi.update(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteWatchlistEntry() {
  const invalidate = useInvalidateWatchlist();
  return useMutation({ mutationFn: watchlistApi.delete, onSuccess: invalidate });
}
