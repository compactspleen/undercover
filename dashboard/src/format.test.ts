import { expect, it } from "vitest";
import { formatClaimType, formatDate, formatMoney } from "./format";

it("shows amounts in US dollars", () => {
  expect(formatMoney(1250)).toBe("$1,250.00");
  expect(formatMoney(420)).toBe("$420.00");
});

it("names claim types in words", () => {
  expect(formatClaimType("emergency_medical")).toBe("Emergency medical");
});

it("shows a date as written, whatever the time zone", () => {
  expect(formatDate("2026-06-18")).toBe("Jun 18, 2026");
});
