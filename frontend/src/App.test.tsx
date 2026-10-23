import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, expect, test, vi } from "vitest"
import App from "./App"
const user = { id: "1a213739-e55c-42d7-aef0-bbd23f07318d", username: "synthetic", role: "doctor" }
function mount(path = "/") { return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>) }
afterEach(() => vi.unstubAllGlobals())
test("restores doctor session from API", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true,json:async()=>user})); mount(); expect(await screen.findByText("مساحة العمل جاهزة")).toBeInTheDocument(); expect(screen.getByText("مساحة الطبيب")).toBeInTheDocument() })
test("receptionist does not see doctor navigation", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:true,json:async()=>({...user,role:"receptionist"})})); mount(); expect(await screen.findByText("مساحة العمل جاهزة")).toBeInTheDocument(); expect(screen.queryByText("مساحة الطبيب")).not.toBeInTheDocument() })
test("anonymous visitor gets login", async () => { vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok:false,status:401})); mount(); expect(await screen.findByRole("heading",{name:"مرحباً بعودتك"})).toBeInTheDocument() })
