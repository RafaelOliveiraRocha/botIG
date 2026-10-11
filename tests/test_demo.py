import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from automacao_local import Resultados, destino_seguro
from rede_local import Rede, carregar_base, iniciar_rede, normalizar_hashtag

ROOT = Path(__file__).resolve().parents[1]
ENTRADA = ROOT / "examples/publicacoes.json"


class DemoTests(unittest.TestCase):
    def test_importacao_e_ajuda_sem_automacao(self):
        codigo = "import igbot, rede_local, automacao_local, sys; assert not any(n.startswith('selenium') for n in sys.modules); igbot.main(['--help'])"
        resultado = subprocess.run([sys.executable, "-c", codigo], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("--demo", resultado.stdout)

    def test_busca_e_repeticao_ficticia(self):
        rede = Rede(carregar_base(ENTRADA))
        self.assertEqual(normalizar_hashtag(" #ILUSTRAÇÃO "), "ilustracao")
        self.assertEqual([p["id"] for p in rede.selecionar("#ARTE")], ["P001", "P002", "P001", "P004", "P005"])
        self.assertEqual([p["id"] for p in rede.selecionar("ilustracao")], ["P002"])
        self.assertEqual(rede.selecionar("inexistente"), [])

    def test_validacao_dos_campos(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "entrada.json"
            base = json.loads(ENTRADA.read_text())
            del base["publicacoes"][0]["autor"]
            path.write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError, "autor"):
                carregar_base(path)
            with self.assertRaises(ValueError):
                normalizar_hashtag("../fora")

    def test_navegacao_restrita(self):
        endereco = "http://127.0.0.1:8123"
        self.assertEqual(destino_seguro(endereco, "/p/P001", {"P001"})[1], "P001")
        for href in [None, "", "https://rede.example.invalid/p/P001", "//rede.example.invalid/p/P001",
                     "http://127.0.0.1:9999/p/P001", "/p/P001?outra=1", "/p/P001#fora", "/p/P002", "/../requirements.txt"]:
            with self.subTest(href=href), self.assertRaises(ValueError):
                destino_seguro(endereco, href, {"P001"})

    def test_csv_incremental_e_sem_sobrescrita(self):
        antes = hashlib.sha256(ENTRADA.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resultado.csv"
            resultado = Resultados(path)
            with contextlib.redirect_stdout(io.StringIO()):
                resultado.registrar("P001", "arte", "Texto fictício", "Confirmado", id_comentario="demo-1")
            # A linha já está disponível mesmo antes do fechamento.
            with path.open(encoding="utf-8", newline="") as f:
                linhas = list(csv.DictReader(f))
            self.assertEqual(linhas[0]["id_comentario"], "demo-1")
            self.assertEqual(linhas[0]["origem"], "ficticia")
            resultado.fechar()
            with self.assertRaisesRegex(ValueError, "já existe"):
                Resultados(path)
        self.assertEqual(hashlib.sha256(ENTRADA.read_bytes()).hexdigest(), antes)

    def test_servidor_nao_expoe_arquivos_ou_origens_externas(self):
        with iniciar_rede(carregar_base(ENTRADA)) as servidor:
            with urlopen(servidor.endereco + "/", timeout=3) as r:
                self.assertEqual(r.status, 200)
            for path in ["/requirements.txt", "/../igbot.py", "/p/DESCONHECIDO"]:
                with self.assertRaises(HTTPError) as erro:
                    urlopen(servidor.endereco + path, timeout=3)
                self.assertEqual(erro.exception.code, 404)
            req = Request(servidor.endereco + "/interromper", method="POST",
                          headers={"Origin": "https://rede.example.invalid"})
            with self.assertRaises(HTTPError) as erro:
                urlopen(req, timeout=3)
            self.assertEqual(erro.exception.code, 403)
            self.assertFalse(servidor.rede.parar.is_set())


if __name__ == "__main__":
    unittest.main()
