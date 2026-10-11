"""Rede fictícia em memória. Importar este módulo não inicia servidor."""

from contextlib import contextmanager
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Lock, Thread
from urllib.parse import parse_qs, urlsplit
import json
import re
import unicodedata

ASSETS = Path(__file__).parent / "assets"


def normalizar_hashtag(texto):
    if not isinstance(texto, str):
        raise ValueError("A hashtag deve ser um texto.")
    texto = texto.strip().lstrip("#")
    if not texto or not re.fullmatch(r"[\w]+", texto, re.UNICODE):
        raise ValueError("Use uma hashtag com letras, números ou sublinhado.")
    return "".join(c for c in unicodedata.normalize("NFKD", texto.casefold())
                   if not unicodedata.combining(c))


def carregar_base(caminho):
    try:
        base = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Não foi possível ler a base JSON.") from exc
    if not isinstance(base, dict) or base.get("origem") != "ficticia":
        raise ValueError("A base deve declarar origem ficticia.")
    posts = base.get("publicacoes")
    indice = base.get("indice")
    if not isinstance(posts, list) or not isinstance(indice, list):
        raise ValueError("A base precisa de publicacoes e indice em listas.")
    ids = set()
    for post in posts:
        if not isinstance(post, dict):
            raise ValueError("Cada publicação deve ser um objeto.")
        for campo in ("id", "autor", "legenda", "hashtags"):
            if campo not in post:
                raise ValueError(f"Campo obrigatório ausente: {campo}.")
        ident = post["id"]
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Z0-9_-]{1,32}", ident) or ident in ids:
            raise ValueError("IDs devem ser textos únicos com letras maiúsculas, números, _ ou -.")
        ids.add(ident)
        if any(not isinstance(post[c], str) or not post[c].strip() for c in ("autor", "legenda")):
            raise ValueError("Autor e legenda devem ser textos preenchidos.")
        if not isinstance(post["hashtags"], list) or not post["hashtags"]:
            raise ValueError("Cada publicação precisa de uma lista de hashtags.")
        for tag in post["hashtags"]:
            normalizar_hashtag(tag)
        if not isinstance(post.get("falha_confirmacao", False), bool):
            raise ValueError("falha_confirmacao deve ser booleano.")
        if not isinstance(post.get("comentarios", []), list) or any(
                not isinstance(c, str) or not c.strip() for c in post.get("comentarios", [])):
            raise ValueError("Comentários iniciais devem ser textos preenchidos.")
        if post.get("cor", "argila") not in {"argila", "lilas", "verde", "azul", "rosa", "areia"}:
            raise ValueError("Cor de publicação desconhecida.")
    if any(not isinstance(i, str) or i not in ids for i in indice):
        raise ValueError("O índice deve apontar somente para IDs existentes.")
    return base


class Rede:
    def __init__(self, base):
        self.posts = {p["id"]: p for p in base["publicacoes"]}
        self.indice = base["indice"]
        self.comentarios = {i: [{"id": f"inicial-{n}", "texto": t, "autor": "Leitor fictício"}
                               for n, t in enumerate(p.get("comentarios", []))]
                            for i, p in self.posts.items()}
        self.parar = Event()
        self.lock = Lock()
        self.contador = 0
        self.estado = {"etapa": "Aguardando a pesquisa", "confirmados": 0, "descartados": 0,
                       "falhas": 0, "finalizado": False}

    def atualizar(self, **valores):
        with self.lock:
            self.estado.update(valores)

    def selecionar(self, hashtag):
        tag = normalizar_hashtag(hashtag) if hashtag else None
        return [self.posts[i] for i in self.indice if tag is None or tag in
                [normalizar_hashtag(t) for t in self.posts[i]["hashtags"]]]


def figura(post, grande=False):
    return (f'<div class="ilustracao {escape(post.get("cor", "argila"))} {"grande" if grande else ""}" '
            'role="img" aria-label="Ilustração abstrata fictícia">'
            '<span class="forma circulo"></span><span class="forma arco"></span>'
            '<span class="forma bloco"></span><span class="selo">CRIAÇÃO FICTÍCIA</span></div>')


def pagina(conteudo, tag=""):
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rede de Papel | botIG</title><link rel="icon" href="data:,">
<link rel="stylesheet" href="/assets/rede.css"><script defer src="/assets/rede.js"></script></head>
<body><a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="cabecalho"><a class="marca" href="/"><span class="icone">#</span><span>Rede de Papel<small>Uma rede social fictícia</small></span></a>
<form action="/" method="get" class="busca" aria-label="Pesquisar por hashtag">
<label for="hashtag">Hashtag</label><div class="campo-busca"><span aria-hidden="true">#</span>
<input id="hashtag" name="hashtag" value="{escape(tag)}" required autocomplete="off" placeholder="arte">
<button type="submit" data-testid="pesquisar">Pesquisar</button></div></form>
<span class="etiqueta">LOCAL · DADOS FICTÍCIOS</span></header>
<main id="conteudo"><section class="progresso" aria-label="Progresso da automação">
<div><span class="ponto" aria-hidden="true"></span><strong id="etapa" aria-live="polite">Aguardando a pesquisa</strong>
<p id="contagem">0 confirmados · 0 descartados · 0 falhas</p></div>
<button id="interromper" type="button">Interromper execução</button></section>
{conteudo}</main><footer>botIG · Aprendendo automação com Python e Selenium<br>
Publicações e comentários fictícios. Tudo acontece neste servidor local.</footer></body></html>'''


def lista_html(rede, tag):
    posts = rede.selecionar(tag)
    titulo = f'Publicações em #{escape(tag)}' if tag else 'Pequenas ideias, novas conexões'
    cards = []
    vistos = set()
    for p in posts:
        ident = p["id"]
        repetida = ident in vistos
        vistos.add(ident)
        cards.append(f'''<article class="card"><a class="post-link" data-testid="publicacao" href="/p/{ident}">
{figura(p)}<div class="card-texto"><span class="autor">{escape(p['autor'])}</span>
<h2>{escape(p['legenda'])}</h2><p class="tags">{' '.join('#'+escape(t) for t in p['hashtags'])}</p>
<span class="abrir">Abrir publicação <span aria-hidden="true">↗</span></span>
{'<small class="repetida">Repetição para exercitar a deduplicação</small>' if repetida else ''}</div></a></article>''')
    aviso = (f'{len(vistos)} publicações distintas · {len(posts)} links na seleção' if posts
             else 'Nenhuma publicação para esta hashtag. Experimente #arte ou #natureza.')
    return pagina(f'<section class="introducao"><span class="sobretitulo">EXPERIMENTE O FLUXO</span>'
                  f'<h1>{titulo}</h1><p>{aviso}</p></section>'
                  f'<div class="grade" data-testid="resultados">{"".join(cards)}</div>', tag)


def post_html(rede, ident):
    post = rede.posts[ident]
    with rede.lock:
        comentarios = list(rede.comentarios[ident])
    itens = ''.join(f'<li data-comment-id="{c["id"]}"><strong>{escape(c["autor"])}</strong>'
                    f'<p class="texto-comentario">{escape(c["texto"])}</p></li>' for c in comentarios)
    falha = ('<p class="aviso">Cenário fictício: esta publicação demonstra uma falha técnica ao comentar.</p>'
             if post.get("falha_confirmacao") else '')
    return pagina(f'''<a class="voltar" href="/?hashtag={escape(post['hashtags'][0])}">← Voltar à pesquisa</a>
<article class="post" data-post-id="{ident}">{figura(post, True)}<div class="post-texto">
<span class="sobretitulo">PUBLICAÇÃO {ident}</span><h1>{escape(post['autor'])}</h1>
<p class="legenda">{escape(post['legenda'])}</p><p class="tags">{' '.join('#'+escape(t) for t in post['hashtags'])}</p>
<h2>Conversa</h2><ol id="comentarios" aria-live="polite">{itens}</ol>{falha}
<form id="form-comentario" data-post-id="{ident}"><label for="comentario">Seu comentário fictício</label>
<textarea id="comentario" required maxlength="500" rows="3" placeholder="Escreva sobre esta criação..."></textarea>
<button type="submit" data-testid="comentar">Publicar comentário local</button>
<p id="retorno-comentario" role="status"></p></form></div></article>''', post['hashtags'][0])


class Servidor(ThreadingHTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def responder(self, status, texto, tipo="text/html; charset=utf-8"):
        dados = texto.encode("utf-8") if isinstance(texto, str) else texto
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(dados)

    def permitido(self):
        return self.headers.get("Host") == self.server.endereco.split("//", 1)[1]

    def do_GET(self):
        if not self.permitido():
            self.responder(403, "Destino local inválido."); return
        url = urlsplit(self.path)
        rede = self.server.rede
        if url.path == "/":
            try:
                tag = parse_qs(url.query).get("hashtag", [""])[0]
                self.responder(200, lista_html(rede, normalizar_hashtag(tag) if tag else ""))
            except ValueError:
                self.responder(400, "Hashtag inválida.")
        elif url.path.startswith("/p/") and url.path[3:] in rede.posts and not url.query:
            self.responder(200, post_html(rede, url.path[3:]))
        elif url.path == "/estado" and not url.query:
            with rede.lock:
                estado = {**rede.estado, "interrompido": rede.parar.is_set()}
            self.responder(200, json.dumps(estado, ensure_ascii=False), "application/json; charset=utf-8")
        elif self.path in ("/assets/rede.css", "/assets/rede.js"):
            tipo = "text/css" if url.path.endswith(".css") else "application/javascript"
            self.responder(200, (ASSETS / url.path.rsplit("/", 1)[1]).read_bytes(), tipo+"; charset=utf-8")
        else:
            self.responder(404, "Página não encontrada nesta rede fictícia.")

    def do_POST(self):
        if not self.permitido() or self.headers.get("Origin", self.server.endereco) != self.server.endereco:
            self.responder(403, "Origem local inválida."); return
        rede = self.server.rede
        if self.path == "/interromper":
            rede.parar.set()
            self.responder(200, '{}', "application/json"); return
        ident = self.path.removeprefix("/comentar/")
        if not self.path.startswith("/comentar/") or ident not in rede.posts:
            self.responder(404, "Publicação desconhecida."); return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if not 0 < tamanho <= 4096:
                raise ValueError()
            texto = json.loads(self.rfile.read(tamanho))["texto"]
            if not isinstance(texto, str) or not texto.strip() or len(texto) > 500:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            self.responder(400, '{"erro":"Preencha um comentário de até 500 caracteres."}', "application/json"); return
        if rede.posts[ident].get("falha_confirmacao"):
            self.responder(503, '{"erro":"Falha técnica do cenário local. Comentário não inserido."}', "application/json"); return
        with rede.lock:
            rede.contador += 1
            c = {"id": f"demo-{rede.contador}", "autor": "Visitante fictício", "texto": texto.strip()}
            rede.comentarios[ident].append(c)
        self.responder(201, json.dumps(c, ensure_ascii=False), "application/json; charset=utf-8")


@contextmanager
def iniciar_rede(base, porta=0):
    servidor = Servidor(("127.0.0.1", porta), Handler)
    servidor.rede = Rede(base)
    servidor.endereco = f"http://127.0.0.1:{servidor.server_port}"
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield servidor
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join()
