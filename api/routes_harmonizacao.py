"""
Rota legada de harmonização via Google Sheets.
Mantida para compatibilidade retroativa.
"""
import os
from flask import Blueprint, request, jsonify

bp_harmonizacao = Blueprint("harmonizacao", __name__)


def _carregar_google_sheets():
    """Carrega cliente Google Sheets (lazy, com tratamento de erro)."""
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Base Harmonização Arvo")

        if not os.path.exists(creds_file):
            return None

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        return client.open(sheet_name).sheet1
    except Exception:
        return None


@bp_harmonizacao.route("/harmonizacao", methods=["GET"])
def harmonizacao():
    """
    Busca de harmonização de códigos médicos (legado).
    Mantém compatibilidade com a API original.
    """
    termo = request.args.get("termo", "").lower()
    if not termo:
        return jsonify({"erro": "Parâmetro 'termo' é obrigatório."}), 400

    sheet = _carregar_google_sheets()
    if sheet is None:
        return jsonify(
            {
                "erro": "Serviço de harmonização indisponível. Verifique credentials.json.",
                "nota": "Use /api/v1/ingestao/upload para a nova API de auditoria.",
            }
        ), 503

    registros = sheet.get_all_records()
    resultados = []
    for registro in registros:
        if termo in str(registro.get("Código interno", "")).lower() or termo in str(
            registro.get("Descrição interna", "")
        ).lower():
            resultados.append(registro)

    return jsonify(resultados[:5])
