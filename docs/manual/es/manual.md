% UNO Overlays para OpenDeck — Manual
% Índice

# Introducción {#introduction}

UNO Overlays controla los overlays de [UNO](https://overlays.uno) (Singular.live) desde OpenDeck en Linux, con teclas y knobs: mostrar y ocultar, slots del servidor, marcador, relojes, fuentes de datos, encuestas, metas, macros, OBS Studio y diagnóstico.

Está pensado para la Rise Mode Vision 01 (15 teclas) y la Vision Sound 01 (6 teclas, 3 knobs y 3 botones sin pantalla), y funciona con cualquier dispositivo que OpenDeck admita.

- Cada tecla muestra su estado: el icono es **blanco** fuera del aire y **rojo intenso** en el aire. El estado llega de UNO en tiempo real.
- Cada operación en UNO, desde cualquier dispositivo, tecla, knob o inspector, pasa por **una cola global**, de una en una y en orden.
- Los disparadores, los grupos exclusivos y la lista de control apps son **globales**: funcionan con cualquier perfil o dispositivo en pantalla.

# Instalación {#installation}

## Requisitos

- OpenDeck para Linux 2.6.0 o posterior.
- Python 3.10 o posterior, con certificados HTTPS (Debian/Ubuntu: `sudo apt install python3 ca-certificates`).
- Acceso a internet para comunicarse con UNO.
- OBS Studio 28 o posterior, solo para las acciones y los disparadores de OBS.
- Nada más: la única dependencia (`websockets`) viene dentro del paquete.

## Instalar o actualizar

1. Descarga `opendeck-uno-overlays-<versión>-linux.plugin.zip` de la release.
2. En OpenDeck, abre **Plugins → Install from file** y elige el archivo.
3. La instalación sustituye la carpeta anterior del plugin. Teclas, knobs y configuración se conservan: los identificadores del plugin y de sus acciones no cambiaron.
4. Si una tecla no se actualiza, reinicia OpenDeck.

![OpenDeck: Plugins → Install from file](botao_instalar_plugins.jpg)

## Actualizar desde la versión 1.0

- Los disparadores de las teclas Overlay pasan solos a la lista global la primera vez que aparece cada tecla. Una tecla que nunca aparece (otro perfil, un dispositivo desconectado) conserva sus disparadores antiguos hasta que aparezca una vez: abre ese perfil una vez después de actualizar.
- La opción "Ediciones en el aire (opcional) – Ocultar, cambiar, volver a mostrar" ya no existe: las ediciones en el aire siempre se escriben directamente, tras la pausa definida en la página de configuración.

# Primeros pasos {#first-steps}

1. En UNO, abre el Control App del overlay, **? → API Description**, y copia el token: la parte de la dirección entre `/controlapps/` y `/api`. Usa el token de control, no la URL de salida que se usa en OBS.
2. En OpenDeck, arrastra una acción **UNO Overlays** a una tecla, pega el token en **Token de la API** y haz clic en **Conectar / Recargar**.
3. Elige el overlay (la lista tiene búsqueda y ★ favoritos) y lo que hace la tecla. Las ediciones del formulario van directamente a UNO; espera **Guardado en UNO.**
4. Cada campo tiene un **?** al lado: pasa el puntero por encima, o llega a él con Tab, para leer qué hace el campo. Esc cierra el texto.

![Inspector de una tecla Overlay](inspetor_overlay.jpg)

# Página de configuración {#settings-page}

Lo que comparten todas las teclas está en la página de configuración del propio plugin: en OpenDeck, en **Plugins**, en la tarjeta **UNO Overlays**, haz clic en el engranaje verde (**Settings**). La página se abre en el navegador predeterminado, acepta conexiones solo desde este equipo y se cierra tras 10 minutos sin uso.

![OpenDeck: el engranaje del plugin UNO Overlays](engrenagem_plugins.jpg)

![Página de configuración del plugin](pagina_configuracoes.jpg)

{{settings}}

## Idiomas

El plugin habla portugués (Brasil), inglés, español, italiano, alemán, japonés, chino (simplificado), coreano y francés. Con **Automático (idioma de OpenDeck)**, sigue el idioma elegido en la configuración de OpenDeck; un idioma elegido en la página de configuración tiene prioridad. OpenDeck no ofrece italiano, así que el italiano solo se elige en la página de configuración. Cuando cambia el idioma de OpenDeck, vuelve a abrir un inspector o la página de configuración para que el plugin lo lea.

## Disparadores

Un disparador ejecuta una función cuando ocurre un evento, como los disparadores de vMix: mostrar u ocultar un overlay tras un retardo de hasta 30 000 ms. Eventos: una escena de OBS entra o sale del programa, la transmisión empieza o termina, la grabación empieza o termina, un overlay de UNO entra o sale del aire (los encadenamientos "Cuando este overlay entra/sale del aire" de la versión 1.0). Usa **Añadir disparador** para crear todos los que necesites; cada uno se puede desactivar sin borrarlo.

Cada disparador escribe en el registro del plugin: el evento recibido, la decisión (se disparó o se ignoró, y por qué) y el resultado en UNO, sin tokens.

## Grupos exclusivos

Los overlays del mismo grupo nunca están en el aire a la vez: mostrar uno oculta los demás, también aquellos cuya tecla no está en pantalla. Las teclas Overlay eligen su grupo por nombre; el tiempo y los miembros están en la página de configuración.

# Cómo funciona {#how-it-works}

- **Cola global.** Todas las teclas, knobs e inspectores de todos los dispositivos entran en una sola cola: una operación en UNO cada vez, en orden. Los giros sobre el mismo campo se suman en una sola escritura.
- **Límites.** La cola espera la siguiente ventana cuando alcanza los límites que anuncia UNO. El plan gratuito de uno tiene un límite diario de 10 000 llamadas a la App API; la tecla Estado las cuenta.
- **Escrituras.** Solo el servidor confirma una escritura; nada se repite solo tras un tiempo de espera agotado.
- **Ediciones en el aire.** Con el overlay en el aire, una edición se envía solo tras una pausa sin cambios (1000 ms por defecto), para que el público nunca vea una palabra a medio escribir. Cerrar el inspector, pasar a otro campo, pulsar una tecla o el Pánico la envían al instante.
- **Teclas fuera de pantalla.** Los temporizadores de Auto Close y las pulsaciones ya hechas siguen tras cambiar de perfil; solo un cambio real en la configuración de la tecla, el Pánico o una nueva pulsación los cancelan.

# Limitaciones {#limitations}

- **Visor y knob.** Una tecla Visor y su knob solo funcionan mientras ambos están en pantalla: el knob guarda lo que está eligiendo, y OpenDeck solo informa al plugin de los knobs del perfil seleccionado.
- **Restaurar.** El conjunto de overlays que Restaurar vuelve a mostrar vive en memoria: reiniciar el plugin lo olvida.
- **Retardos de disparadores.** Un retardo de disparador que ya está contando sobrevive a las ediciones del disparador; el Pánico lo cancela.
- **Teclas borradas.** OpenDeck envía el mismo evento cuando se borra una tecla y cuando se cambia su perfil, así que un Auto Close que ya está contando termina normalmente (como máximo 120 s).
- **Migración.** Los disparadores de la versión 1.0 pasan a la lista global solo cuando su tecla aparece al menos una vez.
- **Quiz.** Revelar respuesta es genérico: elige el campo y los valores que tu overlay usa para revelar la respuesta.

# Casos de uso {#use-cases}

## Marcador

Teclas Campos numéricos para cada equipo (la tecla muestra +1, +2, +3…), una tecla Visor de valor para cada marcador, Deshacer, Bloqueo, Cambiar de lado cuando los equipos cambian de campo, Ciclo para el periodo y Reiniciar mantenido 2 s al final.

## Quiz

Un knob Rueda de slots con el carrusel activado: cada giro pone en el aire la pregunta siguiente; pulsar muestra u oculta el overlay. Una tecla Revelar respuesta revela la respuesta y copia la opción correcta en el campo de resaltado; la pregunta siguiente la vuelve a ocultar sola.

## Reloj

Una tecla Reloj en un campo de texto: cuenta atrás, cuenta progresiva, hora del día o hasta una hora de fin, con colores de cierre. En un knob, girar ajusta el tiempo y una tecla Visor lo muestra.

## Ticker y listas

Una Fuente de datos con una lista escrita, un archivo .txt o .csv, asignada a los campos del overlay, con Auto Next y Repetir.

## OBS Studio

Una tecla OBS: escena cambia la escena de programa y puede mostrar un overlay. Un disparador muestra el rótulo de la cámara cuando la escena "Webcam" entra en programa y lo oculta cuando sale. OBS: actualizar navegador recarga varias fuentes de navegador, o todas las fuentes de navegador de una escena.

# Acciones {#actions}

{{actions}}

# Solución de problemas {#troubleshooting}

- **"Introduce el token de control de la API, no la URL de salida."** Pega solo el token (letras, números, `_` y `-`).
- **"UNO HTTP 4xx".** El token es incorrecto o fue revocado: cópialo de nuevo en **API Description**.
- **"UNO HTTP 429".** Demasiadas solicitudes: espera un momento; evita herramientas que consulten UNO con el mismo token.
- **"OBS no está conectado…".** Configúralo en la página de configuración y comprueba que OBS está abierto.
- **El engranaje no abre nada.** No hay navegador predeterminado: `xdg-settings get default-web-browser` muestra cuál usa el sistema.
- **Una tecla solo muestra una alerta.** La mesa está bloqueada (Bloqueo de mesa en rojo) o la tecla está fuera de las escenas de OBS permitidas.
- **Un disparador no se ejecutó.** Mira el registro del plugin: cada disparador escribe si se disparó o se ignoró, y por qué. Registro: `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

# Privacidad y seguridad {#privacy}

Los nombres y textos de los overlays son datos personales y van a UNO. El plugin no envía nada a sus autores y no escribe tokens en los registros. Los tokens se guardan en la configuración de OpenDeck en este equipo; la página de configuración nunca vuelve a mostrar un token ni la contraseña de OBS. Las escenas guardadas y el registro se pueden borrar a petición (Eliminar escena guardada, Borrar registro). Para ejercer tus derechos según la LGPD de Brasil, abre una issue en el proyecto. Detalles en PRIVACY.md y SECURITY.md del plugin.
