import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
const path = (value: string) => fileURLToPath(new URL(value, import.meta.url));
export default defineConfig({
    root: path("./portfolio"),
    base: "/clinc-final/",
    publicDir: false,
    envDir: false,
    envPrefix: "PORTFOLIO_",
    plugins: [
        react(), tailwindcss(),
        {
            name: "isolated-portfolio-boundary",
            transform(code, id) {
                // Presentation copy only, for shared screens in this isolated build.
                if (id.endsWith("/src/VisitsPage.tsx"))
                    return code.replace("هذه السجلات متاحة للطبيب فقط. تحفظ المسودات والمراجعات على الخادم.", "ملاحظات اصطناعية في منظور الطبيب. تحفظ التغييرات مؤقتاً في ذاكرة العرض فقط.");
                if (id.endsWith("/src/AppointmentsPage.tsx"))
                    return code.replace("يتحقق الخادم من مدة الزيارة وساعات العمل قبل الحفظ.", "يحاكي العرض حجز المواعيد ومنع التداخل. لا توجد حجوزات فعلية.");
            },
            generateBundle() {
                for (const id of this.getModuleIds()) {
                    if (/\/src\/lib\/(api|patients|appointments|visits|billing)\.ts$/.test(id) || /\/src\/(App|main)\.tsx$/.test(id)) {
                        this.error("Real application/auth/network module entered portfolio build");
                    }
                }
            },
        },
    ],
    resolve: { alias: [
            { find: /^@\/lib\/(api|patients|appointments|visits|billing)$/, replacement: path("./portfolio/adapters.ts") },
            { find: "@", replacement: path("./src") },
        ] },
    build: { outDir: path("./portfolio-dist"), emptyOutDir: true, sourcemap: false },
});
