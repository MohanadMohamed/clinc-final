import { QueryClient } from "@tanstack/react-query"

export const createQueryClient = () => new QueryClient({
  defaultOptions: {
    // An offline write must fail now, not wait to execute on reconnect.
    mutations: { retry: false, networkMode: "always" },
  },
})
