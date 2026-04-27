# 🏗️ Alana Core Module

Este diretório contém a espinha dorsal do sistema, incluindo configurações globais e a ponte de comunicação com binários de alta performance.

## 🌉 Binary Bridge

A `BinaryBridge` é o componente que permite à Alana utilizar motores escritos em linguagens de baixo nível (como Go e Rust) de forma transparente através do Python.

- **Uso**: Os binários devem estar localizados na pasta `/bin` na raiz do projeto.
- **Protocolo**: A comunicação é feita via `STDIN` e `STDOUT` utilizando objetos JSON.

## ⚙️ Configurações & Log

O arquivo `config.py` centraliza todas as variáveis de ambiente e a configuração de logging.
- **Logs Rotativos**: O sistema mantém os últimos 5 logs de 10MB, garantindo que o espaço em disco seja preservado.
- **Verbosity**: Bibliotecas externas barulhentas são silenciadas por padrão para manter o foco nos eventos do Agente.

## 🧪 Estrutura
- `binary_bridge.py`: Orquestrador de processos externos.
- `config.py`: Gestor de ambiente e logs.
