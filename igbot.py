"""CLI do botIG. Ajuda e importação não carregam Selenium nem abrem navegador."""

from pathlib import Path
import argparse
import os
import sys


def parser():
    p = argparse.ArgumentParser(description="botIG: comentários visíveis em uma rede social fictícia local.")
    p.add_argument("--demo", action="store_true", help="iniciar a demonstração local no Firefox visível")
    p.add_argument("--hashtag", default="arte", help="hashtag a pesquisar (padrão: arte)")
    p.add_argument("--limite", type=int, default=3, help="máximo de publicações distintas tentadas (padrão: 3)")
    p.add_argument("--entrada", type=Path, default=Path(__file__).parent / "examples/publicacoes.json")
    p.add_argument("--saida", type=Path, default=Path("outputs/resultado.csv"), help="CSV novo; recusa sobrescrita")
    p.add_argument("--driver", help="caminho do geckodriver; também aceita BOTIG_DRIVER ou PATH")
    p.add_argument("--firefox", default=os.environ.get("BOTIG_FIREFOX"), help="caminho opcional do Firefox")
    p.add_argument("--porta", type=int, default=0, help="porta local; 0 escolhe uma livre")
    p.add_argument("--pausa", type=float, default=0.8, help="pausa visual entre as ações, em segundos")
    p.add_argument("--fechar-ao-final", action="store_true", help="fechar sem esperar Enter no terminal")
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if not args.demo:
        p.print_help()
        return 0
    if args.limite < 1 or not 0 <= args.porta <= 65535 or not 0 <= args.pausa <= 30:
        p.error("Use limite positivo, porta entre 0 e 65535 e pausa entre 0 e 30.")
    from rede_local import carregar_base, iniciar_rede, normalizar_hashtag
    from automacao_local import Resultados, criar_driver, executar, localizar_driver
    resultados = None
    driver = None
    try:
        hashtag = normalizar_hashtag(args.hashtag)
        base = carregar_base(args.entrada)
        if args.saida.resolve() == args.entrada.resolve():
            raise ValueError("Entrada e saída precisam ser arquivos diferentes.")
        if args.saida.exists():
            raise ValueError("O CSV de saída já existe. Escolha um nome novo.")
        caminho_driver = localizar_driver(args.driver)
        resultados = Resultados(args.saida)
        with iniciar_rede(base, args.porta) as servidor:
            print(f"Rede fictícia: {servidor.endereco}\nCSV: {args.saida}\nInterrompa pelo botão da página ou Ctrl+C.", flush=True)
            driver = criar_driver(caminho_driver, args.firefox)
            try:
                executar(driver, servidor, hashtag, args.limite, resultados, args.pausa)
                resultados.fechar()
                print(f"Resultados gravados em {args.saida}.", flush=True)
                if not args.fechar_ao_final and sys.stdin.isatty():
                    input("Explore a página. Pressione Enter para fechar o navegador e o servidor: ")
            finally:
                try:
                    driver.quit()
                finally:
                    driver = None
        return 0
    except (ValueError, OSError) as exc:
        print(f"Configuração: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Execução interrompida. O CSV preserva as linhas já gravadas.", file=sys.stderr)
        return 130
    except Exception:
        if resultados and not resultados.linhas:
            resultados.registrar("", args.hashtag, "", "Falha técnica", "Não foi possível iniciar o navegador local.")
        print("Falha técnica. Confira Firefox, geckodriver, ambiente gráfico e a porta local.", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                print("Não foi possível concluir o fechamento do navegador.", file=sys.stderr)
        if resultados is not None and not resultados.arquivo.closed:
            resultados.fechar()


if __name__ == "__main__":
    raise SystemExit(main())
