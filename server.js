import express from "express";
import fetch from "node-fetch";
import dotenv from "dotenv";
import fs from "fs";
import { spawnSync } from "child_process";

dotenv.config();

const app = express();
const PORT = 3000;

// Middleware para leer JSON
app.use(express.json());

// Endpoint para obtener una ephemeral API key con optimizaciones
app.get("/session", async (req, res) => {
  try {
    const response = await fetch("https://api.openai.com/v1/realtime/sessions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4o-realtime-preview-2024-12-17",
        voice: "verse",
        input_audio_format: "pcm16",
        output_audio_format: "pcm16",
        max_response_output_tokens: 200,
        turn_detection: {
          "type": "server_vad",
          "threshold": 0.5,
          "prefix_padding_ms": 300,
          "silence_duration_ms": 500,
          "create_response": true
        },
        instructions: "Eres un asistente creado por Santiago Paz. Solo responde preguntas basadas en la base de datos y no te desvíes del tema.",
        tools: [
          {
            "type": "function",
            "name": "buscar_pregunta_frecuente",
            "description": "Busca una respuesta en la base de datos de preguntas frecuentes",
            "parameters": {
              "type": "object",
              "properties": {
                "pregunta": {
                  "type": "string",
                  "description": "La pregunta del usuario"
                }
              },
              "required": ["pregunta"]
            }
          }
        ],
        tool_choice: "auto"
      }),
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error("Error al crear la sesión:", error);
    res.status(500).json({ error: "Error interno del servidor" });
  }
});

// Function Calling con FAISS
app.post("/function_call", async (req, res) => {
  try {
    const { name, arguments: args, call_id } = req.body;

    if (name === "buscar_pregunta_frecuente") {
      const preguntaUsuario = args.pregunta.trim();

      // 🔹 Ejecutar FAISS para encontrar la mejor respuesta
      const result = spawnSync("python", ["embeddings/buscar_pregunta_faiss.py", preguntaUsuario], { encoding: "utf-8" });
      const respuesta = result.stdout.trim();

      console.log(`🔹 Respuesta encontrada: "${respuesta}"`);

      return res.json({
        type: "conversation.item.create",
        item: {
          type: "function_call_output",
          call_id: call_id,
          output: JSON.stringify({ respuesta })
        }
      });
    }

    res.status(400).json({ error: "Función no reconocida" });
  } catch (error) {
    console.error("❌ Error en Function Calling:", error);
    res.status(500).json({ error: "Error en el servidor" });
  }
});

// Servir archivos estáticos del cliente
app.use(express.static("public"));

app.listen(PORT, () => console.log(`✅ Server running on http://localhost:${PORT}`));
