import { beforeEach, expect, test, vi } from "vitest";
import { choosePerspective, data, resetDemo } from "./state";
import * as demo from "./adapters";
import { cairoDate, localCandidates, cairoDayBounds } from "../src/lib/cairo";
beforeEach(() => { resetDemo(); choosePerspective("doctor"); });
test("synthetic patient CRUD and searches never call the network", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network forbidden"));
    try {
        const p = await demo.createPatient({ full_name: "مريض اصطناعي لاختبار", phone: "00000009999", birth_date: null });
        await demo.updatePatient(p.id, { full_name: "مريض اصطناعي معدل" });
        expect((await demo.listPatients("معدل", 1)).items[0].id).toBe(p.id);
        await demo.archivePatient(p.id);
        expect((await demo.listPatients("معدل", 1)).total).toBe(0);
        expect(fetch).not.toHaveBeenCalled();
    }
    finally {
        fetch.mockRestore();
    }
});
test("demo overlap uses half-open slots and cancellation releases them", async () => {
    const day = cairoDate(), start_at = localCandidates(day, "12:00")[0], end_at = localCandidates(day, "12:30")[0];
    const input = { patient_id: data.patients[5].id, kind: "first_visit" as const, start_at, end_at };
    const a = await demo.createAppointment(input);
    await expect(demo.createAppointment(input)).rejects.toMatchObject({ status: 409 });
    await demo.createAppointment({ ...input, start_at: end_at, end_at: localCandidates(day, "13:00")[0] });
    await demo.cancelAppointment(a.id);
    await expect(demo.createAppointment(input)).resolves.toMatchObject({ status: "scheduled" });
    const bounds = cairoDayBounds(day);
    expect((await demo.getAppointments(bounds.start, bounds.end, "cancelled", 1)).total).toBe(1);
});
test("visits support revisions/finalization and perspectives are only a simulation", async () => {
    const v = await demo.createVisit(data.patients[4].id);
    const saved = await demo.saveVisit(v.id, 1, { neurological_note: "نص اصطناعي", psychiatric_note: "نص تجريبي", follow_up_plan: "خطة اصطناعية" });
    expect(saved.revision).toBe(2);
    await demo.finalizeVisit(v.id, 2);
    await expect(demo.saveVisit(v.id, 2, { neurological_note: "", psychiatric_note: "", follow_up_plan: "" })).rejects.toThrow();
    expect((await demo.getVisitHistory(v.id)).revisions).toHaveLength(3);
    choosePerspective("receptionist");
    await expect(demo.listVisits()).rejects.toThrow("منظور الطبيب");
});
test("simulated payments retain integer totals and suppress duplicate retries", async () => {
    const invoice = await demo.createInvoice({ patient_id: data.patients[3].id, kind: "first_visit", idempotency_key: "synthetic-invoice" });
    await demo.issueInvoice(invoice.id);
    const payment = await demo.recordPayment(invoice.id, 5050, "synthetic-payment");
    expect((await demo.recordPayment(invoice.id, 5050, "synthetic-payment")).id).toBe(payment.id);
    const current = await demo.getInvoice(invoice.id);
    expect(current.paid_minor).toBe(5050);
    expect(current.total_minor).toBe(current.paid_minor + current.balance_minor);
    await expect(demo.recordPayment(invoice.id, 999999, "overpay")).rejects.toThrow();
    expect((await demo.getDaily(cairoDate())).received_minor).toBe(15050);
    resetDemo();
    expect((await demo.listInvoices()).total).toBe(2);
});
