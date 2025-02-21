async function init() {
    const tokenResponse = await fetch("/session");
    const data = await tokenResponse.json();
    const EPHEMERAL_KEY = data.client_secret.value;

    const pc = new RTCPeerConnection();

    // 🔹 Crear un solo elemento de audio para evitar duplicados
    let audioEl = document.getElementById("openai-audio");
    if (!audioEl) {
        audioEl = document.createElement("audio");
        audioEl.id = "openai-audio";
        audioEl.autoplay = true;
        document.body.appendChild(audioEl);
    }

    pc.ontrack = (e) => {
        console.log("🎙️ Recibiendo audio de OpenAI...");
        audioEl.srcObject = e.streams[0];
    };

    const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
    pc.addTrack(ms.getTracks()[0]);

    const dc = pc.createDataChannel("oai-events");

    dc.addEventListener("message", async (e) => {
        try {
            const evento = JSON.parse(e.data);

            if (evento.type === "response.done" && evento.response.output[0]?.type === "function_call") {
                const functionCall = evento.response.output[0];

                console.log("🔹 Function Calling activado:", functionCall);

                let functionArgs;
                try {
                    functionArgs = JSON.parse(functionCall.arguments);
                } catch (error) {
                    console.error("❌ Error al parsear argumentos:", error, functionCall.arguments);
                    return;
                }

                // 🔹 Enviar la solicitud a Function Calling en el servidor
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

                console.log("🔹 Enviando respuesta de Function Calling a OpenAI:", data);
                dc.send(JSON.stringify(data));
            }
        } catch (error) {
            console.error("❌ Error procesando Function Calling:", error);
        }
    });

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
