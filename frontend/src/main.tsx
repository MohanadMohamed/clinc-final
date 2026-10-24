import { QueryClientProvider } from "@tanstack/react-query"
import { createQueryClient } from "./lib/query-client"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import App from "./App"
import "./index.css"

const queryClient = createQueryClient()

createRoot(document.getElementById("root")!).render(
  <StrictMode><QueryClientProvider client={queryClient}><BrowserRouter basename={import.meta.env.BASE_URL}><App /></BrowserRouter></QueryClientProvider></StrictMode>,
)
