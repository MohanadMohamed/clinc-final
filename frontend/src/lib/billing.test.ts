import { describe, expect, it } from "vitest"
import { textToMinor } from "./billing"

describe("billing amount entry", () => {
  it("converts EGP decimals to integer piasters exactly", () => {
    expect(textToMinor("150.50")).toBe(15050)
    expect(textToMinor("0.01")).toBe(1)
    expect(textToMinor("12.3")).toBe(1230)
  })

  it("rejects ambiguous, negative and excessive amounts", () => {
    for (const amount of ["0", "-1", "1.234", "1,000", "20000000.01"]) {
      expect(() => textToMinor(amount)).toThrow()
    }
  })
})
