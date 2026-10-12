import csv
import json
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "solicitacoes.json"
OUTPUT_FILE = BASE_DIR / "aprovados.csv"
LOG_FILE = BASE_DIR / "processamento.log"


def load_requests(input_path=INPUT_FILE):
    try:

        with open(input_path, "r", encoding="utf-8-sig") as file:
            requests = json.load(file)

        if not isinstance(requests, list):
            logging.error("Estrutura JSON inválida: era esperada uma lista.")
            return None

        return requests

    except FileNotFoundError:
        logging.error("Arquivo de entrada não encontrado.")
        return None

    except json.JSONDecodeError as error:
        logging.error(
            f"Formato JSON inválido (linha {error.lineno}, coluna {error.colno}): {error.msg}"
        )
        return None

    except UnicodeDecodeError:
        logging.error("Arquivo de entrada não está codificado em UTF-8.")
        return None

    except OSError as error:
        logging.error(f"Erro ao ler o arquivo de entrada: {error}")
        return None


def validate_request(request):
    if not isinstance(request, dict):
        return False, "O registro não é um objeto válido"

    required_fields = ["id", "nome", "cpf", "status"]

    for field in required_fields:
        if field not in request:
            return False, f"Campo obrigatório ausente: {field}"

    if request["status"] != "APROVADO":
        return False, "Status diferente de APROVADO"

    cpf = request["cpf"]

    if not isinstance(cpf, str) or not cpf.strip():
        return False, "CPF vazio ou inválido"

    name = request["nome"]

    if not isinstance(name, str) or not name.strip():
        return False, "Nome vazio ou inválido"

    record_id = request["id"]

    if isinstance(record_id, bool) or not isinstance(record_id, (int, str)):
        return False, "ID ausente ou inválido"

    if isinstance(record_id, str) and not record_id.strip():
        return False, "ID vazio"

    return True, None


def filter_approved_requests(requests):
    approved_requests = []

    for request in requests:
        is_valid, reason = validate_request(request)

        if is_valid:
            approved_requests.append(request)
        else:
            record_id = (
                request.get("id", "Desconhecido")
                if isinstance(request, dict)
                else "Desconhecido"
            )

            logging.warning(
                f"Solicitação ID {record_id} ignorada: {reason}"
            )

    return approved_requests


def export_to_csv(approved_requests, output_path=OUTPUT_FILE):
    try:
        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file, delimiter=";")

            writer.writerow(["id", "nome", "cpf"])

            for request in approved_requests:
                writer.writerow([
                    request["id"],
                    request["nome"],
                    request["cpf"]
                ])

        return True

    except (OSError, csv.Error) as error:
        logging.error(f"Erro ao gerar CSV: {error}")
        return False


def main(input_path=INPUT_FILE, output_path=OUTPUT_FILE, log_path=LOG_FILE):

    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
        filemode="w",
        force=True
    )

    logging.info("Processamento iniciado.")

    requests = load_requests(input_path)

    if requests is None:
        logging.error("Não foi possível concluir o processamento.")
        print("Não foi possível concluir o processamento. Consulte processamento.log.")
        return 1

    logging.info(f"Total de registros lidos: {len(requests)}")

    approved_requests = filter_approved_requests(requests)
    ignored_count = len(requests) - len(approved_requests)

    if not export_to_csv(approved_requests, output_path):
        logging.error("Falha durante a geração do CSV.")
        print("Não foi possível concluir o processamento. Consulte processamento.log.")
        return 1

    logging.info(f"Total de registros ignorados: {ignored_count}")
    logging.info(f"Total de registros exportados: {len(approved_requests)}")
    logging.info("Processamento concluído com sucesso.")
    print(
        f"Arquivo CSV gerado com sucesso! "
        f"Lidos: {len(requests)} | Exportados: {len(approved_requests)} | Ignorados: {ignored_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
