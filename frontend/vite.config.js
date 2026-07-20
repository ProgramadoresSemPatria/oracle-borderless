/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            "/conversations": "http://localhost:8000",
        },
    },
    test: {
        environment: "jsdom",
        globals: true,
    },
});
