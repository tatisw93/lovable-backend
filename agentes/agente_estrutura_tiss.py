"""
Agente de Estrutura TISS.
Verifica conformidade estrutural das guias com o padrão TISS da ANS.

Heurísticas:
- Campos obrigatórios ausentes
- Formato de campos inválido
- Inconsistência entre campos correlacionados
- Versão TISS desatualizada
"""
from agentes.base import AgenteBase
from models.guia_tiss import GuiaTISS
from dominio.constantes import (
    TipoGuiaTISS,
    CAMPOS_OBRIGATORIOS_TISS,
    NivelAchado,
    NivelConfianca,
)


class AgenteEstruturaTISS(AgenteBase):
    """Agente especializado em validação estrutural TISS."""

    tipo = "estrutura_tiss"
    versao = "1.0.0"
    descricao = (
        "Valida a conformidade estrutural das guias TISS, "
        "verificando campos obrigatórios, formatos e consistência."
    )

    def analisar(self, guia: GuiaTISS) -> list[dict]:
        achados = []

        # 1. Verificar campos obrigatórios ausentes
        achados.extend(self._verificar_campos_obrigatorios(guia))

        # 2. Verificar formato do registro ANS
        achados.extend(self._verificar_registro_ans(guia))

        # 3. Verificar número da guia
        achados.extend(self._verificar_numero_guia(guia))

        # 4. Verificar CID obrigatório
        achados.extend(self._verificar_cid(guia))

        # 5. Verificar consistência de datas
        achados.extend(self._verificar_datas(guia))

        # 6. Verificar dados do beneficiário
        achados.extend(self._verificar_beneficiario(guia))

        # 7. Verificar procedimentos mínimos
        achados.extend(self._verificar_procedimentos(guia))

        return achados

    def _verificar_campos_obrigatorios(self, guia: GuiaTISS) -> list[dict]:
        """Verifica se a guia possui campos obrigatórios preenchidos."""
        achados = []
        campos_ausentes = guia.campos_ausentes or []

        if campos_ausentes:
            achados.append(
                self._criar_achado(
                    titulo="Campos obrigatórios TISS ausentes",
                    descricao=(
                        f"A guia {guia.numero_guia_prestador} ({guia.tipo_guia}) "
                        f"possui {len(campos_ausentes)} campo(s) obrigatório(s) ausente(s): "
                        f"{', '.join(campos_ausentes)}. "
                        "Guias com campos obrigatórios faltantes são automaticamente "
                        "glosadas pela maioria das operadoras."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.95,
                    regra_referencia=f"Padrão TISS 4.01 - Campos obrigatórios para {guia.tipo_guia}",
                    norma_ans="RN 305/2012 - Padrão obrigatório para troca de informações",
                    base_legal=(
                        "Conforme Padrão TISS (ANS), todos os campos marcados como "
                        "obrigatórios devem estar preenchidos para que a guia seja aceita "
                        "no processamento da operadora."
                    ),
                    impacto_valor=float(guia.valor_total_informado or 0),
                    impacto_tipo="glosa_total",
                    acao_recomendada=(
                        "Preencher os campos obrigatórios antes do envio: "
                        f"{', '.join(campos_ausentes)}."
                    ),
                    evidencia=f"Campos ausentes: {campos_ausentes}",
                )
            )

        return achados

    def _verificar_registro_ans(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        reg = guia.registro_ans

        if not reg:
            achados.append(
                self._criar_achado(
                    titulo="Registro ANS ausente",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: Registro ANS da operadora "
                        "não informado. Campo obrigatório em todas as guias TISS."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.98,
                    regra_referencia="TISS 4.01 - registroANS",
                    norma_ans="RN 305/2012",
                    base_legal=(
                        "O registro ANS identifica a operadora e é obrigatório "
                        "para processamento da guia."
                    ),
                    impacto_valor=float(guia.valor_total_informado or 0),
                    impacto_tipo="glosa_total",
                    acao_recomendada="Incluir o registro ANS da operadora (6 dígitos).",
                )
            )
        elif not (reg.isdigit() and len(reg) == 6):
            achados.append(
                self._criar_achado(
                    titulo="Registro ANS com formato inválido",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: Registro ANS '{reg}' "
                        "não possui o formato esperado de 6 dígitos numéricos."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.95,
                    regra_referencia="TISS 4.01 - Formato registroANS",
                    norma_ans="RN 305/2012",
                    acao_recomendada="Corrigir registro ANS para formato de 6 dígitos.",
                    evidencia=f"Valor atual: '{reg}'",
                )
            )

        return achados

    def _verificar_numero_guia(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        if not guia.numero_guia_prestador:
            achados.append(
                self._criar_achado(
                    titulo="Número da guia do prestador ausente",
                    descricao=(
                        "Guia sem número do prestador. Campo obrigatório para "
                        "rastreabilidade e processamento."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.98,
                    regra_referencia="TISS 4.01 - numeroGuiaPrestador",
                    norma_ans="RN 305/2012",
                    acao_recomendada="Informar número da guia do prestador.",
                )
            )
        return achados

    def _verificar_cid(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        tipos_cid_obrigatorio = [
            TipoGuiaTISS.SADT.value,
            TipoGuiaTISS.INTERNACAO.value,
            TipoGuiaTISS.HONORARIOS.value,
        ]

        if guia.tipo_guia in tipos_cid_obrigatorio and not guia.cid_principal:
            achados.append(
                self._criar_achado(
                    titulo="CID principal ausente em guia que exige diagnóstico",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador} ({guia.tipo_guia}): "
                        "CID principal não informado. O diagnóstico é obrigatório "
                        f"para guias do tipo {guia.tipo_guia}."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.95,
                    regra_referencia="TISS 4.01 - diagnosticoCID",
                    norma_ans="RN 305/2012",
                    base_legal=(
                        "O CID é obrigatório para guias SP/SADT, Honorários e Internação. "
                        "Sua ausência resulta em glosa por campos obrigatórios."
                    ),
                    acao_recomendada="Incluir CID-10 principal do diagnóstico.",
                )
            )
        return achados

    def _verificar_datas(self, guia: GuiaTISS) -> list[dict]:
        achados = []

        if not guia.data_atendimento:
            achados.append(
                self._criar_achado(
                    titulo="Data de atendimento ausente",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: Data de atendimento "
                        "não informada."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.95,
                    regra_referencia="TISS 4.01 - dataAtendimento",
                    acao_recomendada="Informar data de atendimento.",
                )
            )

        if guia.data_atendimento and guia.data_fim_atendimento:
            if guia.data_fim_atendimento < guia.data_atendimento:
                achados.append(
                    self._criar_achado(
                        titulo="Data fim anterior à data início",
                        descricao=(
                            f"Guia {guia.numero_guia_prestador}: Data de fim "
                            f"({guia.data_fim_atendimento}) é anterior à data de "
                            f"início ({guia.data_atendimento}). Inconsistência cronológica."
                        ),
                        nivel=NivelAchado.TECNICO.value,
                        confianca=NivelConfianca.ALTA.value,
                        confianca_score=0.99,
                        regra_referencia="TISS 4.01 - Consistência de datas",
                        acao_recomendada="Corrigir datas de atendimento.",
                        evidencia=(
                            f"Início: {guia.data_atendimento}, "
                            f"Fim: {guia.data_fim_atendimento}"
                        ),
                    )
                )

        return achados

    def _verificar_beneficiario(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        if not guia.beneficiario_id and not guia.dados_brutos.get(
            "beneficiario_carteirinha"
        ):
            achados.append(
                self._criar_achado(
                    titulo="Dados do beneficiário ausentes",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: Dados do beneficiário "
                        "não identificados. Obrigatório para todas as guias TISS."
                    ),
                    nivel=NivelAchado.ADMINISTRATIVO.value,
                    confianca=NivelConfianca.MEDIA.value,
                    confianca_score=0.70,
                    regra_referencia="TISS 4.01 - dadosBeneficiario",
                    acao_recomendada="Verificar e incluir dados do beneficiário.",
                )
            )
        return achados

    def _verificar_procedimentos(self, guia: GuiaTISS) -> list[dict]:
        achados = []
        total_procs = guia.procedimentos.count()

        if total_procs == 0:
            achados.append(
                self._criar_achado(
                    titulo="Guia sem procedimentos",
                    descricao=(
                        f"Guia {guia.numero_guia_prestador}: Nenhum procedimento "
                        "encontrado. Guias TISS devem conter ao menos um item faturável."
                    ),
                    nivel=NivelAchado.TECNICO.value,
                    confianca=NivelConfianca.ALTA.value,
                    confianca_score=0.95,
                    regra_referencia="TISS 4.01 - procedimentosRealizados",
                    impacto_valor=float(guia.valor_total_informado or 0),
                    impacto_tipo="glosa_total",
                    acao_recomendada="Incluir procedimentos realizados na guia.",
                )
            )

        return achados
