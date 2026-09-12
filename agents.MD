# Objetivo
Este projeto visa criar um overlay do chat de lives do YouTube para que o streamer consiga acompanhar a conversa sem sair da tela principal do jogo ou da transmissão. A interface deve ser moderna, legível, agradável visualmente e compatível com softwares de streaming como OBS Studio.

Além disso, o sistema deve permitir que mensagens do chat sejam enviadas por conexão de rede, de modo que um computador utilizado para jogar possa enviar as mensagens para outro computador usado para stream, sem depender da tela do primeiro equipamento para visualização do chat.

# Visão geral do produto
O sistema será composto por:
- um módulo de coleta do chat da live do YouTube;
- um canal de comunicação em rede local entre computadores;
- um módulo de renderização do overlay para exibição em tela;
- uma interface de configuração para ajustes de live, rede, tema e layout.

# Escopo funcional
## 1. Coleta do chat do YouTube
- Obter mensagens da live em tempo real.
- Identificar remetente, texto, hora e metadados relevantes.
- Suportar o uso de autenticação e token de acesso conforme a API do YouTube.
- Filtrar mensagens duplicadas e inválidas.

## 2. Transmissão por rede local
- Enviar mensagens entre computadores na mesma rede.
- Usar comunicação TCP como padrão inicial.
- Suportar reconexão automática e reconciliação de falhas de rede.
- Encapsular mensagens em um protocolo simples com identificadores e timestamps.

## 3. Exibição do overlay
- Renderizar mensagens em uma janela leve e transparente.
- Permitir posicionamento e layout personalizados.
- Exibir texto em alto contraste para leitura em streaming.
- Suportar rolagem automática de mensagens.
- Permitir limite de mensagens visíveis e tempo de permanência.

## 4. Compatibilidade com streaming
- Funcionar como janela capturada em OBS Studio.
- Ser compatível com outros ambientes de transmissão que suportem browser source ou janela transparente.
- Permitir ajuste de tamanho, opacidade e posicionamento do overlay.

# Requisitos funcionais
1. O sistema deve conectar-se à live do YouTube e consumir o chat em tempo real.
2. O sistema deve enviar as mensagens de chat para outro computador via rede local.
3. O sistema deve receber as mensagens em um computador de stream e renderizar o overlay.
4. O sistema deve permitir configuração da live, IP do servidor, porta, tema e layout.
5. O sistema deve manter uma fila de mensagens e exibir as mais recentes em ordem de chegada.
6. O sistema deve tratar falhas de rede sem quebrar a execução da aplicação.
7. O sistema deve permitir ocultar, ajustar ou filtrar mensagens conforme configuração.

# Requisitos não funcionais
- Performance: latência aceitável para exibição em tempo real.
- Disponibilidade: a aplicação deve continuar operando mesmo com pequenas quedas de rede.
- Usabilidade: configuração simples, com poucos passos para iniciar a live.
- Portabilidade: o projeto deve funcionar em ambiente Windows por padrão.
- Manutenibilidade: estrutura modular para facilitar evolução e testes.

# Arquitetura proposta
## Fluxo principal
1. O módulo de coleta do YouTube faz a leitura do chat da live.
2. Os dados são convertidos para um formato padrão de mensagem.
3. A mensagem é enviada via socket TCP para o computador de exibição.
4. O computador receptor recebe a mensagem e a renderiza no overlay.
5. O overlay pode ser capturado pelo OBS e incluído na transmissão.

## Componentes
- Chat Collector: responsável pela conexão com a API do YouTube.
- Network Transport: responsável pela comunicação em rede local.
- Overlay Renderer: responsável pela UI do chat no formato de overlay.
- Config Manager: responsável por manter as configurações do usuário.
- Logger: responsável por registrar eventos, erros e diagnósticos.

# Especificação técnica inicial
## Tecnologia sugerida
- Linguagem principal: Python
- Interface gráfica: Tkinter, PyQt/PySide ou biblioteca leve para overlay
- Rede: socket TCP com JSON como formato de mensagem
- Comunicação: protocolo textual simples com timestamps e ids
- Persistência: arquivo de configuração em JSON ou INI

## Estrutura sugerida do projeto
- app/
  - main.py
  - config.py
  - logger.py
- modules/
  - youtube_chat.py
  - network_server.py
  - network_client.py
  - overlay.py
- utils/
  - message_schema.py
  - protocol.py
- assets/
  - themes/
  - fonts/

# Protocolo de mensagens
Cada mensagem enviada pela rede deve conter, no mínimo:
- id da mensagem
- timestamp
- nome do usuário
- texto da mensagem
- tipo de evento
- metadata opcional

Formato de exemplo:
{
  "message_id": "abc123",
  "timestamp": "2026-09-12T12:00:00Z",
  "author": "usuario1",
  "text": "Olá galera!",
  "event_type": "chat_message"
}

# Regras de UX e interface
- O overlay deve priorizar legibilidade em tela de transmissão.
- As mensagens mais recentes devem aparecer no topo ou no final da área de renderização.
- Uso de cores com contraste forte em fundo escuro.
- Campos como nome, texto e avatar devem manter consistência visual.
- Mensagens longas devem ser quebradas em múltiplas linhas ou truncadas com ellipsis.

# Critérios de aceitação
- O sistema consegue ler mensagens da live do YouTube em tempo real.
- O sistema consegue enviar as mensagens para outro computador pela rede local.
- O overlay aparece corretamente no OBS e mantém legibilidade.
- A aplicação lida com falhas simples de rede sem travar.
- O usuário consegue iniciar a live com pouca configuração inicial.

# Roadmap inicial
## Fase 1 - MVP
- Conexão com API do YouTube Live Chat
- Envio e recebimento de mensagens por TCP
- Renderização de overlay simples
- Configuração básica

## Fase 2 - Melhorias
- Theme system
- Filtragem por usuário ou palavra
- Melhorias visuais e animações
- Painel de controle avançado

## Fase 3 - Escala e robustez
- Logs de diagnóstico
- Persistência de histórico
- Suporte a múltiplas lives
- Otimização de desempenho e estabilidade

# Observações finais
Este documento deve servir como referência para a implementação inicial do projeto. Futuras evoluções podem adicionar melhorias de usabilidade, suporte a outras fontes de chat e refinamento visual do overlay, mas a base funcional deve seguir este escopo.
