import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { journalApi } from "../../services/api";
import type { JournalCategory } from "../../types/api";

export function useJournalEntries(
  params: { asset_id?: number; category?: JournalCategory; date_from?: string; date_to?: string } = {},
) {
  return useQuery({ queryKey: ["journal", params], queryFn: () => journalApi.list(params) });
}

function useInvalidateJournal() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["journal"] });
}

export function useCreateJournalEntry() {
  const invalidate = useInvalidateJournal();
  return useMutation({ mutationFn: journalApi.create, onSuccess: invalidate });
}

export function useUpdateJournalEntry() {
  const invalidate = useInvalidateJournal();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof journalApi.update>[1] }) =>
      journalApi.update(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteJournalEntry() {
  const invalidate = useInvalidateJournal();
  return useMutation({ mutationFn: journalApi.delete, onSuccess: invalidate });
}
