# YouTube Overlay

Projeto inicial para coletar mensagens de chat de uma live do YouTube, transmitir via rede local e renderizar um overlay para streaming.

## Estrutura do projeto

- `app/` - aplicaÃ§Ã£o principal e configuraÃ§Ãµes
- `modules/` - coleta do chat, rede e overlay
- `utils/` - schema e protocolo de mensagens
- `assets/` - temas e fontes

## Objetivo do MVP

- conectar Ã  live do YouTube
- enviar mensagens por TCP em rede local
- receber e renderizar o overlay
- permitir uma configuraÃ§Ã£o bÃ¡sica

## InstalaÃ§Ã£o

Para usar o app:

```bash
pip install -r requirements.txt
```

Para desenvolver e rodar testes:

```bash
pip install -r requirements-dev.txt
```

## Como executar

```bash
python app/main.py
```

## Requisito: YouTube Data API

Para ler mensagens reais do chat ao vivo, Ã© necessÃ¡rio ter uma chave da **YouTube Data API v3** no Google Cloud.

### Como obter a chave

1. Acesse o Google Cloud Console: https://console.cloud.google.com/
2. Crie ou selecione um projeto.
3. VÃ¡ em **APIs e serviÃ§os** > **Biblioteca**.
4. Pesquise por **YouTube Data API v3**.
5. Clique em **Ativar**.
6. VÃ¡ em **APIs e serviÃ§os** > **Credenciais**.
7. Clique em **Criar credenciais** > **Chave de API**.
8. Copie a chave gerada.
9. Recomenda-se restringir a chave para uso apenas com **YouTube Data API v3**.

### Configurar a chave no projeto

Crie ou edite o arquivo `.env` na raiz do projeto:

```env
YOUTUBE_API_KEY=sua_chave_aqui
```

TambÃ©m Ã© possÃ­vel preencher a chave no campo **API Key** da interface. Por seguranÃ§a, o app nÃ£o salva a chave no JSON por padrÃ£o. Marque **Salvar API key no JSON** apenas se quiser persistir essa informaÃ§Ã£o em `config/settings.json`.

## Modos de uso

### `demo` - Demo

Usa mensagens fictícias para testar o visual do overlay.

Use este modo para:

- ajustar cores, fonte, opacidade e quantidade de mensagens;
- posicionar o overlay na tela;
- validar a aparência antes de conectar ao YouTube.

Não precisa de API key.

### `local_overlay` - Coletar YouTube e mostrar neste PC

Coleta o chat do YouTube e renderiza o overlay no mesmo computador.

Use este modo quando:

- você quer ver o chat sobre o jogo no próprio PC gamer;
- o PC de stream vai capturar a tela/jogo desse computador;
- você quer rodar tudo em um único PC;
- não precisa enviar mensagens pela rede local.

Campos importantes:

- **Live ID do YouTube**: pode ser o ID do vídeo ou o link da live.
- **API Key**: pode vir do `.env` ou do campo da interface.

### `send_network` - Coletar YouTube e enviar pela rede

Coleta o chat do YouTube neste computador e envia as mensagens para outro PC via TCP.

Use este modo no computador que deve buscar o chat no YouTube, mas não necessariamente exibir o overlay localmente.

Campos importantes:

- **Live ID do YouTube**: ID ou link da live.
- **API Key**: chave da YouTube Data API.
- **Host de destino**: IP local do computador que está em `receive_network`.
- **Porta de destino**: a mesma porta configurada no receptor, por padrão `9000`.

### `receive_network` - Receber da rede e mostrar neste PC

Abre um servidor TCP neste computador, recebe mensagens de outro PC e renderiza o overlay localmente.

Use este modo quando:

- este PC deve apenas exibir o overlay;
- outro computador será responsável por coletar o chat do YouTube;
- você quer mostrar o chat sobre o jogo em uma máquina que não tem API key.

Campos importantes:

- **Host para escutar**: IP local deste computador. Em muitos casos, use `0.0.0.0` para escutar na rede.
- **Porta para escutar**: porta TCP, por padrão `9000`.

## Fluxos recomendados

### Overlay sobre o jogo no PC gamer

No PC gamer:

1. Selecione `local_overlay`.
2. Informe o link ou ID da live.
3. Configure a API key.
4. Clique em **Iniciar overlay**.

Esse é o fluxo mais simples quando o objetivo é o jogador ver o chat sem olhar para outro monitor.

### PC de stream coleta, PC gamer exibe

No PC gamer:

1. Selecione `receive_network`.
2. Configure **Host para escutar** e **Porta para escutar**.
3. Clique em **Iniciar overlay**.

No PC de stream:

1. Selecione `send_network`.
2. Informe o link ou ID da live.
3. Configure a API key.
4. Informe o IP e a porta do PC gamer.
5. Clique em **Iniciar overlay**.

Nesse fluxo, a API key fica no PC de stream e o PC gamer apenas recebe e mostra o overlay.

### PC gamer coleta, PC de stream exibe

No PC de stream:

1. Selecione `receive_network`.
2. Configure host e porta.
3. Clique em **Iniciar overlay**.

No PC gamer:

1. Selecione `send_network`.
2. Informe o link ou ID da live.
3. Configure a API key.
4. Informe o IP e a porta do PC de stream.
5. Clique em **Iniciar overlay**.

Esse fluxo valida o envio por rede local no sentido oposto.

## ConfiguraÃ§Ãµes salvas

As configuraÃ§Ãµes da interface sÃ£o salvas em:

```text
config/settings.json
```

Esse arquivo guarda preferÃªncias visuais, rede, modo de uso e posiÃ§Ã£o do overlay. A API key sÃ³ Ã© salva se a opÃ§Ã£o **Salvar API key no JSON** estiver marcada.

## ObservaÃ§Ãµes

Este Ã© um ponto de partida para o MVP, e a arquitetura pode ser expandida conforme o projeto evolui.
