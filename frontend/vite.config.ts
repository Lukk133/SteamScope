import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    // ECharts sam w sobie waży ~600 kB minified — ostrzeżenie Rollupa
    // (limit domyślny 500 kB) jest nieistotne po wydzieleniu go do osobnego
    // chunka, który jest osobno cache'owany przez przeglądarkę.
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ["echarts", "vue-echarts"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
