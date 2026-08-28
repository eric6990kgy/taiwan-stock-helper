import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { researchApi, thesisApi } from "../../services/api";

export function useResearchPage(ticker: string | null) {
  return useQuery({
    queryKey: ["research", ticker],
    queryFn: () => researchApi.page(ticker as string),
    enabled: !!ticker,
  });
}

export function usePrices(ticker: string | null, range: string) {
  return useQuery({
    queryKey: ["prices", ticker, range],
    queryFn: () => researchApi.prices(ticker as string, range),
    enabled: !!ticker,
  });
}

export function useUpsertThesis(ticker: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof thesisApi.upsert>[1]) => thesisApi.upsert(ticker, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["research", ticker] }),
  });
}
