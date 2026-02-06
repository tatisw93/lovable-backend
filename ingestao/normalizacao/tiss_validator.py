"""
Validador de estrutura TISS (Troca de Informações em Saúde Suplementar).
Verifica campos obrigatórios, regras de preenchimento e consistência
conforme o Padrão TISS da ANS.
"""
from dominio.constantes import (
    TipoGuiaTISS,
    CAMPOS_OBRIGATORIOS_TISS,
    PRAZO_APRESENTACAO_GUIA_DIAS,
)
from datetime import datetime, date


class TissValidator:
    """Validador de estrutura e conformidade TISS."""

    def validar_guia(self, guia: dict) -> list[dict]:
        """
        Valida uma guia TISS conforme regras do padrão.

        Returns:
            Lista de erros encontrados, cada um com:
            - campo: nome do campo
            - regra: referência à regra TISS
            - mensagem: descrição do erro
            - severidade: alta/media/baixa
        """
        erros = []
        tipo_guia = guia.get("tipo_guia", "")

        # 1. Validar campos obrigatórios
        erros.extend(self._validar_campos_obrigatorios(guia, tipo_guia))

        # 2. Validar registro ANS
        erros.extend(self._validar_registro_ans(guia))

        # 3. Validar datas
        erros.extend(self._validar_datas(guia))

        # 4. Validar número da guia
        erros.extend(self._validar_numero_guia(guia))

        # 5. Validar CID quando obrigatório
        erros.extend(self._validar_cid_obrigatorio(guia, tipo_guia))

        return erros

    def _validar_campos_obrigatorios(
        self, guia: dict, tipo_guia: str
    ) -> list[dict]:
        """Verifica se todos os campos obrigatórios estão preenchidos."""
        erros = []

        # Mapear tipo_guia para enum
        tipo_enum = None
        for t in TipoGuiaTISS:
            if t.value == tipo_guia:
                tipo_enum = t
                break

        if tipo_enum and tipo_enum in CAMPOS_OBRIGATORIOS_TISS:
            campos_req = CAMPOS_OBRIGATORIOS_TISS[tipo_enum]
            campos_ausentes = []

            # Verificar campos no nível da guia
            # Mapear campos TISS para campos do nosso modelo
            mapeamento = {
                "registroANS": "registro_ans",
                "numeroGuiaPrestador": "numero_guia_prestador",
                "dadosBeneficiario": "beneficiario_id",
                "dadosSolicitante": "prestador_id",
                "dadosSolicitacao": "data_atendimento",
                "dadosExecutante": "prestador_id",
                "procedimentosRealizados": "procedimentos",
                "dadosContratado": "prestador_id",
                "dadosInternacao": "data_atendimento",
                "guiaSolicInternacao": "numero_autorizacao",
                "dadosSaidaInternacao": "data_fim_atendimento",
                "valorTotal": "valor_total_informado",
                "dadosContratadoExecutante": "prestador_id",
                "dadosAtendimento": "data_atendimento",
            }

            for campo_tiss in campos_req:
                campo_modelo = mapeamento.get(campo_tiss, campo_tiss)
                valor = guia.get(campo_modelo)
                if not valor:
                    campos_ausentes.append(campo_tiss)

            if campos_ausentes:
                erros.append(
                    {
                        "campo": ", ".join(campos_ausentes),
                        "regra": f"TISS 4.01 - Campos obrigatórios para {tipo_guia}",
                        "mensagem": (
                            f"Campos obrigatórios ausentes na guia {tipo_guia}: "
                            f"{', '.join(campos_ausentes)}. "
                            "Conforme padrão TISS, estes campos são de preenchimento obrigatório."
                        ),
                        "severidade": "alta",
                    }
                )

        return erros

    def _validar_registro_ans(self, guia: dict) -> list[dict]:
        """Valida o registro ANS da operadora."""
        erros = []
        reg = guia.get("registro_ans")

        if not reg:
            erros.append(
                {
                    "campo": "registroANS",
                    "regra": "TISS 4.01 - Registro ANS obrigatório",
                    "mensagem": "Registro ANS ausente. Campo obrigatório em todas as guias TISS.",
                    "severidade": "alta",
                }
            )
        elif not (str(reg).isdigit() and len(str(reg)) == 6):
            erros.append(
                {
                    "campo": "registroANS",
                    "regra": "TISS 4.01 - Formato do registro ANS",
                    "mensagem": (
                        f"Registro ANS '{reg}' inválido. "
                        "Deve conter exatamente 6 dígitos numéricos."
                    ),
                    "severidade": "alta",
                }
            )

        return erros

    def _validar_datas(self, guia: dict) -> list[dict]:
        """Valida datas da guia (consistência e prazo)."""
        erros = []
        data_atend = guia.get("data_atendimento")
        data_fim = guia.get("data_fim_atendimento")

        if data_atend and data_fim:
            try:
                dt_inicio = self._parse_data(data_atend)
                dt_fim = self._parse_data(data_fim)
                if dt_inicio and dt_fim and dt_fim < dt_inicio:
                    erros.append(
                        {
                            "campo": "datas",
                            "regra": "TISS 4.01 - Consistência de datas",
                            "mensagem": (
                                f"Data fim ({data_fim}) anterior à data início ({data_atend}). "
                                "Inconsistência cronológica."
                            ),
                            "severidade": "alta",
                        }
                    )
            except (ValueError, TypeError):
                pass

        # Verificar prazo de apresentação
        if data_atend:
            try:
                dt = self._parse_data(data_atend)
                if dt:
                    hoje = date.today()
                    dias = (hoje - dt).days
                    if dias > PRAZO_APRESENTACAO_GUIA_DIAS:
                        erros.append(
                            {
                                "campo": "data_atendimento",
                                "regra": (
                                    "RN 305/2012 ANS - Prazo de apresentação"
                                ),
                                "mensagem": (
                                    f"Guia com {dias} dias desde o atendimento. "
                                    f"Prazo padrão de apresentação é de "
                                    f"{PRAZO_APRESENTACAO_GUIA_DIAS} dias. "
                                    "Verificar regras contratuais específicas."
                                ),
                                "severidade": "media",
                            }
                        )
            except (ValueError, TypeError):
                pass

        return erros

    def _validar_numero_guia(self, guia: dict) -> list[dict]:
        """Valida formato do número da guia."""
        erros = []
        num = guia.get("numero_guia_prestador")

        if not num:
            erros.append(
                {
                    "campo": "numeroGuiaPrestador",
                    "regra": "TISS 4.01 - Número da guia do prestador",
                    "mensagem": "Número da guia do prestador ausente. Campo obrigatório.",
                    "severidade": "alta",
                }
            )

        return erros

    def _validar_cid_obrigatorio(
        self, guia: dict, tipo_guia: str
    ) -> list[dict]:
        """Verifica se CID está preenchido quando obrigatório."""
        erros = []
        tipos_cid_obrigatorio = [
            TipoGuiaTISS.SADT.value,
            TipoGuiaTISS.INTERNACAO.value,
            TipoGuiaTISS.HONORARIOS.value,
        ]

        if tipo_guia in tipos_cid_obrigatorio and not guia.get("cid_principal"):
            erros.append(
                {
                    "campo": "diagnosticoCID",
                    "regra": "TISS 4.01 - CID obrigatório para guias SADT/Internação",
                    "mensagem": (
                        f"CID principal ausente em guia {tipo_guia}. "
                        "O diagnóstico CID é obrigatório para este tipo de guia."
                    ),
                    "severidade": "alta",
                }
            )

        return erros

    @staticmethod
    def _parse_data(valor) -> date | None:
        """Parse de data em vários formatos."""
        if isinstance(valor, date):
            return valor
        if isinstance(valor, datetime):
            return valor.date()
        texto = str(valor).strip()
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(texto, fmt).date()
            except ValueError:
                continue
        return None
