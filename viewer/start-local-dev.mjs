import { createServer } from "vite";

const server = await createServer({
  configFile: "vite.config.mjs",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});

await server.listen();
server.printUrls();
setInterval(() => {}, 60_000);
