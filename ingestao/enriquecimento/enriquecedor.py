"""
Enriquecedor de dados: adiciona informações derivadas e de contexto
aos dados normalizados.
"""
from dominio.constantes import PORTES_CBHPM, REGRAS_CID_PROCEDIMENTO


class Enriquecedor:
    """
    Enriquece dados normalizados com:
    - Classificação de grupo TUSS
    - Validação de compatibilidade CID x procedimento
    - Referência de porte CBHPM
    - Detecção de padrões de faturamento
    """

    def enriquecer(self, dados_normalizados: dict) -> dict:
        """Executa enriquecimento completo."""
        dados = dict(dados_normalizados)
        alertas_enriquecimento = []

        # Enriquecer procedimentos
        for proc in dados.get("procedimentos", []):
            self._enriquecer_procedimento(proc, dados, alertas_enriquecimento)

        # Enriquecer guias
        for guia in dados.get("guias", []):
            self._enriquecer_guia(guia, dados, alertas_enriquecimento)

        dados["alertas_enriquecimento"] = alertas_enriquecimento
        return dados

    def _enriquecer_procedimento(
        self, proc: dict, dados: dict, alertas: list
    ):
        """Enriquece um procedimento com dados derivados."""
        codigo = proc.get("codigo_tuss", "")

        # Adicionar porte CBHPM se disponível
        porte = proc.get("porte_cbhpm")
        if porte and porte in PORTES_CBHPM:
            info_porte = PORTES_CBHPM[porte]
            proc["porte_descricao"] = info_porte["descricao"]
            proc["valor_minimo_cbhpm"] = info_porte["valor_minimo"]

            # Verificar se valor está abaixo do mínimo CBHPM
            vl_unit = proc.get("valor_unitario")
            if vl_unit and float(vl_unit) < info_porte["valor_minimo"]:
                alertas.append(
                    {
                        "tipo": "valor_abaixo_cbhpm",
                        "codigo_tuss": codigo,
                        "valor_unitario": float(vl_unit),
                        "valor_minimo_cbhpm": info_porte["valor_minimo"],
                        "diferenca": round(
                            info_porte["valor_minimo"] - float(vl_unit), 2
                        ),
                        "mensagem": (
                            f"Valor unitário R${vl_unit} do procedimento {codigo} "
                            f"está abaixo do mínimo CBHPM ({info_porte['descricao']}: "
                            f"R${info_porte['valor_minimo']})."
                        ),
                    }
                )

        # Detectar procedimento sem descrição
        if not proc.get("descricao"):
            alertas.append(
                {
                    "tipo": "procedimento_sem_descricao",
                    "codigo_tuss": codigo,
                    "mensagem": f"Procedimento {codigo} sem descrição. Verificar base TUSS.",
                }
            )

    def _enriquecer_guia(self, guia: dict, dados: dict, alertas: list):
        """Enriquece uma guia com dados derivados."""
        cid = guia.get("cid_principal", "")

        if not cid:
            return

        # Verificar compatibilidade CID x procedimentos
        cid_base = cid.split(".")[0] if cid else ""
        if cid_base in REGRAS_CID_PROCEDIMENTO:
            regra = REGRAS_CID_PROCEDIMENTO[cid_base]
            prefixos_validos = regra.get("procedimentos_validos_prefixos", [])

            # Buscar procedimentos da guia
            num_guia = guia.get("numero_guia_prestador")
            procs_guia = [
                p
                for p in dados.get("procedimentos", [])
                if p.get("numero_guia_ref") == num_guia
            ]

            for proc in procs_guia:
                codigo = proc.get("codigo_tuss", "")
                if codigo and not any(
                    codigo.startswith(pref) for pref in prefixos_validos
                ):
                    alertas.append(
                        {
                            "tipo": "cid_procedimento_incompativel",
                            "cid": cid,
                            "codigo_tuss": codigo,
                            "guia": num_guia,
                            "mensagem": (
                                f"Procedimento {codigo} pode ser incompatível com "
                                f"CID {cid}. Prefixos esperados: {prefixos_validos}."
                            ),
                        }
                    )
