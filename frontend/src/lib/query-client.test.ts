import { MutationObserver, onlineManager } from "@tanstack/react-query"
import { expect, test, vi } from "vitest"
import { createQueryClient } from "./query-client"

test("offline mutations fail without queuing or replay on reconnect", async () => {
  const client = createQueryClient()
  client.mount()
  onlineManager.setOnline(false)
  const write = vi.fn().mockRejectedValue(new Error("offline"))
  const observer = new MutationObserver(client, { mutationFn: write })
  try {
    await expect(observer.mutate(undefined)).rejects.toThrow("offline")
    expect(observer.getCurrentResult().isPaused).toBe(false)
    onlineManager.setOnline(true)
    await client.resumePausedMutations()
    expect(write).toHaveBeenCalledTimes(1)
  } finally {
    onlineManager.setOnline(true)
    client.unmount()
    client.clear()
  }
})
