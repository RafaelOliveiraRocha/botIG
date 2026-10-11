const etapa = document.querySelector('#etapa');
const contagem = document.querySelector('#contagem');
const interromper = document.querySelector('#interromper');

async function atualizarProgresso() {
  try {
    const resposta = await fetch('/estado');
    const estado = await resposta.json();
    etapa.textContent = estado.etapa;
    contagem.textContent = `${estado.confirmados} confirmados · ${estado.descartados} descartados · ${estado.falhas} falhas`;
    interromper.disabled = estado.interrompido || estado.finalizado;
  } catch {
    etapa.textContent = 'Servidor local encerrado';
    interromper.disabled = true;
    clearInterval(atualizacao);
  }
}
interromper.addEventListener('click', async () => {
  await fetch('/interromper', {method: 'POST'});
  etapa.textContent = 'Interrupção solicitada. Resultados obtidos serão preservados.';
  interromper.disabled = true;
});
const atualizacao = setInterval(atualizarProgresso, 600);
atualizarProgresso();

const formulario = document.querySelector('#form-comentario');
if (formulario) {
  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const campo = document.querySelector('#comentario');
    const retorno = document.querySelector('#retorno-comentario');
    const botao = formulario.querySelector('button');
    const texto = campo.value.trim();
    if (!texto) {
      retorno.textContent = 'Escreva um comentário antes de publicar.';
      campo.focus();
      return;
    }
    botao.disabled = true;
    retorno.textContent = 'Inserindo comentário local...';
    try {
      const resposta = await fetch(`/comentar/${formulario.dataset.postId}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({texto})
      });
      const dados = await resposta.json();
      if (!resposta.ok) throw new Error(dados.erro);
      const item = document.createElement('li');
      item.dataset.commentId = dados.id;
      const autor = document.createElement('strong');
      autor.textContent = dados.autor;
      const mensagem = document.createElement('p');
      mensagem.className = 'texto-comentario';
      mensagem.textContent = dados.texto;
      item.append(autor, mensagem);
      document.querySelector('#comentarios').append(item);
      campo.value = '';
      retorno.textContent = 'Comentário inserido nesta publicação fictícia.';
    } catch (erro) {
      retorno.textContent = erro.message === 'Failed to fetch' ? 'Falha de conexão com o servidor local.' : erro.message;
      retorno.dataset.falha = 'true';
    } finally {
      botao.disabled = false;
    }
  });
}
