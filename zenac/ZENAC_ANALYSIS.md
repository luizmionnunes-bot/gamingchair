# ZenAC — registro de análise (log corrente)

> "guarde tudo que vc passar por cima" — este arquivo acumula tudo que eu analiso do
> ZenAC. Atualizado incrementalmente.

## Material
- `zenac/ZenAC_bytecode.bin` — bytecode bruto fornecido (285.254 bytes).
- `zenac/strings_raw.txt` — strings extraídas do bytecode (prefixadas por tamanho).

## 1. Formato do bytecode (recon inicial — 2026-10-15)
- Binário, não texto. Cabeçalho: `[9, 3, 221, 2, 0, 1, '=', '@', 'A', ...]` → byte 0 = **9**
  (versão de serialização; o `luau-compile` desta máquina gera byte 0 = 14).
- Tabela de **strings prefixadas por tamanho** logo no início (`\x04find`, `\x03sub`,
  `\x03gsub`), padrão de bytecode serializado tipo Luau.
- Formato compatível com VM Luau (v9) ou VM custom muito próxima.

## 2. Proteção de strings
- Contém um **decoder base64**: constante com o alfabeto
  `ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/`, o padrão de
  sanitização `[^ABC...+/=]` e `find`/`sub`/`gsub`.
- **377** strings extraídas; a esmagadora maioria são **blobs base64** (até ~136 chars)
  → as strings reais estão **base64-encodadas e provavelmente cifradas**, decodificadas
  em runtime. Em claro só aparecem utilitários como `getmetatable`, `getfenv`.
- Conclusão: ZenAC é mais fechado que o gamingchairac — a lógica e as strings estão no
  bytecode/ofuscação; extração estática crua rende pouco.

## 3. Próximo passo
- Obter **decompilação do bytecode → Lua** (usuário tem decompilador). Mesmo que volte
  ofuscado/flattened, é muito mais analisável que o bytecode cru, e o pipeline de
  desofuscação (Stages A–D + interpretador estático) já está pronto para limpá-lo e
  decodificar as strings base64/cifradas estaticamente.
- Alternativa sem decompilador: escrever um desmontador para este formato (v9) — mais
  trabalhoso e menos fiel; só se não houver decompilação.

## Achados (vão sendo anexados abaixo)
- (aguardando a decompilação / próximos passos)
