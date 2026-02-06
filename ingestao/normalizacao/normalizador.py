"""
Normalizador central: coordena a normalização de todos os dados extraídos.
Aplica validações TUSS, CID, TISS e regras de negócio.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Any, Optional

from ingestao.parsers.base import ResultadoParsing
from ingestao.normalizacao.tuss_validator import TussValidator
from ingestao.normalizacao.cid_validator import CidValidator
from ingestao.normalizacao.tiss_validator import TissValidator


class ResultadoNormalizacao:
    """Resultado da normalização com dados limpos e alertas."""

    def __init__(self):
        self.dados_normalizados: dict[str, Any] = {}
        self.alertas: list[dict] = []
        self.erros_validacao: list[dict] = []
        self.estatisticas: dict[str, int] = {}

    def to_dict(self) -> dict:
        return {
            "dados": self.dados_normalizados,
            "alertas": self.alertas,
            "erros_validacao": self.erros_validacao,
            "estatisticas": self.estatisticas,
        }


class Normalizador:
    """
    Normaliza e valida dados extraídos pelos parsers.
    Etapas:
    1. Limpeza de campos (trim, formato, tipo)
    2. Validação de códigos (TUSS, CID)
    3. Validação de estrutura TISS
    4. Cálculos derivados (totais, inconsistências numéricas)
    """

    def __init__(self):
        self.tuss_validator = TussValidator()
        self.cid_validator = CidValidator()
        self.tiss_validator = TissValidator()

    def normalizar(self, resultado_parsing: ResultadoParsing) -> ResultadoNormalizacao:
        """Executa a normalização completa sobre os dados extraídos."""
        resultado = ResultadoNormalizacao()

        # 1. Normalizar guias
        guias_norm = []
        for guia in resultado_parsing.guias:
            guia_limpa = self._normalizar_guia(guia, resultado)
            guias_norm.append(guia_limpa)

        # 2. Normalizar procedimentos
        procs_norm = []
        for proc in resultado_parsing.procedimentos:
            proc_limpo = self._normalizar_procedimento(proc, resultado)
            procs_norm.append(proc_limpo)

        # 3. Normalizar glosas
        glosas_norm = []
        for glosa in resultado_parsing.glosas:
            glosa_limpa = self._normalizar_glosa(glosa, resultado)
            glosas_norm.append(glosa_limpa)

        # 4. Validar estrutura TISS das guias
        for guia in guias_norm:
            erros_tiss = self.tiss_validator.validar_guia(guia)
            for erro in erros_tiss:
                resultado.erros_validacao.append(
                    {
                        "tipo": "estrutura_tiss",
                        "guia": guia.get("numero_guia_prestador"),
                        **erro,
                    }
                )

        # 5. Validar consistência numérica
        self._validar_consistencia_numerica(procs_norm, guias_norm, resultado)

        resultado.dados_normalizados = {
            "guias": guias_norm,
            "procedimentos": procs_norm,
            "glosas": glosas_norm,
            "prestadores": resultado_parsing.prestadores,
            "operadoras": resultado_parsing.operadoras,
            "beneficiarios": resultado_parsing.beneficiarios,
            "metadados": resultado_parsing.metadados,
        }

        resultado.estatisticas = {
            "total_guias": len(guias_norm),
            "total_procedimentos": len(procs_norm),
            "total_glosas": len(glosas_norm),
            "total_alertas": len(resultado.alertas),
            "total_erros_validacao": len(resultado.erros_validacao),
        }

        return resultado

    def _normalizar_guia(self, guia: dict, resultado: ResultadoNormalizacao) -> dict:
        """Normaliza campos de uma guia TISS."""
        guia_norm = dict(guia)

        # Normalizar registro ANS (6 dígitos)
        reg_ans = guia_norm.get("registro_ans")
        if reg_ans:
            reg_ans = str(reg_ans).strip().zfill(6)
            if len(reg_ans) != 6 or not reg_ans.isdigit():
                resultado.alertas.append(
                    {
                        "tipo": "registro_ans_invalido",
                        "valor": reg_ans,
                        "guia": guia_norm.get("numero_guia_prestador"),
                        "mensagem": f"Registro ANS '{reg_ans}' não possui 6 dígitos numéricos.",
                    }
                )
            guia_norm["registro_ans"] = reg_ans

        # Normalizar datas
        for campo_data in ["data_atendimento", "data_fim_atendimento"]:
            guia_norm[campo_data] = self._normalizar_data(
                guia_norm.get(campo_data)
            )

        # Normalizar valores monetários
        for campo_valor in [
            "valor_total_informado",
            "valor_total_pago",
            "valor_total_glosado",
        ]:
            guia_norm[campo_valor] = self._normalizar_valor(
                guia_norm.get(campo_valor)
            )

        # Validar CID principal
        cid = guia_norm.get("cid_principal")
        if cid:
            cid_norm = self.cid_validator.normalizar(cid)
            if not self.cid_validator.validar(cid_norm):
                resultado.alertas.append(
                    {
                        "tipo": "cid_invalido",
                        "valor": cid,
                        "guia": guia_norm.get("numero_guia_prestador"),
                        "mensagem": f"Código CID '{cid}' não é válido conforme padrão CID-10.",
                    }
                )
            guia_norm["cid_principal"] = cid_norm

        return guia_norm

    def _normalizar_procedimento(
        self, proc: dict, resultado: ResultadoNormalizacao
    ) -> dict:
        """Normaliza campos de um procedimento."""
        proc_norm = dict(proc)

        # Normalizar código TUSS
        codigo = proc_norm.get("codigo_tuss")
        if codigo:
            codigo = str(codigo).strip()
            validacao = self.tuss_validator.validar(codigo)
            if not validacao["valido"]:
                resultado.alertas.append(
                    {
                        "tipo": "tuss_invalido",
                        "valor": codigo,
                        "mensagem": validacao["mensagem"],
                    }
                )
            proc_norm["codigo_tuss"] = codigo

        # Normalizar valores
        for campo in ["valor_unitario", "valor_total", "valor_pago", "valor_glosado"]:
            proc_norm[campo] = self._normalizar_valor(proc_norm.get(campo))

        # Normalizar quantidade
        proc_norm["quantidade_realizada"] = self._normalizar_inteiro(
            proc_norm.get("quantidade_realizada")
        )

        # Verificar consistência valor_unitario * quantidade = valor_total
        vl_unit = proc_norm.get("valor_unitario")
        qtd = proc_norm.get("quantidade_realizada")
        vl_total = proc_norm.get("valor_total")

        if vl_unit and qtd and vl_total:
            calculado = round(vl_unit * qtd, 2)
            if abs(calculado - vl_total) > 0.01:
                resultado.alertas.append(
                    {
                        "tipo": "inconsistencia_valor",
                        "codigo_tuss": proc_norm.get("codigo_tuss"),
                        "valor_unitario": float(vl_unit),
                        "quantidade": qtd,
                        "valor_total_informado": float(vl_total),
                        "valor_total_calculado": calculado,
                        "mensagem": (
                            f"Valor total informado (R${vl_total}) difere do calculado "
                            f"(R${calculado} = R${vl_unit} x {qtd})."
                        ),
                    }
                )

        # Normalizar data
        proc_norm["data_realizacao"] = self._normalizar_data(
            proc_norm.get("data_realizacao")
        )

        return proc_norm

    def _normalizar_glosa(
        self, glosa: dict, resultado: ResultadoNormalizacao
    ) -> dict:
        """Normaliza campos de uma glosa."""
        glosa_norm = dict(glosa)
        for campo in ["valor_glosado", "valor_original", "valor_recuperado"]:
            glosa_norm[campo] = self._normalizar_valor(glosa_norm.get(campo))
        return glosa_norm

    def _validar_consistencia_numerica(
        self,
        procedimentos: list[dict],
        guias: list[dict],
        resultado: ResultadoNormalizacao,
    ):
        """Valida totais entre procedimentos e guias."""
        # Agrupar procedimentos por guia
        totais_por_guia: dict[str, float] = {}
        for proc in procedimentos:
            ref = proc.get("numero_guia_ref")
            if ref and proc.get("valor_total"):
                totais_por_guia[ref] = totais_por_guia.get(ref, 0) + float(
                    proc["valor_total"]
                )

        for guia in guias:
            num = guia.get("numero_guia_prestador")
            vl_guia = guia.get("valor_total_informado")
            if num and vl_guia and num in totais_por_guia:
                soma_procs = round(totais_por_guia[num], 2)
                vl_guia_f = float(vl_guia)
                if abs(soma_procs - vl_guia_f) > 0.01:
                    resultado.alertas.append(
                        {
                            "tipo": "divergencia_total_guia",
                            "guia": num,
                            "valor_total_guia": vl_guia_f,
                            "soma_procedimentos": soma_procs,
                            "diferenca": round(abs(soma_procs - vl_guia_f), 2),
                            "mensagem": (
                                f"Soma dos procedimentos (R${soma_procs}) difere do "
                                f"valor total da guia (R${vl_guia_f})."
                            ),
                        }
                    )

    @staticmethod
    def _normalizar_valor(valor: Any) -> Optional[Decimal]:
        """Converte qualquer representação de valor monetário em Decimal."""
        if valor is None:
            return None
        try:
            if isinstance(valor, (int, float)):
                return Decimal(str(valor))
            texto = (
                str(valor)
                .replace("R$", "")
                .replace(" ", "")
                .strip()
            )
            # Formato brasileiro: 1.234,56
            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".")
            elif "," in texto:
                texto = texto.replace(",", ".")
            return Decimal(texto) if texto else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _normalizar_inteiro(valor: Any) -> Optional[int]:
        """Converte valor para inteiro."""
        if valor is None:
            return None
        try:
            return int(float(str(valor).strip()))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalizar_data(valor: Any) -> Optional[str]:
        """Normaliza data para formato ISO (YYYY-MM-DD)."""
        if valor is None:
            return None
        if isinstance(valor, (date, datetime)):
            return valor.isoformat()[:10]
        texto = str(valor).strip()
        # Tentar formato brasileiro DD/MM/YYYY
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y%m%d"]:
            try:
                return datetime.strptime(texto, fmt).date().isoformat()
            except ValueError:
                continue
        return texto  # Retorna como está se não conseguir parsear
