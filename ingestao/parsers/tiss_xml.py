"""
Parser especializado para arquivos XML no padrão TISS (ANS).
Suporta lotes de guias e guias individuais nos formatos:
- guiaSP_SADT
- guiaConsulta
- guiaHonorarios
- guiaInternacao
"""
import xml.etree.ElementTree as ET
from typing import Optional

from ingestao.parsers.base import BaseParser, ResultadoParsing
from dominio.constantes import TipoGuiaTISS, TISS_XML_NAMESPACE

NS = TISS_XML_NAMESPACE


class TissXmlParser(BaseParser):
    """Parser para XML TISS versões 3.x e 4.x."""

    def tipos_suportados(self) -> list[str]:
        return ["xml"]

    def parse(self, conteudo: bytes, nome_arquivo: str) -> ResultadoParsing:
        resultado = ResultadoParsing()
        resultado.tipo_documento = "xml_tiss"

        try:
            root = ET.fromstring(conteudo)
        except ET.ParseError as e:
            resultado.erros.append(f"Erro ao parsear XML: {str(e)}")
            return resultado

        # Detectar namespace dinamicamente
        ns = self._detectar_namespace(root)

        # Extrair cabeçalho do lote
        resultado.metadados = self._extrair_cabecalho(root, ns)

        # Processar cada tipo de guia
        for tipo_guia in TipoGuiaTISS:
            guias_encontradas = root.findall(f".//{tipo_guia.value}", ns) or []
            # Tentar com namespace ANS
            if not guias_encontradas and ns:
                tag_ns = f".//{{{ns.get('ans', '')}}}{tipo_guia.value}"
                guias_encontradas = root.findall(tag_ns) or []
                # Também buscar sem namespace
                if not guias_encontradas:
                    guias_encontradas = root.iter(tipo_guia.value)

            for elem_guia in guias_encontradas:
                guia_dict = self._extrair_guia(elem_guia, tipo_guia, ns)
                if guia_dict:
                    resultado.guias.append(guia_dict)

                    # Extrair procedimentos da guia
                    procs = self._extrair_procedimentos(elem_guia, ns)
                    for proc in procs:
                        proc["numero_guia_ref"] = guia_dict.get("numero_guia_prestador")
                    resultado.procedimentos.extend(procs)

                    # Extrair beneficiário
                    benef = self._extrair_beneficiario(elem_guia, ns)
                    if benef:
                        resultado.beneficiarios.append(benef)

                    # Extrair prestador
                    prest = self._extrair_prestador(elem_guia, ns)
                    if prest:
                        resultado.prestadores.append(prest)

        if not resultado.guias:
            resultado.avisos.append(
                "Nenhuma guia TISS identificada no XML. "
                "Verifique se o arquivo segue o padrão TISS da ANS."
            )

        return resultado

    def _detectar_namespace(self, root: ET.Element) -> dict:
        """Detecta o namespace usado no XML TISS."""
        tag = root.tag
        if "{" in tag:
            uri = tag.split("}")[0].strip("{")
            return {"ans": uri}
        return NS

    def _extrair_cabecalho(self, root: ET.Element, ns: dict) -> dict:
        """Extrai metadados do cabeçalho do lote TISS."""
        cab = {}
        # Buscar versão TISS
        for tag in ["versaoPadrao", "ans:versaoPadrao"]:
            elem = root.find(f".//{tag}", ns)
            if elem is not None and elem.text:
                cab["versao_tiss"] = elem.text
                break

        # Buscar registro ANS do cabeçalho
        for tag in ["registroANS", "ans:registroANS"]:
            elem = root.find(f".//{tag}", ns)
            if elem is not None and elem.text:
                cab["registro_ans"] = elem.text
                break

        # Número do lote
        for tag in ["numeroLote", "ans:numeroLote"]:
            elem = root.find(f".//{tag}", ns)
            if elem is not None and elem.text:
                cab["numero_lote"] = elem.text
                break

        return cab

    def _texto(self, elem: Optional[ET.Element]) -> Optional[str]:
        """Extrai texto de um elemento XML de forma segura."""
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    def _buscar_tag(
        self, parent: ET.Element, tags: list[str], ns: dict
    ) -> Optional[str]:
        """Busca um valor em múltiplas variações de tag (com/sem namespace)."""
        for tag in tags:
            elem = parent.find(f".//{tag}", ns)
            val = self._texto(elem)
            if val:
                return val
            # Sem namespace
            elem = parent.find(f".//{tag}")
            val = self._texto(elem)
            if val:
                return val
        return None

    def _extrair_guia(
        self, elem: ET.Element, tipo: TipoGuiaTISS, ns: dict
    ) -> Optional[dict]:
        """Extrai dados de uma guia individual."""
        guia = {
            "tipo_guia": tipo.value,
            "numero_guia_prestador": self._buscar_tag(
                elem, ["numeroGuiaPrestador"], ns
            ),
            "numero_guia_operadora": self._buscar_tag(
                elem, ["numeroGuiaOperadora"], ns
            ),
            "numero_autorizacao": self._buscar_tag(
                elem,
                ["numeroGuiaAutorizacao", "guiaSolicInternacao"],
                ns,
            ),
            "registro_ans": self._buscar_tag(elem, ["registroANS"], ns),
            "data_atendimento": self._buscar_tag(
                elem, ["dataAtendimento", "dataInicioFaturamento"], ns
            ),
            "data_fim_atendimento": self._buscar_tag(
                elem, ["dataFimFaturamento", "dataFimAtendimento"], ns
            ),
            "tipo_atendimento": self._buscar_tag(
                elem, ["tipoAtendimento"], ns
            ),
            "indicacao_acidente": self._buscar_tag(
                elem, ["indicacaoAcidente"], ns
            ),
            "carater_atendimento": self._buscar_tag(
                elem, ["caraterAtendimento"], ns
            ),
            "cid_principal": self._buscar_tag(
                elem,
                [
                    "diagnosticoCID",
                    "CID",
                    "codigoCID",
                ],
                ns,
            ),
            "valor_total_informado": self._buscar_tag(
                elem,
                [
                    "valorTotalGeral",
                    "valorTotal",
                    "valorTotalProcedimentos",
                ],
                ns,
            ),
        }
        return guia

    def _extrair_procedimentos(
        self, elem_guia: ET.Element, ns: dict
    ) -> list[dict]:
        """Extrai procedimentos de dentro de uma guia."""
        procedimentos = []
        tags_proc = [
            "procedimentoExecutado",
            "procedimentosRealizados",
            "identificacaoProcedimento",
        ]

        for tag in tags_proc:
            for proc_elem in elem_guia.iter(tag):
                proc = {
                    "codigo_tuss": self._buscar_tag(
                        proc_elem, ["codigoProcedimento", "codigo"], ns
                    ),
                    "descricao": self._buscar_tag(
                        proc_elem, ["descricaoProcedimento", "descricao"], ns
                    ),
                    "tabela_referencia": self._buscar_tag(
                        proc_elem, ["codigoTabela"], ns
                    ),
                    "quantidade_realizada": self._buscar_tag(
                        proc_elem, ["quantidadeExecutada", "quantidade"], ns
                    ),
                    "valor_unitario": self._buscar_tag(
                        proc_elem, ["valorUnitario"], ns
                    ),
                    "valor_total": self._buscar_tag(
                        proc_elem, ["valorTotal"], ns
                    ),
                    "data_realizacao": self._buscar_tag(
                        proc_elem, ["dataExecucao", "dataRealizacao"], ns
                    ),
                    "hora_inicio": self._buscar_tag(
                        proc_elem, ["horaInicial"], ns
                    ),
                    "hora_fim": self._buscar_tag(
                        proc_elem, ["horaFinal"], ns
                    ),
                    "via_acesso": self._buscar_tag(
                        proc_elem, ["viaAcesso"], ns
                    ),
                    "tecnica_utilizada": self._buscar_tag(
                        proc_elem, ["tecnicaUtilizada"], ns
                    ),
                    "grau_participacao": self._buscar_tag(
                        proc_elem, ["grauParticipacao"], ns
                    ),
                }

                # Profissional executante
                prof_nome = self._buscar_tag(
                    proc_elem, ["nomeProfissional"], ns
                )
                if prof_nome:
                    proc["profissional_nome"] = prof_nome
                    proc["profissional_conselho"] = self._buscar_tag(
                        proc_elem, ["siglaConselho", "conselhoProfissional"], ns
                    )
                    proc["profissional_numero"] = self._buscar_tag(
                        proc_elem, ["numeroConselhoProfissional"], ns
                    )
                    proc["profissional_uf"] = self._buscar_tag(
                        proc_elem, ["UF"], ns
                    )
                    proc["profissional_cbos"] = self._buscar_tag(
                        proc_elem, ["CBOS", "codigoCBOS"], ns
                    )

                if proc.get("codigo_tuss"):
                    procedimentos.append(proc)

        return procedimentos

    def _extrair_beneficiario(
        self, elem_guia: ET.Element, ns: dict
    ) -> Optional[dict]:
        """Extrai dados do beneficiário de uma guia."""
        benef_elem = None
        for tag in ["dadosBeneficiario", "identificacaoBeneficiario"]:
            benef_elem = elem_guia.find(f".//{tag}", ns) or elem_guia.find(
                f".//{tag}"
            )
            if benef_elem is not None:
                break

        if benef_elem is None:
            return None

        return {
            "numero_carteirinha": self._buscar_tag(
                benef_elem, ["numeroCarteira"], ns
            ),
            "nome": self._buscar_tag(
                benef_elem, ["nomeBeneficiario"], ns
            ),
            "cns": self._buscar_tag(
                benef_elem, ["numeroCNS"], ns
            ),
        }

    def _extrair_prestador(
        self, elem_guia: ET.Element, ns: dict
    ) -> Optional[dict]:
        """Extrai dados do prestador/contratado de uma guia."""
        prest_elem = None
        for tag in [
            "dadosContratado",
            "dadosContratadoExecutante",
            "dadosExecutante",
        ]:
            prest_elem = elem_guia.find(f".//{tag}", ns) or elem_guia.find(
                f".//{tag}"
            )
            if prest_elem is not None:
                break

        if prest_elem is None:
            return None

        return {
            "cnes": self._buscar_tag(prest_elem, ["CNES", "codigoCNES"], ns),
            "cnpj": self._buscar_tag(
                prest_elem, ["CNPJ", "cnpjContratado"], ns
            ),
            "razao_social": self._buscar_tag(
                prest_elem, ["nomeContratado", "razaoSocial"], ns
            ),
        }
