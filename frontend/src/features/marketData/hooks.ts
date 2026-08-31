import { useMutation, useQueryClient } from "@tanstack/react-query";
import { marketDataApi } from "../../services/api";

export function useUpdateMarketData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: marketDataApi.update,
    onSuccess: () => {
      // Ingested data feeds straight into the same reads everything else
      // already uses (MockMarketDataProvider serves both) -- refresh the
      // views that would show new prices/fundamentals/demo-data status.
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      queryClient.invalidateQueries({ queryKey: ["research"] });
      queryClient.invalidateQueries({ queryKey: ["prices"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}
