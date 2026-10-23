import { fileURLToPath, URL } from "node:url"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vitest/config"
import { readFileSync } from "node:fs"

const testTls = process.env.CLINIC_TEST_CERT && process.env.CLINIC_TEST_KEY ? {
  cert: readFileSync(process.env.CLINIC_TEST_CERT),
  key: readFileSync(process.env.CLINIC_TEST_KEY),
} : undefined

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { host: "127.0.0.1", port: 5173, strictPort: true, https: testTls,
    proxy: { "/api": { target: testTls ? "https://127.0.0.1:8443" : "http://127.0.0.1:8000", secure: !testTls } } },
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.ts"] },
})
