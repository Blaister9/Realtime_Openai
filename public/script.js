// script.js - Cliente WebRTC optimizado para Function Calling y corrección de doble audio

async function init() {
    // Obtener una ephemeral API key desde el servidor
    const tokenResponse = await fetch("/session");
    const data = await tokenResponse.json();
    const EPHEMERAL_KEY = data.client_secret.value;
  
    // Crear la conexión WebRTC
    const pc = new RTCPeerConnection();
  
    // Crear un solo elemento de audio para reproducir la voz de OpenAI
    let audioEl = document.getElementById("openai-audio");
    if (!audioEl) {
        audioEl = document.createElement("audio");
        audioEl.id = "openai-audio";
        audioEl.autoplay = true;
        document.body.appendChild(audioEl);
    }
  
    pc.ontrack = (e) => {
        console.log("Recibiendo audio de OpenAI...");
        audioEl.srcObject = e.streams[0];
    };
  
    // Capturar el audio del micrófono
    const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
    pc.addTrack(ms.getTracks()[0]);
  
    // Crear un canal de datos para eventos
    const dc = pc.createDataChannel("oai-events");
    
    dc.addEventListener("message", async (e) => {
        try {
            const evento = JSON.parse(e.data);
            
            // Detectar si OpenAI llama a la función "buscar_pregunta_frecuente"
            if (evento.type === "response.done" && evento.response.output[0]?.type === "function_call") {
                const functionCall = evento.response.output[0];
    
                console.log("🔹 Function Calling activado:", functionCall);
    
                // 🔹 Intentamos parsear los argumentos de la función
                let functionArgs;
                try {
                    functionArgs = JSON.parse(functionCall.arguments);
                } catch (error) {
                    console.error("❌ Error al parsear argumentos de la función:", error, functionCall.arguments);
                    return;
                }
    
                // Enviar la solicitud al servidor para buscar la respuesta en preguntas.json
                const respuesta = await fetch("/function_call", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        name: functionCall.name,
                        arguments: functionArgs,
                        call_id: functionCall.call_id
                    })
                });
    
                const data = await respuesta.json();
                
                // 🔹 Ahora forzamos a OpenAI a procesar la respuesta en voz
                console.log("🔹 Enviando respuesta de Function Calling a OpenAI:", data);
                dc.send(JSON.stringify({
                    type: "response.create",
                    response: {
                        modalities: ["text", "audio"], // 🔹 Asegurar que OpenAI genere voz
                        input: [
                            {
                                type: "message",
                                role: "assistant",
                                content: [
                                    {
                                        type: "text",
                                        text: JSON.parse(data.item.output).respuesta
                                    }
                                ]
                            }
                        ]
                    }
                }));
            }
        } catch (error) {
            console.error("❌ Error procesando Function Calling:", error);
        }
    });
    

    // Iniciar la sesión con SDP
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const baseUrl = "https://api.openai.com/v1/realtime";
    const model = "gpt-4o-realtime-preview-2024-12-17";
    const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
            Authorization: `Bearer ${EPHEMERAL_KEY}`,
            "Content-Type": "application/sdp",
        },
    });

    const answer = { type: "answer", sdp: await sdpResponse.text() };
    await pc.setRemoteDescription(answer);
}
  
init();
