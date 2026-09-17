import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { accountsApi, assetsApi, importExportApi, transactionsApi, type TransactionFilters } from "../../services/api";

export function useAccounts() {
  return useQuery({ queryKey: ["accounts"], queryFn: accountsApi.list });
}

export function useAssets() {
  return useQuery({ queryKey: ["assets"], queryFn: assetsApi.list });
}

/** Phase 11: preview a ticker's real FinMind company info before creating
 * it. `enabled` is left to the caller (debounce first, don't fire on every
 * keystroke). */
export function useAssetLookup(ticker: string, enabled: boolean) {
  return useQuery({
    queryKey: ["asset-lookup", ticker],
    queryFn: () => assetsApi.lookup(ticker),
    enabled,
    retry: false,
  });
}

export function useQuickCreateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: assetsApi.quickCreate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
  });
}

function useInvalidateAccounts() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["accounts"] });
}

export function useCreateAccount() {
  const invalidate = useInvalidateAccounts();
  return useMutation({
    mutationFn: accountsApi.create,
    onSuccess: invalidate,
  });
}

export function useUpdateAccount() {
  const invalidate = useInvalidateAccounts();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof accountsApi.update>[1] }) =>
      accountsApi.update(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteAccount() {
  const invalidate = useInvalidateAccounts();
  return useMutation({
    mutationFn: accountsApi.delete,
    onSuccess: invalidate,
  });
}

export function useImportTransactions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: importExportApi.importTransactions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });
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
