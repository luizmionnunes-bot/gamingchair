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

## Por que o bytecode está "assim" (explicação)
1. **Código compilado, não fonte.** Luau é compilado para bytecode (instruções da VM +
   tabela de constantes); o protetor entrega o bytecode, não o `.lua`. Daí o binário de
   alta entropia.
2. **Container serializado.** O trecho legível no início (`find`/`sub`/`gsub` + alfabeto
   base64) é a tabela de strings/constantes, prefixada por tamanho; depois vêm os protos
   (fluxo de instruções). Cabeçalho `9,3,…` ≠ `luau-compile` local (`14,3,…`) ⇒ versão/
   serialização alterada (build específico ou serializador customizado — comum para
   quebrar loaders/decompiladores padrão).
3. **Strings cifradas.** Não estão em claro: ficam base64+cifradas e são decodificadas em
   runtime por um decoder base64 embutido (alfabeto + `[^…+/=]` + find/sub/gsub). Por
   isso o dump cru só traz blobs base64 + utilitários (`getmetatable`,`getfenv`). Medida
   anti-análise.
4. **Motivo (anti-cheat client-side).** Se lógica/strings fossem legíveis, exploiters
   veriam todas as verificações e bypasses; então é enviado ofuscado/cifrado para elevar
   o custo de RE. Mesma filosofia do gamingchairac (que ainda usa VM própria + flattening).
Resumo: proteção em camadas (compilar → serializar com versão alterada → cifrar strings),
daí a leitura estática render pouco; precisamos decompilar para recuperar a lógica.

## ZenAC vs AGC (gamingchairac) — dificuldade (avaliação preliminar)
- ZenAC **começa mais fechado**: temos bytecode cru (AGC veio já decompilado); strings
  com base64+cifra "de verdade" (no AGC o decode cuspia bytecode); versão de serialização
  alterada (9 vs 14) atrapalha decompiladores.
- Mas o que travou o AGC foi o **VM aninhado (t[114]) + leitor t[30] = buraco do
  decompilador** → lógica instrução-a-instrução irrecuperável.
- **Decisivo:** se o ZenAC decompilar para Lua ofuscado SEM VM aninhado próprio →
  provavelmente dá pra recuperar 100% da lógica (⇒ no fim mais fácil que o AGC). Se tiver
  VM aninhado → comparável ou mais difícil.
- Veredito final depende da decompilação (presença ou não de VM aninhado).

## Achados (vão sendo anexados abaixo)
- (aguardando a decompilação / próximos passos)
