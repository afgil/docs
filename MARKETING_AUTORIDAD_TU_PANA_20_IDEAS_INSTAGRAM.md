# Marketing de autoridad – Tu Pana: 20 ideas profundas para Instagram

Documento con know-how real extraído del código y dominio de Tu Pana. Cada idea sirve para enseñar en Instagram y posicionar a Tu Pana como referente en facturación electrónica Chile y SII.

---

## SII y certificación

### 1. El SII no tiene API pública para todo
Muchos flujos (cesión, tipo de compra, traza, libro de ventas) se hacen con integración controlada al portal del SII. Quien construye bien la capa que unifica eso (managers por flujo) evita que el usuario tenga que “entrar al SII a mano” para cada operación. **Enseñanza:** No es que el SII sea lento; es que no hay un solo botón “API” para todo. La expertise está en orquestar bien esos flujos.

### 2. Firma centralizada: las cookies que el SII exige
Para cesiones y otras operaciones firmadas, el backend debe enviar cookies específicas (`usa_firma_central`, `s_cc`). Si no las llevas, el flujo puede fallar aunque el login sea correcto. **Enseñanza:** El “error raro” en cesión a veces es solo que falta la cookie de firma centralizada. Quien lo sabe, lo corrige en minutos.

### 3. Persona natural vs certificado digital
El SII permite entrar con RUT/clave (persona natural) o con certificado digital. Según el flujo (por ejemplo cesión con firma), a veces se usa certificado para misma IP/origen y evitar bloqueos. **Enseñanza:** No es lo mismo “entrar al SII” que “hacer todas las operaciones que tu negocio necesita”. La elección persona natural vs certificado afecta qué puedes automatizar y con qué estabilidad.

### 4. El código interno del documento (dhdrCodigo) no es el folio
El SII identifica cada DTE con un código interno (dhdr/EHDR). No es el folio ni el tipo+folio: puede venir de la traza, del libro de ventas o de metadata. Sin ese código, operaciones como “obtener detalle” o ciertos reportes fallan. **Enseñanza:** Cuando el sistema “no encuentra” un documento en el SII, a veces el problema es que se está buscando por folio y lo que el SII pide es el código interno. Resolver varias fuentes en orden (traza → libro ventas → EHDR) es know-how real.

---

## DTE y tipos de documento

### 5. No todos los DTE llevan acuse ni “CEDIBLE” en el PDF
En el PDF, tipos 56, 61, 111, 112 no llevan acuse de recibo ni leyenda CEDIBLE. Mostrarlos igual que una factura 33 es un error de formato y de imagen ante el SII. **Enseñanza:** El diseño del PDF tributario no es “uno para todos”: por tipo de documento cambian recuadros, leyendas y acuse. Hacerlo bien evita observaciones y rechazos.

### 6. Boleta de honorarios 80 y 90 no son lo mismo
La 90 (terceros) no lleva actividad económica ni IVA en el PDF ni en la tabla; la 80 sí puede llevar dirección completa. La UI y el backend usan configuración por tipo para no mostrar columnas que no aplican. **Enseñanza:** Tratar todas las boletas de honorarios igual es un error. La 80 y la 90 tienen reglas distintas en campos, PDF y declaración.

### 7. Requisitos de dirección dependen del tipo de DTE
Boletas 39/41 no exigen dirección; exportación (110, 111, 112) pide dirección + ciudad; facturas y otros piden dirección completa (dirección, comuna, ciudad). Un solo “¿tiene dirección?” no basta. **Enseñanza:** La validación “dirección obligatoria” debe ser por tipo de documento. Una misma regla para todos genera rechazos o datos de más.

### 8. Forma de pago: solo Contado (1) o Crédito (2)
En el XML y en el PDF solo existen “Contado” (1) y “Crédito” (2). Cualquier lógica de “cuotas” o “parcial” debe mapearse a esos dos para el SII. **Enseñanza:** Lo que el negocio llama “3 cuotas” o “anticipo + saldo” a nivel tributario es Contado o Crédito. Quien mapea bien evita errores en el envío al SII.

---

## Cesión de facturas (AEC)

### 9. Cesión no es “enviar la factura”
Es un flujo regulado: formulario de cesión en el SII, generación del DTE Cedido (AEC), firma y envío al SII. Si usas datos del autorizador ya conocidos, puedes saltarte solo el paso de “pedir formulario”; firmar y enviar siguen siendo obligatorios. **Enseñanza:** Ceder una factura es un proceso con pasos formales. Confundirlo con “reenviar el PDF” lleva a incumplimiento y problemas con el cesionario.

### 10. Fecha “último vencimiento” en la cesión
La cesión lleva `ultimo_vencim` (última fecha de vencimiento). Debe ser coherente con el negocio (por ejemplo un mes después). Dejarla mal calculada puede invalidar o complicar la cesión. **Enseñanza:** La cesión no es solo “qué factura” sino “hasta cuándo”. Saber calcular y registrar bien el último vencimiento es parte del proceso correcto.

### 11. Documentos no cedibles
No se puede ceder un documento con nota de crédito total o parcial asociada. Elegir el primer documento cedible (tipo 33 o 34, sin N/C total/parcial) evita intentos que el SII rechazará. **Enseñanza:** Antes de intentar ceder, hay que validar que el DTE sea cedible. Factura con N/C total o parcial no lo es; intentarlo genera error y pérdida de tiempo.

---

## Recepción y estados (ERM, ACD, RCD)

### 12. ERM y ACD no son lo mismo
ERM es acuse de recibo (recibí el documento); ACD es aceptación de contenido (acepto el contenido). Ambos actualizan la traza. El IVA del receptor se rebaja con el acuse (ERM); el mérito ejecutivo suele ligarse a ACD. **Enseñanza:** Mezclar “recibí” con “acepto el contenido” genera problemas de plazos y contabilidad. En Instagram se puede explicar con un carrusel: “Recibí vs Acepté”.

### 13. RCD, RFT, RFP son reclamos; no es lo mismo que “rechazado por el SII”
Esos eventos marcan reclamos en la traza (contenido, otros rechazos). “Rechazado por el receptor” y “rechazado por el SII” son cosas distintas; la traza dice quién y por qué. **Enseñanza:** Cuando hay rechazo, hay que mirar el evento de traza para saber si fue el receptor o el SII y actuar en consecuencia (corregir documento, aclarar con cliente, etc.).

### 14. Tipo de compra se define en el SII después de recibir
Para facturas de compra (46) y otras recibidas, el “tipo de compra” (y a veces indicador de servicio) se consulta o cambia con `cambiaTipoCompra`. Las facturas internacionales (140) no tienen tipo de compra en el SII. **Enseñanza:** No basta con recibir la factura; para declarar bien hay que asegurar que el tipo de compra en el SII coincida con el uso real (activo, costo, etc.).

### 15. Período tributario: fecha que importa para el SII
Para tipo de compra y declaración, la fecha que suele importar es la de recepción del documento (traza), no solo la de emisión. Usar solo la fecha de emisión puede llevar a declarar en el mes equivocado. **Enseñanza:** “¿En qué mes declaro esta factura?” se responde con la fecha de recepción en el SII, no solo con la fecha del PDF.

---

## Cálculos y validaciones

### 16. Totales e IVA siempre enteros (redondeo ROUND_HALF_UP)
El SII espera montos netos, IVA y total en enteros. Calcular con decimales y redondear solo al final puede generar diferencias de 1 peso que el SII rechace o que desajusten libros. **Enseñanza:** La facturación electrónica exige redondeo consistente (por ítem y por total). Un peso de diferencia puede tumbar una emisión o una conciliación.

### 17. RUT en múltiples formatos: el mismo cliente “no existe”
El mismo RUT puede estar guardado con puntos (12.345.678-9) o sin (12345678-9). Buscar solo por un formato hace que “el cliente ya existe” no se encuentre y se dupliquen entidades. **Enseñanza:** Normalizar y buscar por RUT en todos los formatos habituales evita duplicados y “no encontré al cliente” cuando sí está en el sistema.

---

## Batch, Excel y webhooks

### 18. Excel masivo sin depender del SII en la subida
La estrategia correcta es guardar todo en base de datos y crear documentos en la misma request; no hacer scraping al SII en ese momento. Si falta algo (por ejemplo branch_code), se resuelve en background. Así se pueden subir cientos de filas sin depender de la disponibilidad del portal SII. **Enseñanza:** Un buen flujo de carga masiva no depende de que el SII responda en el segundo exacto de la subida. Primero se persiste; luego se completa y se emite.

### 19. Webhooks con reintentos en escalera
Los webhooks de documentos no son “un intento y listo”. Usar reintentos con delays (por ejemplo 1 min, 5 min, 15 min, 1 h, 6 h) tolera caídas cortas del cliente sin perder el evento (document.issued, delivered, rejected, etc.). **Enseñanza:** Quien integra con facturación electrónica debe esperar reintentos; quien ofrece la API debe implementarlos. Así la integración sigue funcionando aunque haya un corte de 5 minutos.

### 20. Estado del batch desde los ítems, no de un solo campo
El estado “real” del batch (completado/fallido) se calcula a partir de los estados de cada documento del batch (success, permanent_error, incomplete). Así backoffice y cliente ven lo mismo y no hay desincronización. **Enseñanza:** Un batch “en proceso” no es un flag mágico: es el agregado de cada documento. Mostrar ese estado coherente evita “dice que terminó pero faltan 3” y soportes innecesarios.

---

## Cómo usar este documento en Instagram

- **Carruseles:** 1 idea = 1 slide; slide final con CTA a Tu Pana o a perfil.
- **Reels:** Elegir 1 idea (por ejemplo ERM vs ACD, o “totales enteros”) y explicarla en 60–90 segundos.
- **Stories:** Pregunta del tipo “¿Sabías que…?” + 1 idea en 1–2 frases + link a blog o landing.
- **Texto largo:** Desarrollar 2–3 ideas en un post de 150–200 palabras con título tipo “3 errores que evitas si sabes cómo funciona el SII”.

Si quieres, el siguiente paso puede ser bajar 3–5 ideas a guiones concretos (copys listos para pegar) o a esquemas de carrusel (títulos por slide).
