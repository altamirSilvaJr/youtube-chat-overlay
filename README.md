# YouTube Overlay

Projeto inicial para coletar mensagens de chat de uma live do YouTube, transmitir via rede local e renderizar um overlay para streaming.

## Estrutura do projeto

- `app/` - aplicação principal e configurações
- `modules/` - coleta do chat, rede e overlay
- `utils/` - schema e protocolo de mensagens
- `assets/` - temas e fontes

## Objetivo do MVP

- conectar à live do YouTube
- enviar mensagens por TCP em rede local
- receber e renderizar o overlay
- permitir uma configuração básica

## Como executar

```bash
python app/main.py
```

## Requisito: YouTube Data API

Para ler mensagens reais do chat ao vivo, é necessário ter uma chave da **YouTube Data API v3** no Google Cloud.

### Como obter a chave

1. Acesse o Google Cloud Console: https://console.cloud.google.com/
2. Crie ou selecione um projeto.
3. Vá em **APIs e serviços** > **Biblioteca**.
4. Pesquise por **YouTube Data API v3**.
5. Clique em **Ativar**.
6. Vá em **APIs e serviços** > **Credenciais**.
7. Clique em **Criar credenciais** > **Chave de API**.
8. Copie a chave gerada.
9. Recomenda-se restringir a chave para uso apenas com **YouTube Data API v3**.

### Configurar a chave no projeto

Crie ou edite o arquivo `.env` na raiz do projeto:

```env
YOUTUBE_API_KEY=sua_chave_aqui
```

Também é possível preencher a chave no campo **API Key** da interface. Por segurança, o app não salva a chave no JSON por padrão. Marque **Salvar API key no JSON** apenas se quiser persistir essa informação em `config/settings.json`.

## Modos de uso

### `demo`

Usa mensagens fictícias para testar o visual do overlay.

Use este modo para:

- ajustar cores, fonte, opacidade e quantidade de mensagens;
- posicionar o overlay na tela;
- validar a aparência antes de conectar ao YouTube.

Não precisa de API key.

### `same_pc`

Coleta o chat do YouTube e renderiza o overlay no mesmo computador.

Use este modo quando:

- o mesmo PC roda a live, o OBS e o overlay;
- você quer testar a integração real com uma live pública;
- não precisa transmitir mensagens pela rede local.

Campos importantes:

- **Live ID do YouTube**: pode ser o ID do vídeo ou o link da live.
- **API Key**: pode vir do `.env` ou do campo da interface.

### `stream`

Abre o servidor TCP no computador de transmissão e renderiza o overlay nele.

Use este modo no PC que roda o OBS/stream.

Objetivo:

- receber mensagens enviadas por outro computador na rede local;
- exibir o overlay no computador de stream;
- permitir captura da janela pelo OBS.

Campos importantes:

- **Host do servidor**: IP local do computador de stream. Em muitos casos, use `0.0.0.0` para escutar na rede.
- **Porta do servidor**: porta TCP, por padrão `9000`.

### `gamer`

Coleta o chat do YouTube no computador de jogo e envia as mensagens para o computador de stream via TCP.

Use este modo no PC gamer quando:

- o jogo roda em um computador;
- você não quer ficar olhando para outro monitor para ver o chat;
- o OBS/overlay roda em outro computador;
- ambos estão na mesma rede local.

Campos importantes:

- **Live ID do YouTube**: ID ou link da live.
- **API Key**: chave da YouTube Data API.
- **Host do stream**: IP local do computador que está em modo `stream`.
- **Porta do stream**: a mesma porta configurada no modo `stream`.

## Fluxos recomendados

### Um computador

1. Selecione `same_pc`.
2. Informe o link ou ID da live.
3. Configure a API key.
4. Clique em **Iniciar overlay**.
5. Capture a janela do overlay no OBS.

### Dois computadores

No computador de stream:

1. Selecione `stream`.
2. Configure host e porta.
3. Clique em **Iniciar overlay**.
4. Capture a janela do overlay no OBS.

No computador gamer:

1. Selecione `gamer`.
2. Informe o link ou ID da live.
3. Configure a API key.
4. Informe o IP e a porta do computador de stream.
5. Clique em **Iniciar overlay** para iniciar a coleta e envio das mensagens.

## Configurações salvas

As configurações da interface são salvas em:

```text
config/settings.json
```

Esse arquivo guarda preferências visuais, rede, modo de uso e posição do overlay. A API key só é salva se a opção **Salvar API key no JSON** estiver marcada.

## Observações

Este é um ponto de partida para o MVP, e a arquitetura pode ser expandida conforme o projeto evolui.
