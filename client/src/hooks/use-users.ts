import { useMutation } from "@tanstack/react-query";
import { api } from "@shared/routes";

export function useCheckAvailability() {
  return useMutation({
    mutationFn: async (username: string) => {
      const res = await fetch(api.users.checkAvailability.path, {
        method: api.users.checkAvailability.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      });
      
      if (!res.ok) {
        throw new Error("Failed to check username availability");
      }
      
      return api.users.checkAvailability.responses[200].parse(await res.json());
    },
  });
}
