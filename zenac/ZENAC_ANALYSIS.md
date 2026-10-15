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

## Dica: arquitetura Luraph VM (fornecida pelo usuário) — 2026-10-15
Usuário apontou a arquitetura do Luraph: prototypes em **Structure-of-Arrays (11 colunas)**,
`LPH_Deserialize` lendo de um `buffer` (`readu32/readf64/readi16/copy`), interpretador com
`PC = PC + 1` pós-incremento, e wrapper externo `return ({...}):t()(...)`.

Verificação contra os artefatos:
- **AGC (gamingchairac) BATE com essa arquitetura.** `t[114]` é o interpretador: 4164 linhas,
  loops `while true`, e leitura massiva de **arrays-coluna indexados por PC** — `X[1][i]` (82×),
  `X[76][i]` (32×), `X[54][i]`, `X[21][i]`, `X[93][i]`… Usa `buffer.create/len/readu8`. Ou seja,
  é um VM SoA estilo Luraph. O "buraco irrecuperável" `t[30]` (structuring failed func 268) é o
  **leitor de stream** (`buffer.readu8`/varint) ⇒ **reconstruível**, não perdido.
- **ZenAC:** `LPH` encontrado antes era **coincidência dentro de um blob base64** (NÃO marcador
  Luraph). `readf64/readi16/copy/buffer` não estão em claro (strings cifradas). ⇒ Luraph é
  hipótese forte mas **não confirmada estaticamente**; confirmar na decompilação procurando os
  fingerprints (wrapper `({...}):t()(...)`, SoA deserializer, aliases de reader, PC++).

## Plano de devirtualização (vale para AGC e, se confirmado, ZenAC)
1. Reconstruir o deserializer → prototypes SoA (11 colunas).
2. Mapear opcode virtual → handler (lendo os handlers do interpretador).
3. Lifting dos opcodes de volta para Lua legível = a lógica real.
AGC é o alvo concreto imediato (já tenho o bytecode decodificado t[19]=189KB + o VM t[114]).

## zenac_out.lua — decompilação recebida (do GitHub, main) — 2026-10-15
472 KB, 9738 linhas. É o **runtime da VM Luraph decompilado** (não a aplicação ainda).
Caracterização:
- **Flattening por `goto __siza_L##`** (labels `::__siza_LN::`). É **Lua 5.2+**, NÃO Luau
  ⇒ `luau-ast` dá **segfault/erro** (Luau não tem `goto`). Também há um **BOM U+FEFF** no
  início. ⇒ preciso de parser com `goto` (lua5.3/5.4 ou parser Lua em Python), não o luau.
- Topo: aliases de stdlib (`v0=type, v1=pairs, v2=bit32.bxor, v3=getmetatable`) + ~muitos
  `local vN=nil`.
- **Decryptor de números**: `v23(k,salt,slot)=upval1(k,A)-upval1(salt,B)` guardado em memo
  `upval0[slot]` (subtração de valores derivados — estilo dos geradores do AGC).
- **Strings cifradas**: literais byte-escaped (`"\239\191\189..."`, bytes U+FFFD = bytes
  cifrados manglados em UTF-8) passadas por um decryptor; e um **payload base64 gigante na
  linha 9664 (18.480 chars)** = o bytecode Luraph com a lógica real do ZenAC.
- 118 funções, 26 `while true`, 0 `for`, 372 referências `upval`. Sem `buffer`/`readu32`
  em claro ⇒ Luraph mais antigo (pré-buffer, reader via string) OU readers aliasados.

Conclusão: a **lógica do ZenAC está no payload** (linha 9664), interpretado por este
runtime. Para recuperá-la: desserializar o payload em protos SoA e liftar — conforme
`LURAPH_METHODOLOGY.md`.

## Tooling pendente
- Parser Lua com `goto` (instalar lua5.4, ou `luaparser`/`lupa` em Python) p/ análise de
  AST do `zenac_out.lua`. O luau-ast só serve para código Luau (sem goto).
- Decryptor estático de strings (base64/bxor e o subtrator de números) — reaproveitar a
  abordagem do interpretador Python do AGC (`tools/luaeval.py`).

## Plano de devirt do ZenAC (próximos passos)
1. Normalizar `zenac_out.lua` (remover BOM) + obter parser com goto.
2. Decodificar estaticamente as strings/constantes (decryptor base64+bxor e o subtrator).
3. Identificar o deserializer e o layout de colunas SoA deste build (derivar o mapa, não
   copiar os números do artigo).
4. Desserializar o payload (linha 9664) → grafo de protos.
5. Mapear opcode→handler (AST fingerprint), aplicar lei da continuação (PC=target+1),
   recuperar CFG, resolver upvalues (p[6]), liftar para Lua legível.

## Tentativa de devirt — resultados e bloqueio (2026-10-15)
- **Ferramenta:** instalado `luaparser` 4.2.0 (parser Lua com `goto`) — parseia o
  `zenac_out.lua` limpo (BOM removido). Conjunto de nós: If/While/Goto/Label/Call/Index/
  ops; **sem `for`**.
- **Payloads cifrados:** os 2 grandes literais (18.444 e 9.224 chars) são **base64 de
  bytes CIFRADOS** → decodificam para binário (~37% imprimível), **sem strings legíveis**.
  Diferente do AGC (bytecode com strings em claro); aqui é o modelo Luraph de constantes
  LCG/bxor decifradas em runtime. Scan estático simples não revela nada.
- **Upvalues NÃO resolvidos:** `upvalN` (upval0..upval12) têm **369 leituras, 0 `local`,
  2 escritas** → são nomes livres que o decompilador não ligou. Logo `zenac_out.lua`
  **não é executável offline** (`upval1`=nil ⇒ `v5(v6,v7)` chama nil ⇒ crash imediato).

### Conclusão (limite real, honesto)
Com os inputs atuais — **payload cifrado** + decompilação com **upvalues não resolvidos**
e **goto-flattening** — a devirtualização estática completa **não é tratável**:
- para decifrar o payload preciso do decryptor+chaves do runtime (traçar isso em ~9.700
  linhas goto/upval-livre é inviável à mão);
- para rodar o deserializer offline (abordagem do artigo) o runtime precisaria dos
  upvalues ligados e de stubs — e a decompilação não dá os upvalues.

### Caminho que destrava (divisão de trabalho igual à do artigo)
O artigo **captura o grafo SoA dinamicamente** (hook no deserializer) e só então faz o
**lifting estático**. Para o ZenAC, o que destrava:
1. **(ideal) Dump dinâmico:** rodar o harness do Passo 1 do artigo no **.luau ORIGINAL do
   ZenAC** (não no bytecode) no seu runtime Luau/executor, com o hook no deserializer
   (`error("BOUNDARY_CAPTURED")`), gerando o **grafo SoA de 11 colunas (JSON)** + o
   **k_table** (pool de constantes já decifrado). Com isso eu faço o lifting estático
   (CFG + lei da continuação + opcode map + upvalues p[6] → Lua limpo) — essa parte eu
   domino.
2. **(alternativa) Decompilação com upvalues resolvidos:** se o decompilador emitir os
   upvalues ligados (não como `upvalN` livres), dá pra rodar o runtime offline e capturar.
3. **(alternativa) Dumps prontos:** se você tiver os equivalentes do ZenAC a
   `prototype_graph.txt` / `k_table.json` / `opcode_handlers.txt`, mando o lifting direto.

## Achados (vão sendo anexados abaixo)
- Payload cifrado + upvalues não resolvidos ⇒ precisa de dump dinâmico do SoA p/ seguir.
