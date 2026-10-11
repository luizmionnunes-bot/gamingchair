# Resolução estática forçada — resultado

Tentativa de **forçar** a resolução estática das strings/valores que o Stage D havia
marcado como dependentes de runtime, executando o script num VM **Luau isolado**
(sem rede, ambiente stubado, só para extrair dados — nenhuma interação com jogo).

## Como
- `tools/make_runnable.py` — gera uma cópia *executável* (só p/ emulação): o Luau
  rejeita `continue` que pula sobre um `local` usado no `until` de um `repeat`, então
  faz hoisting desses `local` para fora do laço. (Não é o entregável.)
- `tools/mkharness.py` — monta o harness: roteia os decoders de stdlib (`gsub`, `char`,
  `concat`, `sub`) passados a `f1` por versões com hook (locais do chunk — a stdlib do
  Luau é readonly e não pode ser instrumentada), capturando toda string produzida.
- Execução: `luau harness.lua` (timeout curto).

## O que achamos
1. **Dupla ofuscação.** Sob o control-flow flattening (desfeito nos Stages A–C) há um
   **interpretador de bytecode (VM)**: `t[114]` executa as grandes tabelas de números
   como bytecode. A lógica e a maioria das strings reais são produzidas por essa VM em
   tempo de execução.
2. **Decodificação parcial funcionou.** Strings independentes de ambiente saíram
   (`__index`, `lshift`, `rshift`, além dos fragmentos base-85 do decode por `char`).
3. **Bloqueio: buracos do próprio decompilador.** A execução trava em
   `t2[138] = t2[138] + t[30](p1)` → `+ nil`, porque `t[30]` é um stub
   `"structuring failed for function 268"` que retorna `nil`. O lua.expert falhou em
   decompilar **16 funções** — 3, 96, 98, 100, 110, 128, 156, 160, 173, 186, 228, 234,
   250, 260, 264, 268 — deixando **10 handlers como stubs vazios**:
   `t[6, 22, 30, 75, 87, 102, 103, 108, 115, 116]`. A decodificação das strings
   restantes passa por essas funções ausentes.

## Conclusão
Não há "force" que resolva **código que não existe na saída do decompilador**. A
resolução estática completa exigiria uma decompilação mais limpa do bytecode original
(ou o fonte). Isto dá a **causa raiz concreta** da conclusão do Stage D e explica por
que `t[6]`/`t[30]`/`t[108]` (e os demais) permanecem stubs no entregável.
