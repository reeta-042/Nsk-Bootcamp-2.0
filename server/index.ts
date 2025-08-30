import "dotenv/config";
import express from "express";
import cors from "cors";
import { handleDemo } from "./routes/demo";
import { handleGenerateJourney } from "./routes/generate-journey";
import { handleImageUpload, uploadMiddleware } from "./routes/upload-image";

export function createServer() {
  const app = express();

  // Middleware
  app.use(cors());
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Example API routes
  app.get("/api/ping", (_req, res) => {
    const ping = process.env.PING_MESSAGE ?? "ping";
    res.json({ message: ping });
  });

  app.get("/api/demo", handleDemo);

  // Journey app routes
  app.post("/api/generate-journey", handleGenerateJourney);
  app.post("/api/upload-image", uploadMiddleware, handleImageUpload);

  return app;
}
