import csv
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import (
    export_to_csv,
    filter_approved_requests,
    load_requests,
    main,
    validate_request,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent


def make_request(**overrides):
    request = {
        "id": 1,
        "nome": "Maria Silva",
        "cpf": "12345678900",
        "status": "APROVADO",
    }
    request.update(overrides)
    return request


class TempDirTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self._close_log_handlers)

    @staticmethod
    def _close_log_handlers():
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)

    def write_json(self, content, name="solicitacoes.json"):
        path = self.tmp / name
        path.write_text(json.dumps(content), encoding="utf-8")
        return path


class TestRequestValidation(unittest.TestCase):

    def test_approved_request(self):
        valid, reason = validate_request(make_request())
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_pending_request(self):
        valid, reason = validate_request(make_request(status="PENDENTE"))
        self.assertFalse(valid)
        self.assertEqual(reason, "Status diferente de APROVADO")

    def test_status_is_case_sensitive(self):
        valid, _ = validate_request(make_request(status="aprovado"))
        self.assertFalse(valid)

    def test_empty_cpf(self):
        valid, reason = validate_request(make_request(cpf=""))
        self.assertFalse(valid)
        self.assertEqual(reason, "CPF vazio ou inválido")

    def test_null_cpf(self):
        valid, reason = validate_request(make_request(cpf=None))
        self.assertFalse(valid)
        self.assertEqual(reason, "CPF vazio ou inválido")

    def test_blank_cpf(self):
        valid, reason = validate_request(make_request(cpf="   "))
        self.assertFalse(valid)
        self.assertEqual(reason, "CPF vazio ou inválido")

    def test_non_string_cpf(self):
        valid, reason = validate_request(make_request(cpf=12345678900))
        self.assertFalse(valid)
        self.assertEqual(reason, "CPF vazio ou inválido")

    def test_empty_name(self):
        valid, reason = validate_request(make_request(nome=" "))
        self.assertFalse(valid)
        self.assertEqual(reason, "Nome vazio ou inválido")

    def test_invalid_id(self):
        for bad_id in (None, True, 1.5, [1]):
            with self.subTest(bad_id=bad_id):
                valid, reason = validate_request(make_request(id=bad_id))
                self.assertFalse(valid)
                self.assertEqual(reason, "ID ausente ou inválido")

    def test_blank_string_id(self):
        valid, reason = validate_request(make_request(id="  "))
        self.assertFalse(valid)
        self.assertEqual(reason, "ID vazio")

    def test_missing_each_required_field(self):
        for field in ("id", "nome", "cpf", "status"):
            with self.subTest(field=field):
                request = make_request()
                del request[field]
                valid, reason = validate_request(request)
                self.assertFalse(valid)
                self.assertEqual(reason, f"Campo obrigatório ausente: {field}")

    def test_multiple_errors_returns_first_reason(self):
        request = make_request(status="PENDENTE", cpf="", nome="")
        valid, reason = validate_request(request)
        self.assertFalse(valid)
        self.assertEqual(reason, "Status diferente de APROVADO")

    def test_record_that_is_not_an_object(self):
        for item in ("texto", None, 42, [1, 2]):
            with self.subTest(item=item):
                valid, reason = validate_request(item)
                self.assertFalse(valid)
                self.assertEqual(reason, "O registro não é um objeto válido")


class TestFilterApprovedRequests(unittest.TestCase):

    def test_keeps_only_valid_approved(self):
        requests = [
            make_request(id=1),
            make_request(id=2, status="PENDENTE"),
            make_request(id=3, cpf=""),
            "lixo",
            make_request(id=5),
        ]

        with self.assertLogs(level="WARNING") as captured:
            result = filter_approved_requests(requests)

        self.assertEqual([r["id"] for r in result], [1, 5])
        self.assertEqual(len(captured.records), 3)

    def test_invalid_records_do_not_interrupt_processing(self):
        requests = [
            make_request(id=1, cpf=""),
            make_request(id=2),
            make_request(id=3, status="PENDENTE"),
            make_request(id=4),
        ]
        with self.assertLogs(level="WARNING") as captured:
            result = filter_approved_requests(requests)
        self.assertEqual([record["id"] for record in result], [2, 4])
        self.assertEqual(len(captured.records), 2)

    def test_logs_reason_for_each_ignored_record(self):
        requests = [
            make_request(id=2, cpf=""),
            make_request(id=3, status="REPROVADO"),
        ]

        with self.assertLogs(level="WARNING") as captured:
            filter_approved_requests(requests)

        messages = [record.getMessage() for record in captured.records]
        self.assertIn("Solicitação ID 2 ignorada: CPF vazio ou inválido", messages)
        self.assertIn("Solicitação ID 3 ignorada: Status diferente de APROVADO", messages)


class TestLoadRequests(TempDirTestCase):

    def test_load_valid_file(self):
        path = self.write_json([make_request()])
        result = load_requests(path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["nome"], "Maria Silva")

    def test_file_not_found(self):
        with self.assertLogs(level="ERROR") as captured:
            result = load_requests(self.tmp / "nao_existe.json")

        self.assertIsNone(result)
        self.assertIn("Arquivo de entrada não encontrado.", captured.output[0])

    def test_invalid_json(self):
        path = self.tmp / "solicitacoes.json"
        path.write_text("{invalid json", encoding="utf-8")

        with self.assertLogs(level="ERROR") as captured:
            result = load_requests(path)

        self.assertIsNone(result)
        self.assertIn("Formato JSON inválido", captured.output[0])

    def test_json_root_is_not_a_list(self):
        path = self.write_json({"id": 1})

        with self.assertLogs(level="ERROR") as captured:
            result = load_requests(path)

        self.assertIsNone(result)
        self.assertIn("era esperada uma lista", captured.output[0])

    def test_file_with_bom_is_accepted(self):
        path = self.tmp / "solicitacoes.json"
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps([make_request()]).encode("utf-8"))

        result = load_requests(path)

        self.assertEqual(len(result), 1)

    def test_file_not_in_utf8(self):
        path = self.tmp / "solicitacoes.json"
        path.write_bytes('[{"nome": "João"}]'.encode("latin-1"))

        with self.assertLogs(level="ERROR") as captured:
            result = load_requests(path)

        self.assertIsNone(result)
        self.assertIn("não está codificado em UTF-8", captured.output[0])

    def test_read_error_is_logged(self):
        path = self.write_json([make_request()])

        with patch("main.open", side_effect=PermissionError("Access denied")):
            with self.assertLogs(level="ERROR") as captured:
                result = load_requests(path)

        self.assertIsNone(result)
        self.assertIn("Erro ao ler o arquivo de entrada", captured.output[0])


class TestExportToCsv(TempDirTestCase):

    def read_rows(self, path):
        with open(path, "r", encoding="utf-8", newline="") as file:
            return list(csv.reader(file, delimiter=";"))

    def test_export_to_csv(self):
        output = self.tmp / "aprovados.csv"

        success = export_to_csv([make_request()], output)

        self.assertTrue(success)
        rows = self.read_rows(output)
        self.assertEqual(rows[0], ["id", "nome", "cpf"])
        self.assertEqual(rows[1], ["1", "Maria Silva", "12345678900"])

    def test_export_empty_list_writes_only_header(self):
        output = self.tmp / "aprovados.csv"

        self.assertTrue(export_to_csv([], output))
        self.assertEqual(self.read_rows(output), [["id", "nome", "cpf"]])

    def test_name_with_separator_and_quotes_roundtrips(self):
        output = self.tmp / "aprovados.csv"
        tricky_name = 'Silva; "Júnior"'

        export_to_csv([make_request(nome=tricky_name)], output)

        self.assertEqual(self.read_rows(output)[1][1], tricky_name)

    def test_leading_zeros_in_cpf_are_preserved(self):
        output = self.tmp / "aprovados.csv"

        export_to_csv([make_request(cpf="00123456789")], output)

        self.assertEqual(self.read_rows(output)[1][2], "00123456789")

    def test_csv_write_error(self):
        with patch("main.open", side_effect=PermissionError("Access denied")):
            with self.assertLogs(level="ERROR") as captured:
                success = export_to_csv([make_request()], self.tmp / "aprovados.csv")

        self.assertFalse(success)
        self.assertIn("Erro ao gerar CSV", captured.output[0])


class TestMainEndToEnd(TempDirTestCase):

    def run_main(self, input_path):
        output = self.tmp / "aprovados.csv"
        log = self.tmp / "processamento.log"
        with patch("builtins.print"):
            code = main(input_path, output, log)
        self._close_log_handlers()
        return code, output, log

    def test_success_run_logs_all_totals(self):
        requests = [
            make_request(id=1, nome="Nome criado para o teste"),
            make_request(id=2, cpf=""),
            make_request(id=3, status="PENDENTE"),
        ]
        path = self.write_json(requests)

        code, output, log = self.run_main(path)
        log_text = log.read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertTrue(output.exists())

        expected_rows = [
            {"id": str(record["id"]), "nome": record["nome"], "cpf": record["cpf"]}
            for record in requests
            if record["status"] == "APROVADO"
            and isinstance(record["cpf"], str)
            and bool(record["cpf"].strip())
        ]
        with open(output, "r", encoding="utf-8", newline="") as file:
            actual_rows = list(csv.DictReader(file, delimiter=";"))
        self.assertEqual(actual_rows, expected_rows)

        for expected in (
            "Processamento iniciado.",
            "Total de registros lidos: 3",
            "Solicitação ID 2 ignorada: CPF vazio ou inválido",
            "Solicitação ID 3 ignorada: Status diferente de APROVADO",
            "Total de registros ignorados: 2",
            "Total de registros exportados: 1",
            "Processamento concluído com sucesso.",
        ):
            self.assertIn(expected, log_text)

    def test_missing_input_returns_error_and_creates_no_csv(self):
        code, output, log = self.run_main(self.tmp / "nao_existe.json")

        self.assertEqual(code, 1)
        self.assertFalse(output.exists())
        self.assertIn("Arquivo de entrada não encontrado.", log.read_text(encoding="utf-8"))

    def test_csv_failure_returns_error(self):
        path = self.write_json([make_request()])
        output = self.tmp / "aprovados.csv"
        output.mkdir()  
        log = self.tmp / "processamento.log"

        with patch("builtins.print"):
            code = main(path, output, log)
        self._close_log_handlers()

        self.assertEqual(code, 1)
        self.assertIn("Falha durante a geração do CSV.", log.read_text(encoding="utf-8"))

    def test_official_file_gives_15_read_7_exported_8_ignored(self):
        code, output, log = self.run_main(PROJECT_DIR / "solicitacoes.json")
        log_text = log.read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        with open(output, "r", encoding="utf-8", newline="") as file:
            rows = list(csv.reader(file, delimiter=";"))
        self.assertEqual([row[0] for row in rows[1:]], ["1", "4", "6", "9", "12", "13", "15"])

        with open(PROJECT_DIR / "solicitacoes.json", "r", encoding="utf-8-sig") as file:
            source_requests = json.load(file)
        expected_rows = [
            [str(record["id"]), record["nome"], record["cpf"]]
            for record in source_requests
            if isinstance(record, dict)
            and record.get("status") == "APROVADO"
            and isinstance(record.get("cpf"), str)
            and bool(record["cpf"].strip())
            and isinstance(record.get("nome"), str)
            and bool(record["nome"].strip())
            and isinstance(record.get("id"), (int, str))
            and not isinstance(record["id"], bool)
            and (not isinstance(record["id"], str) or bool(record["id"].strip()))
        ]
        self.assertEqual(rows[1:], expected_rows)
        self.assertIn("Total de registros lidos: 15", log_text)
        self.assertIn("Total de registros exportados: 7", log_text)
        self.assertIn("Total de registros ignorados: 8", log_text)


if __name__ == "__main__":
    unittest.main()
