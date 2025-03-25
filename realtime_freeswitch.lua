session:answer()
freeswitch.consoleLog("INFO", "Llamada contestada\n")

local audio_respuesta = "/home/sysadmin/encuesta_IVR/tmp/assistant_response.wav"
local pregunta_audio = "/home/sysadmin/encuesta_IVR/tmp/pregunta.wav"

-- Loop principal para múltiples interacciones
while session:ready() do
    -- Solicitar al usuario que haga su pregunta
    session:streamFile("/home/sysadmin/encuesta_IVR/sounds/Beep_Inicio.wav")

    -- Grabar pregunta del usuario
    session:execute("record", pregunta_audio .. " 30 100 2")

    -- Ejecutar script Python en segundo plano
    os.execute("/home/sysadmin/encuesta_IVR/venv/bin/python3 /home/sysadmin/encuesta_IVR/scripts/asistente_virtual.py " .. pregunta_audio .. " > /dev/null 2>&1 &")

    -- Mensaje de espera mientras procesa
    session:streamFile("/home/sysadmin/encuesta_IVR/sounds/Beep_Pensar.wav")

    -- Esperar la respuesta de Python con un tiempo límite (ej. 20 segundos)
    local espera = 0
    local max_espera = 40  -- Máximo 20 segundos (40 * 500ms)
    local respuesta_lista = false

    while espera < max_espera do
        local file = io.open(audio_respuesta, "rb")
        if file then
            local size = file:seek("end")
            file:close()
            if size > 1000 then
                freeswitch.consoleLog("INFO", "Respuesta lista!\n")
                respuesta_lista = true
                break
            end
        end
        espera = espera + 1
        session:sleep(500)
    end

    if respuesta_lista then
        -- Reproducir respuesta generada por Python
        session:streamFile(audio_respuesta)
    else
        -- Informar que no se generó respuesta
        session:streamFile("/home/sysadmin/encuesta_IVR/sounds/Beep_Error.wav")
    end

    -- Limpiar archivos temporales para siguiente interacción
    os.execute("rm -f " .. audio_respuesta)
    os.execute("rm -f " .. pregunta_audio)

    -- Pequeña pausa antes de la siguiente interacción
    session:sleep(500)
end

-- Finalizar sesión si el usuario cuelga
session:hangup()