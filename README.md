# Mintlify Starter Kit

Click on `Use this template` to copy the Mintlify starter kit. The starter kit contains examples including

- Guide pages
- Navigation
- Customizations
- API Reference pages
- Use of popular components

### Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify) to preview the documentation changes locally. To install, use the following command

```
npm i -g mintlify
```

Run the following command at the root of your documentation (where docs.json is)

```
npm run dev
```

The `dev` script automatically combines all OpenAPI files before starting Mintlify. The OpenAPI combination happens automatically via the `predev` hook.

### Building for Production

To build the documentation for production:

```
npm run build
```

The `build` script automatically combines all OpenAPI files before building. The OpenAPI combination happens automatically via the `prebuild` hook.

### Publishing Changes

Install our Github App to auto propagate changes from your repo to your deployment. Changes will be deployed to production automatically after pushing to the default branch. Find the link to install on your dashboard.

The OpenAPI combination script runs automatically during the build process in production.

### Contrato de la API con el backend

`scripts/check_api_contract.py` compara `transport_data`, `details` y `export_data` de las especificaciones OpenAPI (`api-reference/openapi-combined.json` y `api-reference/openapi-v2.json`) con el contrato de payload del backend (`apps/documents/contracts/document_payload_contract.json` en `pana-backend`). Lista los campos que faltan en cada lado y termina con código 1 si no coinciden. Córrelo en cada PR que cambie el payload de la API:

```
python3 scripts/check_api_contract.py ../pana-backend/apps/documents/contracts/document_payload_contract.json
```

Sin argumento, usa `../pana-backend/...` relativo a la raíz de este repositorio.

#### Troubleshooting

- Mintlify dev isn't running - Run `mintlify install` it'll re-install dependencies.
- Page loads as a 404 - Make sure you are running in a folder with `docs.json`
- OpenAPI files not combining - Make sure Python 3 is installed and `scripts/combine_openapi.py` is executable