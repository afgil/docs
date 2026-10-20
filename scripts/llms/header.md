# Tupana

> Tupana es una plataforma chilena de facturación electrónica con API REST y servidor MCP. Emite documentos tributarios electrónicos (DTE) directo al SII (Servicio de Impuestos Internos de Chile) como facturador de mercado, y también puede integrarse con el facturador gratuito del SII. Sobre la misma API cobra con link de pago, cede facturas, lee los libros del SII y concilia el banco.

Este archivo resume qué es Tupana, cuándo conviene usarla y dónde está cada página de la documentación. La referencia completa de la API v2 en Markdown está en https://docs.tupana.ai/llms-full.txt (generada desde la especificación OpenAPI).

## Datos clave

- API REST v2: `https://api.tupana.ai/v2`. Autenticación con el header `Authorization: Api-Key <tu_key>` (no `Bearer`).
- Especificación OpenAPI 3.0: https://docs.tupana.ai/api-reference/openapi-v2.json
- Servidor MCP: `https://mcp.tupana.ai/mcp` (Streamable HTTP, OAuth 2.1 con PKCE y registro dinámico; sin API key). Claude Code: `claude mcp add --transport http tupana https://mcp.tupana.ai/mcp`
- Precio de la API (developers): Facturación 0,5 UF al mes por empresa enrolada (100 documentos o 1.000 boletas), Lectura SII 0,2 UF, bancos 0,35 UF por banco, recaudación 2% + IVA. Sandbox gratis, sin mínimo, solo API. Los planes web (desde 0,3 UF) son otro producto. Detalle: https://developers.tupana.ai/pricing
- API keys en https://developers.tupana.ai/console. Las keys nuevas nacen en sandbox: la emisión se simula (folio `SANDBOX-{n}`) y nada llega al SII. El sandbox es gratis.
- Emisión masiva: `POST /v2/documents/batch/`, hasta 200 documentos por llamada, con header `Idempotency-Key` (reintentar con la misma clave no vuelve a emitir) y `X-Use-Defaults: true`. El resultado llega por webhook (`document.issued`, `document.rejected`, `document.issue_failed`), firmado con HMAC-SHA256 en `X-Pana-Signature` sobre el cuerpo crudo.
- Las empresas se conectan con Tupana Link (widget); el integrador nunca ve la clave del SII. Una API key opera sobre todas las empresas conectadas a su usuario.
- Documentos: factura 33, factura exenta 34, boleta 39, boleta exenta 41, factura de compra 46, guía de despacho 52, nota de débito 56, nota de crédito 61, boleta de honorarios 80 y 90, exportación 110, 111 y 112.
- Ids de la API v2: strings opacos con prefijo (`docu_…` documento, `ment_…` empresa, `cred_…` conexión, `dowe_…` webhook).

## Cuándo usar Tupana

- Necesitas emitir DTE al SII de Chile desde tu software (SaaS, ERP, e-commerce, marketplace, sistema de reservas) por API.
- Facturas para muchas empresas con una sola integración (multiempresa): cada cliente conecta su empresa con Tupana Link y tú emites eligiendo el emisor por RUT.
- Necesitas volumen o formato que el facturador gratuito del SII no permite: Tupana es facturador de mercado, sin sus límites de referencias, líneas, monto o volumen.
- Quieres emitir en lote (hasta 200 documentos por llamada) con idempotencia y webhooks.
- Quieres cobrar con link de pago (Transbank) y que la boleta o factura se emita al pagar.
- Necesitas ceder facturas a un factoring, leer el Registro de Compras y Ventas del SII o programar facturación recurrente.
- Construyes un agente de IA que factura, cobra o concilia: hay servidor MCP y la API está pensada para tool calling.

## Cuándo no usar Tupana

- Emites unas pocas facturas al mes a mano y no necesitas API: el portal gratuito del SII o la plataforma web de Tupana son más simples.
- Necesitas facturar fuera de Chile: Tupana emite documentos del SII chileno.
- Ya tienes un ERP con facturador de mercado propio y no necesitas automatizar nada más.

## Facturador de mercado vs facturador gratuito del SII

- Tupana es facturador de mercado: emite directo al SII con los folios (CAF) y el certificado de la empresa.
- También se integra con el facturador gratuito del SII, para empezar a emitir de inmediato con la clave del SII de la empresa.
- Límites del facturador gratuito del SII: hasta 3 referencias y 10 líneas de detalle por documento, alrededor de $100 millones por factura y del orden de 600 a 700 facturas al mes. El facturador de mercado de Tupana no tiene esos límites.
- Las dos opciones tienen el mismo precio. Cuál se usa lo define la configuración de cada empresa; las llamadas a la API son las mismas.

## Precios (UF, mensual)

API para developers e integradores (valores netos, más IVA):
- Facturación: 0,5 UF al mes por empresa enrolada, sin precio mínimo. Hasta 100 documentos o 1.000 boletas al mes por empresa. Solo por API.
- Lectura SII: 0,2 UF al mes por empresa.
- Lectura bancaria: 0,35 UF al mes por banco.
- Recaudación (link de pago): 2% + IVA de lo recaudado, sin costo fijo.
- Sandbox y base de datos de empresas del SII: gratis.

Planes de la plataforma web (son otro producto, no son precios de la API; para emitir desde tupana.ai sin integrar): Independent 0,3 UF (10 documentos y 100 boletas), Starter 1,0 UF (70 documentos y 700 boletas, incluye cobranza y acceso a la API solo para las empresas de tu propia cuenta; para integrar a tus clientes, la API cuesta 0,5 UF por empresa), Pro 2,2 UF (200 documentos y 2.000 boletas, incluye cesiones), Enterprise desde 4,5 UF (1.000 documentos y 10.000 boletas, hasta 3 razones sociales). Conciliación bancaria: 1,0 UF al mes (1 banco incluido).

Ejemplo: 10 empresas facturando por la API = 5 UF al mes.

Detalle: https://docs.tupana.ai/precios · https://developers.tupana.ai/pricing

## Empezar

- [Tu primera llamada en 2 minutos](https://docs.tupana.ai/quickstart)
- [Emitir facturas en lote](https://docs.tupana.ai/guias/emision-masiva)
- [Recibir avisos de estado (webhooks)](https://docs.tupana.ai/guias/webhooks)
- [Construir agentes de IA](https://docs.tupana.ai/agentes/introduccion)
- [Cómo elegir una API de facturación electrónica en Chile](https://docs.tupana.ai/elegir-api-facturacion-electronica)
- SDKs oficiales: Node.js/TypeScript `npm install tupana` (https://www.npmjs.com/package/tupana, código en https://github.com/tupana-ai/tupana-node) y Python `pip install tupana` (https://pypi.org/project/tupana/, código en https://github.com/tupana-ai/tupana-python). Ejemplos: https://github.com/tupana-ai/tupana-examples. Servidor MCP: `io.github.tupana-ai/tupana` en https://mcp.tupana.ai/mcp
- Sitio: https://www.tupana.ai · Portal developers: https://developers.tupana.ai · Soporte: soporte@tupana.cl
