import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { accountsApi, assetsApi, transactionsApi, type TransactionFilters } from "../../services/api";

export function useAccounts() {
  return useQuery({ queryKey: ["accounts"], queryFn: accountsApi.list });
}

export function useAssets() {
  return useQuery({ queryKey: ["assets"], queryFn: assetsApi.list });
}

export function useTransactions(filters: TransactionFilters) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => transactionsApi.list(filters),
  });
}

function useInvalidatePortfolio() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["transactions"] });
    queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    queryClient.invalidateQueries({ queryKey: ["analytics"] });
  };
}

export function useCreateTransaction() {
  const invalidate = useInvalidatePortfolio();
  return useMutation({
    mutationFn: transactionsApi.create,
    onSuccess: invalidate,
  });
}

export function useDeleteTransaction() {
  const invalidate = useInvalidatePortfolio();
  return useMutation({
    mutationFn: transactionsApi.delete,
    onSuccess: invalidate,
  });
}
