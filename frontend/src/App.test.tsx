import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, expect, test, vi } from "vitest"
import App from "./App"

afterEach(() => vi.unstubAllGlobals())

test("Arabic shell displays actual API success", async () => {
  const fetcher = vi.fn().mockImplementation(async (url: string) => ({ ok: true, json: async () => ({ status: url.endsWith("ready") ? "ready" : "ok" }) }))
  vi.stubGlobal("fetch", fetcher)
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><App /></MemoryRouter></QueryClientProvider>)
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("عيادة المخ والأعصاب")
  expect(await screen.findByText("الخادم وقاعدة البيانات متصلان")).toBeInTheDocument()
  expect(fetcher.mock.calls.map(call => call[0])).toEqual(["/api/health", "/api/health/ready"])
})

test("DB failure is visible rather than reporting successful connection", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => ({ status: "unavailable" }) }))
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><App /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByText("تعذر الاتصال بالخادم أو قاعدة البيانات")).toBeInTheDocument()
})
