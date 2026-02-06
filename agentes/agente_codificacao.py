"""
Agente de Codificação.
Verifica a corretude da codificação de procedimentos, materiais
e medicamentos conforme tabelas TUSS, CID-10 e CBHPM.

Heurísticas:
- Código TUSS inválido ou inexistente
- CID-10 com formato incorreto
- Procedimento em tabela incorreta
- Código CBOS do profissional inválido
- Valor incompatível com porte CBHPM
"""
from agentes.base import AgenteBase
from models.guia_tiss import GuiaTISS
from models.procedimento import Procedimento
from dominio.constantes import NivelAchado, NivelConfianca, PORTES_CBHPM
from ingestao.normalizacao.tuss_validator import TussValidator, CODIGOS_ATENCAO
from ingestao.normalizacao.cid_validator import CidValidator


class AgenteCodificacao(AgenteBase):
    """Agente especializado em validação de codificação."""

    tipo = "codificacao"
    versao = "1.0.0"
    descricao = (
        "Valida a corretude da codificação TUSS, CID-10, CBHPM e "
        "identifica erros de codificação que causam glosa."
    )

    def __init__(self):
        self.tuss_validator = TussValidator()
        self.cid_validator = CidValidator()

    def analisar(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        procedimentos = guia.procedimentos.all()

        # 1. Validar códigos TUSS
        achados.extend(self._validar_tuss(guia, procedimentos))

        # 2. Validar CID da guia
        achados.extend(self._validar_cid(guia))

        # 3. Validar profissionais
        achados.extend(self._validar_profissionais(guia, procedimentos))

        # 4. Verificar tabela de referência
        achados.extend(self._validar_tabela_referencia(guia, procedimentos))

        # 5. Verificar porte CBHPM
        achados.extend(self._validar_porte_cbhpm(guia, procedimentos))

        return achados

    def _validar_tuss(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        achados = []

        for proc in procedimentos:
            if not proc.codigo_tuss:
                achados.append(
                    self._criar_achado(
                        titulo="Procedimento sem código TUSS",
                        descricao=(
                            f"Procedimento na guia {guia.numero_guia_prestador} "
                            "sem código TUSS. Obrigatório para faturamento."
                        ),
                        nivel=NivelAchado.TECNICO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.98,
                        regra_referencia="TISS 4.01 - codigoProcedimento",
                        norma_ans="RN 305/2012",
                        impacto_valor=float(proc.valor_total or 0),
                        impacto_tipo="glosa_total",
                        acao_recomendada="Incluir código TUSS válido.",
                        procedimento_id=proc.id,
                    )
                )
                continue

            validacao = self.tuss_validator.validar(proc.codigo_tuss)
            if not validacao["valido"]:
                achados.append(
                    self._criar_achado(
                        titulo=f"Código TUSS inválido: {proc.codigo_tuss}",
                        descricao=(
                            f"Procedimento {proc.codigo_tuss}: {validacao['mensagem']} "
                            "Código inválido resulta em glosa automática (MG004)."
                        ),
                        nivel=NivelAchado.TECNICO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.95,
                        regra_referencia="Tabela TUSS/Tabela 22 ANS",
                        norma_ans="RN 305/2012 - Tabela de procedimentos",
                        base_legal=(
                            "O código TUSS deve ser válido conforme a última "
                            "versão publicada pela ANS. Códigos inexistentes "
                            "são glosados por MG004."
                        ),
                        impacto_valor=float(proc.valor_total or 0),
                        impacto_tipo="glosa_codificacao",
                        acao_recomendada=(
                            f"Substituir código {proc.codigo_tuss} por código "
                            "TUSS válido e vigente."
                        ),
                        procedimento_id=proc.id,
                    )
                )

            # Verificar códigos que requerem atenção
            if proc.codigo_tuss in CODIGOS_ATENCAO:
                achados.append(
                    self._criar_achado(
                        titulo=f"Código TUSS de atenção: {proc.codigo_tuss}",
                        descricao=(
                            f"Procedimento {proc.codigo_tuss}: "
                            f"{CODIGOS_ATENCAO[proc.codigo_tuss]}."
                        ),
                        nivel=NivelAchado.ADMINISTRATIVO.value,
                        confianca=NivelConfianca.MEDIA.value,
                        confianca_score=0.65,
                        regra_referencia="Regras operacionais TUSS",
                        acao_recomendada=(
                            f"Verificar regras específicas para {proc.codigo_tuss}."
                        ),
                        procedimento_id=proc.id,
                    )
                )

        return achados

    def _validar_cid(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        cid = guia.cid_principal

        if not cid:
            return achados

        cid_norm = self.cid_validator.normalizar(cid)
        if not self.cid_validator.validar(cid_norm):
            achados.append(
                self._criar_achado(
                    titulo=f"CID-10 com formato inválido: {cid}",
                    descricao=(
                        f"CID '{cid}' não segue o formato CID-10 "
                        "(Letra + 2 dígitos + subcategoria opcional). "
                        "CID inválido pode resultar em glosa."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.90,
                    regra_referencia="CID-10 OMS / MS",
                    acao_recomendada="Corrigir código CID para formato válido.",
                    evidencia=f"CID informado: '{cid}', normalizado: '{cid_norm}'",
                )
            )

        return achados

    def _validar_profissionais(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        achados = []

        for proc in procedimentos:
            # Verificar se profissional está identificado
            if proc.valor_total and float(proc.valor_total) > 0:
                if not proc.profissional_conselho and not proc.profissional_numero:
                    achados.append(
                        self._criar_achado(
                            titulo="Profissional executante não identificado",
                            descricao=(
                                f"Procedimento {proc.codigo_tuss}: profissional "
                                "executante sem conselho/número de registro. "
                                "Pode resultar em glosa por MG016."
                            ),
                            nivel=NivelAchado.ADMINISTRATIVO.value,
                            confianca=NivelConfianca.MEDIA.value,
                            confianca_score=0.70,
                            regra_referencia="TISS 4.01 - Identificação do profissional",
                            base_legal=(
                                "O profissional executante deve ser identificado "
                                "com conselho de classe e número de registro."
                            ),
                            acao_recomendada=(
                                "Incluir conselho (CRM, COREN, etc.) e número "
                                "de registro do profissional executante."
                            ),
                            procedimento_id=proc.id,
                        )
                    )

        return achados

    def _validar_tabela_referencia(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        achados = []

        for proc in procedimentos:
            if proc.tabela_referencia and proc.tabela_referencia not in (
                "22",
                "00",
                "18",
                "19",
                "20",
            ):
                achados.append(
                    self._criar_achado(
                        titulo=f"Tabela de referência inválida: {proc.tabela_referencia}",
                        descricao=(
                            f"Procedimento {proc.codigo_tuss}: tabela de referência "
                            f"'{proc.tabela_referencia}' não é uma tabela TISS válida. "
                            "Tabelas válidas: 22 (TUSS), 00 (própria), "
                            "18 (diárias/taxas), 19 (materiais), 20 (medicamentos)."
                        ),
                        nivel=NivelAchado.TECNICO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.90,
                        regra_referencia="TISS 4.01 - codigoTabela",
                        acao_recomendada="Corrigir código de tabela de referência.",
                        procedimento_id=proc.id,
                    )
                )

        return achados

    def _validar_porte_cbhpm(
        self, guia: GuiaTISS, procedimentos: list[Procedimento]
    ) -> list[dict]:
        achados = []

        for proc in procedimentos:
            if not proc.porte_cbhpm or not proc.valor_unitario:
                continue

            if proc.porte_cbhpm in PORTES_CBHPM:
                info = PORTES_CBHPM[proc.porte_cbhpm]
                valor = float(proc.valor_unitario)

                if valor < info["valor_minimo"]:
                    diferenca = info["valor_minimo"] - valor
                    achados.append(
                        self._criar_achado(
                            titulo=f"Valor abaixo do mínimo CBHPM ({proc.porte_cbhpm})",
                            descricao=(
                                f"Procedimento {proc.codigo_tuss}: valor unitário "
                                f"R${valor:.2f} está abaixo do mínimo CBHPM para "
                                f"porte {proc.porte_cbhpm} (R${info['valor_minimo']:.2f}). "
                                f"Diferença: R${diferenca:.2f} por unidade."
                            ),
                            nivel=NivelAchado.ADMINISTRATIVO.value,
                            confianca=NivelConfianca.MEDIA.value,
                            confianca_score=0.70,
                            regra_referencia=f"CBHPM - {info['descricao']}",
                            base_legal=(
                                "A tabela CBHPM define valores mínimos de referência "
                                "para honorários médicos por porte de procedimento."
                            ),
                            impacto_valor=diferenca * (proc.quantidade_realizada or 1),
                            impacto_tipo="subfaturamento",
                            acao_recomendada=(
                                "Negociar reajuste contratual para adequação "
                                "ao piso CBHPM."
                            ),
                            procedimento_id=proc.id,
                        )
                    )

        return achados
