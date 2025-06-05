
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open('Base Harmonização Arvo').sheet1

@app.route('/harmonizacao', methods=['GET'])
def harmonizacao():
    termo = request.args.get('termo', '').lower()
    registros = sheet.get_all_records()
    resultados = []
    for registro in registros:
        if termo in str(registro['Código interno']).lower() or termo in str(registro['Descrição interna']).lower():
            resultados.append(registro)
    return jsonify(resultados[:5])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
