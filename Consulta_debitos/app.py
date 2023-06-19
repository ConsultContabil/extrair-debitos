import pdfplumber
import re
from flask import Flask, render_template, request
from tabulate import tabulate
import locale

app = Flask(__name__)

def converter_pdf_para_texto(caminho_arquivo_pdf):
    texto = ""
    with pdfplumber.open(caminho_arquivo_pdf) as pdf:
        for page in pdf.pages:
            texto += page.extract_text()

    padrao_cnpj = r"CNPJ:\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})"
    resultado_cnpj = re.search(padrao_cnpj, texto)
    cnpj = resultado_cnpj.group(1) if resultado_cnpj else ""

    padrao_nome_empresa = r"CNPJ:\s+[\d\s.-]+-\s+(.*)"
    resultado_nome_empresa = re.search(padrao_nome_empresa, texto)
    nome_empresa = resultado_nome_empresa.group(1) if resultado_nome_empresa else ""
    # print(texto)
    return texto, nome_empresa, cnpj

def buscar_valores_debitos(texto_pdf):
    resultados = {}

    padrao_linha1 = r"(\d{4}-\d{2} - [A-Za-z.-]+)\s+\d{2}/\d{4}(?:\s+\d{2}/\d{2}/\d{4})?\s+[\d.,]+\s+([\d.,]+)\s+DEVEDOR"
    padrao_linha2 = r"(SIMPLES NAC\.)\s+\d{2}/\d{4}(?:\s+\d{2}/\d{2}/\d{4})?\s+[\d.,]+\s+([\d.,]+)\s+DEVEDOR"
    padrao_linha3 = r"(\d{4}-\d{2} - [A-Za-z.-]+)\s+\d{4}\s+\d{2}/\d{2}/\d{4}\s+[\d.,]+\s+([\d.,]+)\s+DEVEDOR"
    padrao_linha4 = r"\d{4}-\d{2} - ([\w\s/º.-]+)\s+\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+([\d.,]+)\s+([\d.,]+)\s+DEVEDOR"
    padrao_linha5 = r"\d{4}-\d{2} - ([A-Za-z.-]+)\s+(\d{1,2}(?:º|ª)\s+TRIM/\d{4}).*?([\d.,]+)\s+([\d.,]+)\s+DEVEDOR"

    matches1 = re.findall(padrao_linha1, texto_pdf, flags=re.IGNORECASE)
    matches2 = re.findall(padrao_linha2, texto_pdf, flags=re.IGNORECASE)
    matches3 = re.findall(padrao_linha3, texto_pdf, flags=re.IGNORECASE)
    matches4 = re.findall(padrao_linha4, texto_pdf, flags=re.IGNORECASE)
    matches5 = re.findall(padrao_linha5, texto_pdf, flags=re.IGNORECASE)

    for match in matches1:
        nome_debito = match[0].split(" - ", 1)[1].strip()
        saldo_devedor = float(match[1].replace(".", "").replace(",", "."))

        if nome_debito in resultados:
            resultados[nome_debito] += saldo_devedor
        else:
            resultados[nome_debito] = saldo_devedor

    for match in matches2:
        nome_debito = match[0].strip()
        saldo_devedor = float(match[1].replace(".", "").replace(",", "."))

        if nome_debito in resultados:
            resultados[nome_debito] += saldo_devedor
        else:
            resultados[nome_debito] = saldo_devedor

    for match in matches3:
        nome_debito = match[0].split(" - ", 1)[1].strip()
        saldo_devedor = float(match[1].replace(".", "").replace(",", "."))

        if nome_debito in resultados:
            resultados[nome_debito] += saldo_devedor
        else:
            resultados[nome_debito] = saldo_devedor

    for match in matches4:
        nome_debito = match[0].split(" - ", 0)[-1].strip()
        saldo_devedor = float(match[1].replace(".", "").replace(",", "."))

        if nome_debito in resultados:
            resultados[nome_debito] += saldo_devedor
        else:
            resultados[nome_debito] = saldo_devedor

    for match in matches5:
        nome_debito = match[0].strip()
        trimestre = match[0].split(" ")
        saldo_devedor = float(match[2].replace(".", "").replace(",", "."))

        if nome_debito in resultados:
            resultados[nome_debito] += saldo_devedor
        else:
            resultados[nome_debito] = saldo_devedor

    resultados = {nome: round(valor, 2) for nome, valor in resultados.items()}

    return resultados

@app.route("/", methods=["GET"])
def exibir_formulario():
    return render_template("index.html")

@app.route("/resultado", methods=["POST"])
def processar_formulario():
    arquivo_pdf = request.files["arquivo_pdf"]
    locale.setlocale(locale.LC_ALL, '')

    texto_pdf, nome_empresa, cnpj = converter_pdf_para_texto(arquivo_pdf)
    debitos = buscar_valores_debitos(texto_pdf)

    total_debitos = round(sum(debitos.values()), 2)
    total_debitos_formatado = locale.format_string("%.2f", total_debitos, grouping=True)

    tabela = []
    for nome, valor in debitos.items():
        valor_formatado = locale.format_string("%.2f", valor, grouping=True)
        tabela.append([nome, valor_formatado])

    resultado_table = tabulate(tabela, headers=["Nome do Débito", "Valor"], tablefmt="html")

    return render_template("resultado.html", tabela=resultado_table, nome_empresa=nome_empresa, cnpj=cnpj, total_debitos=total_debitos_formatado)

if __name__ == "__main__":
    app.run(debug=True)
