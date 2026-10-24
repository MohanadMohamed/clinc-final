import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"
import PatientsPage from "./PatientsPage"

afterEach(() => vi.unstubAllGlobals())

test("patient list reports a connection failure in Arabic and recovers on retry", async () => {
  const fetchMock = vi.fn()
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
    .mockResolvedValue({ ok: true, json: async () => ({ items: [], total: 0, page: 1, page_size: 10 }) })
  vi.stubGlobal("fetch", fetchMock)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><PatientsPage /></QueryClientProvider>)
  expect(await screen.findByRole("alert")).toHaveTextContent("تعذر الاتصال بالخادم")
  fireEvent.click(screen.getByRole("button", { name: "إعادة المحاولة" }))
  expect(await screen.findByText("عدد السجلات: 0")).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(2)
  client.clear()
})
