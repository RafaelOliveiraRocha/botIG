"""Interações Selenium restritas à rede fictícia; imports externos sob demanda."""

from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
import csv
import os
import re
import shutil

COLUNAS = ["publicacao", "hashtag", "comentario", "estado", "motivo", "origem", "id_comentario"]
TEXTOS = ["Que combinação bonita de formas e cores!", "Adorei os detalhes desta criação!",
          "Uma ideia muito criativa. Obrigado por compartilhar!"]


class Interrompida(Exception):
    pass


def destino_seguro(endereco, href, ids):
    """Nenhuma navegação aceita outro servidor, query, fragmento ou caminho."""
    if not isinstance(href, str) or not href:
        raise ValueError("Link ausente.")
    url = urlsplit(urljoin(endereco + "/", href))
    origem = urlsplit(endereco)
    if url.scheme != "http" or url.netloc != origem.netloc or url.username or url.password:
        raise ValueError("Link fora do servidor local.")
    if url.query or url.fragment or not url.path.startswith("/p/") or url.path[3:] not in ids:
        raise ValueError("Link fora dos caminhos de publicação.")
    return url.geturl(), url.path[3:]


def conferir_pagina(driver, endereco, caminho, query=None):
    atual = urlsplit(driver.current_url)
    if (atual.scheme != "http" or atual.netloc != urlsplit(endereco).netloc or
            atual.path != caminho or atual.fragment or atual.username or atual.password or
            parse_qs(atual.query) != (query or {})):
        raise ValueError("O navegador saiu do destino local esperado.")


def localizar_driver(configurado=None):
    candidato = configurado or os.environ.get("BOTIG_DRIVER") or shutil.which("geckodriver")
    if candidato:
        p = Path(candidato).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        raise ValueError("O geckodriver configurado não é um executável disponível.")
    # Reutiliza somente drivers já instalados; não inicia download automático.
    cache = Path.home() / ".cache" / "selenium" / "geckodriver"
    encontrados = list(cache.glob("**/geckodriver")) if cache.exists() else []
    def versao(p):
        return tuple(int(x) for x in re.findall(r"\d+", p.parent.name))
    for p in sorted(encontrados, key=versao, reverse=True):
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    raise ValueError("Instale geckodriver no PATH ou informe --driver. Nenhum navegador foi iniciado.")


def criar_driver(caminho_driver, firefox=None):
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    opcoes = Options()
    if firefox:
        opcoes.binary_location = firefox
    preferencias = {
        "network.proxy.type": 1, "network.proxy.http": "127.0.0.1", "network.proxy.http_port": 9,
        "network.proxy.ssl": "127.0.0.1", "network.proxy.ssl_port": 9,
        "network.proxy.no_proxies_on": "127.0.0.1,localhost",
        "network.proxy.failover_direct": False,
        "network.captive-portal-service.enabled": False, "network.connectivity-service.enabled": False,
        "browser.safebrowsing.downloads.enabled": False, "browser.safebrowsing.malware.enabled": False,
        "browser.safebrowsing.phishing.enabled": False, "extensions.update.enabled": False,
        "app.update.auto": False, "datareporting.healthreport.uploadEnabled": False,
        "toolkit.telemetry.enabled": False, "browser.newtabpage.enabled": False,
    }
    for chave, valor in preferencias.items():
        opcoes.set_preference(chave, valor)
    driver = webdriver.Firefox(service=Service(executable_path=caminho_driver, log_path=os.devnull), options=opcoes)
    try:
        driver.set_page_load_timeout(15)
        driver.set_window_size(1280, 900)
    except BaseException:
        driver.quit()
        raise
    return driver


class Resultados:
    def __init__(self, caminho):
        p = Path(caminho)
        if p.exists():
            raise ValueError("O CSV de saída já existe. Escolha um nome novo.")
        p.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo = p.open("x", encoding="utf-8", newline="")
        self.writer = csv.DictWriter(self.arquivo, fieldnames=COLUNAS)
        self.writer.writeheader()
        self.arquivo.flush()
        self.linhas = []

    def registrar(self, publicacao, hashtag, comentario, estado, motivo="", id_comentario=""):
        linha = dict(zip(COLUNAS, [publicacao, hashtag, comentario, estado, motivo, "ficticia", id_comentario]))
        self.writer.writerow(linha)
        self.arquivo.flush()
        self.linhas.append(linha)
        print(f"[{estado}] {publicacao or 'pesquisa'}" + (f" — {motivo}" if motivo else ""), flush=True)

    def fechar(self):
        self.arquivo.close()


def executar(driver, servidor, hashtag, limite, resultados, pausa=0.8):
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    rede = servidor.rede
    endereco = servidor.endereco
    contagens = {"confirmados": 0, "descartados": 0, "falhas": 0}
    def atualizar(etapa):
        rede.atualizar(etapa=etapa, **contagens)
        print(etapa, flush=True)
    def esperar():
        if rede.parar.wait(pausa):
            raise Interrompida()
    def novo_comentario(anteriores, texto):
        for item in driver.find_elements(By.CSS_SELECTOR, "#comentarios [data-comment-id]"):
            ident = item.get_attribute("data-comment-id")
            if ident not in anteriores and item.find_element(By.CSS_SELECTOR, ".texto-comentario").text == texto:
                return ident
        return None
    atualizar(f"Pesquisando #{hashtag}")
    try:
        driver.get(endereco + "/")
        conferir_pagina(driver, endereco, "/")
        campo = driver.find_element(By.ID, "hashtag")
        campo.clear()
        campo.send_keys(hashtag)
        driver.find_element(By.CSS_SELECTOR, '[data-testid="pesquisar"]').click()
        WebDriverWait(driver, 8).until(lambda d: urlsplit(d.current_url).query != "")
        conferir_pagina(driver, endereco, "/", {"hashtag": [hashtag]})
        links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, '[data-testid="publicacao"]')]
        if not links:
            resultados.registrar("", hashtag, "", "Sem resultados", "Nenhuma publicação para a hashtag.")
            return contagens
        vistos = set()
        tentativas = 0
        for href in links:
            if rede.parar.is_set() or tentativas >= limite:
                break
            try:
                destino, ident = destino_seguro(endereco, href, rede.posts)
            except ValueError as exc:
                resultados.registrar("", hashtag, "", "Descartado", str(exc))
                contagens["descartados"] += 1
                continue
            if ident in vistos:
                resultados.registrar(ident, hashtag, "", "Descartado", "Publicação repetida na seleção.")
                contagens["descartados"] += 1
                atualizar("Publicação repetida descartada")
                continue
            vistos.add(ident)
            tentativas += 1
            texto = TEXTOS[(tentativas - 1) % len(TEXTOS)]
            anteriores = set()
            enviado = False
            try:
                atualizar(f"Abrindo {ident} · {tentativas}/{limite}")
                driver.get(destino)
                conferir_pagina(driver, endereco, "/p/" + ident)
                anteriores = {e.get_attribute("data-comment-id") for e in driver.find_elements(By.CSS_SELECTOR, "#comentarios [data-comment-id]")}
                esperar()
                comentario = driver.find_element(By.ID, "comentario")
                comentario.send_keys(texto)
                atualizar(f"Comentário preenchido em {ident}")
                esperar()
                driver.find_element(By.CSS_SELECTOR, '[data-testid="comentar"]').click()
                enviado = True
                def confirmar(d):
                    conferir_pagina(d, endereco, "/p/" + ident)
                    confirmado = novo_comentario(anteriores, texto)
                    if confirmado:
                        return confirmado
                    if rede.parar.is_set():
                        raise Interrompida()
                    if d.find_element(By.ID, "retorno-comentario").get_attribute("data-falha") == "true":
                        raise RuntimeError("A interface local informou uma falha técnica.")
                    return False
                id_comentario = WebDriverWait(driver, 6, poll_frequency=0.2).until(confirmar)
                resultados.registrar(ident, hashtag, texto, "Confirmado", id_comentario=id_comentario)
                contagens["confirmados"] += 1
                atualizar(f"Comentário confirmado na página {ident}")
                esperar()
            except (Interrompida, KeyboardInterrupt):
                # Preserva também uma confirmação que tenha ocorrido junto da interrupção.
                if not any(r["publicacao"] == ident and r["estado"] == "Confirmado" for r in resultados.linhas):
                    try:
                        confirmado = novo_comentario(anteriores, texto) if enviado else None
                    except WebDriverException:
                        confirmado = None
                    resultados.registrar(ident, hashtag, texto, "Confirmado" if confirmado else "Interrompido",
                                         "" if confirmado else "Execução interrompida pelo usuário.", confirmado or "")
                    if confirmado:
                        contagens["confirmados"] += 1
                rede.parar.set()
                break
            except (TimeoutException, WebDriverException, ValueError, RuntimeError) as exc:
                if isinstance(exc, TimeoutException):
                    motivo = "Tempo de espera excedido na interação ou confirmação local."
                elif isinstance(exc, ValueError):
                    motivo = "Destino local inesperado; navegação interrompida."
                elif isinstance(exc, RuntimeError):
                    motivo = "A interface local informou uma falha técnica; comentário não confirmado."
                else:
                    motivo = "Falha técnica no navegador local."
                resultados.registrar(ident, hashtag, texto, "Falha técnica", motivo)
                contagens["falhas"] += 1
                atualizar(f"Falha técnica em {ident}; seguindo para a próxima publicação")
    except (Interrompida, KeyboardInterrupt):
        rede.parar.set()
    except (TimeoutException, WebDriverException, ValueError):
        resultados.registrar("", hashtag, "", "Falha técnica", "Não foi possível concluir a pesquisa local.")
        contagens["falhas"] += 1
    finally:
        etapa = "Execução interrompida · resultados preservados" if rede.parar.is_set() else "Execução concluída"
        rede.atualizar(etapa=etapa, finalizado=True, **contagens)
        print(etapa, flush=True)
    return contagens
