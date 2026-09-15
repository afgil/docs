#!/usr/bin/env python3
"""
Compara el contrato de payload del backend con los schemas OpenAPI de la documentación.

El backend (pana-backend) publica en
``apps/documents/contracts/document_payload_contract.json`` las llaves que acepta
cada nivel del documento del batch:

    {"version": 1, "levels": {"transport_data": [...], "details": [...], ...}}

Este script verifica que los niveles documentados en OpenAPI tengan exactamente
esas llaves, en la especificación v1 (openapi-combined.json) y en la v2
(openapi-v2.json). Si hay campos que están en un lado y no en el otro, los lista
y termina con código 1.

Uso:
    python3 scripts/check_api_contract.py
    python3 scripts/check_api_contract.py ruta/al/document_payload_contract.json

La ruta por defecto es relativa a la raíz de este repositorio:
../pana-backend/apps/documents/contracts/document_payload_contract.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = (
    REPO_ROOT.parent
    / "pana-backend"
    / "apps"
    / "documents"
    / "contracts"
    / "document_payload_contract.json"
)
SPECS = {
    "v1": REPO_ROOT / "api-reference" / "openapi-combined.json",
    "v2": REPO_ROOT / "api-reference" / "openapi-v2.json",
}
# Nivel del contrato -> schema de OpenAPI que lo documenta.
LEVEL_SCHEMAS = {
    "transport_data": "TransportData",
    "details": "DetailItem",
    "export_data": "ExportData",
}


class ApiContractChecker:
    """Compara los niveles del contrato del backend con los schemas OpenAPI."""

    def __init__(self, contract_path, specs=SPECS, level_schemas=LEVEL_SCHEMAS):
        self.contract_path = Path(contract_path)
        self.specs = specs
        self.level_schemas = level_schemas

    def load_contract_levels(self):
        with open(self.contract_path, encoding="utf-8") as handle:
            contract = json.load(handle)
        return contract["levels"]

    def load_schema_fields(self, spec_path, schema_name):
        with open(spec_path, encoding="utf-8") as handle:
            spec = json.load(handle)
        schema = spec["components"]["schemas"][schema_name]
        return set(schema.get("properties", {}))

    def compare(self):
        """Devuelve una lista de diferencias: (versión, nivel, schema, faltan_en_openapi, faltan_en_contrato)."""
        levels = self.load_contract_levels()
        mismatches = []
        for version, spec_path in self.specs.items():
            for level, schema_name in self.level_schemas.items():
                contract_fields = set(levels[level])
                openapi_fields = self.load_schema_fields(spec_path, schema_name)
                missing_in_openapi = sorted(contract_fields - openapi_fields)
                missing_in_contract = sorted(openapi_fields - contract_fields)
                if missing_in_openapi or missing_in_contract:
                    mismatches.append(
                        (
                            version,
                            level,
                            schema_name,
                            missing_in_openapi,
                            missing_in_contract,
                        )
                    )
        return mismatches

    def run(self):
        print(f"Contrato: {self.contract_path}")
        if not self.contract_path.is_file():
            print("ERROR: no existe el contrato. Indica la ruta como argumento.")
            return 2
        mismatches = self.compare()
        if not mismatches:
            checked = ", ".join(
                f"{level}->{schema}" for level, schema in self.level_schemas.items()
            )
            print(f"OK: {checked} coinciden en {', '.join(self.specs)}.")
            return 0
        for version, level, schema_name, missing_in_openapi, missing_in_contract in mismatches:
            spec_name = self.specs[version].name
            print(f"\n[{version}] {spec_name}: {level} -> {schema_name}")
            if missing_in_openapi:
                print("  En el contrato del backend, faltan en OpenAPI:")
                for field in missing_in_openapi:
                    print(f"    - {field}")
            if missing_in_contract:
                print("  En OpenAPI, faltan en el contrato del backend:")
                for field in missing_in_contract:
                    print(f"    - {field}")
        print(f"\nERROR: {len(mismatches)} diferencia(s) entre el contrato y OpenAPI.")
        return 1

    @classmethod
    def main(cls, argv=None):
        parser = argparse.ArgumentParser(
            description="Compara el contrato de payload del backend con los schemas OpenAPI."
        )
        parser.add_argument(
            "contract",
            nargs="?",
            default=str(DEFAULT_CONTRACT),
            help="Ruta a document_payload_contract.json (por defecto: %(default)s)",
        )
        args = parser.parse_args(argv)
        return cls(args.contract).run()


if __name__ == "__main__":
    sys.exit(ApiContractChecker.main())
