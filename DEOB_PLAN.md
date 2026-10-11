# Plano de desofuscação — `gamingchairac.unflat.lua` → código próximo ao original

**Objetivo:** produzir o Lua mais próximo possível do fonte original — controle de fluxo
nativo, sem o ruído do flattening, com nomes legíveis — preservando o comportamento.

**Entrega:** `gamingchairac.deob.lua` (resultado) + `DEOB_REPORT.md` (o que foi
recuperado, o que é irrecuperável, confiança por handler), em commits revisáveis na
branch `claude/intelligent-darwin-g33037`.

## Expectativas realistas (limites do "próximo do original")
Isto é um **artefato decompilado e depois reofuscado**, não o fonte. Mesmo no melhor caso:
- **Nomes e comentários originais estão perdidos** — darei nomes derivados do uso, não os reais.
- **Buracos do decompilador são irrecuperáveis:** `t[6]` e `t[108]` trazem
  `structuring failed for function N`. Ficam como stubs anotados; não há o que reconstruir.
- **Dialeto-alvo é Luau** (há if-expressions `x = if c then a else b`), não Lua 5.1.
- **Equivalência, não identidade:** garanto comportamento equivalente + legibilidade,
  não o texto exato do autor.

## Estágios (incrementais, validados, commit a commit)

### Estágio 0 — Toolchain e rede de segurança
- Snapshot do arquivo atual.
- Obter um validador **Luau** (`luau`/`luau-analyze`, binário de release) para checagem
  de sintaxe após cada transformação. Se a rede bloquear, cair para um validador
  estrutural em perl (balanceamento de blocos/parênteses) — mais fraco, porém útil.
- Inventário por handler: estados, transições, variáveis, tabelas de dados vs. maquinaria.

### Estágio B — Remoção de código morto (perl, consciente de escopo)  — *seguro*
Remover apenas a maquinaria do flattening, **preservando dados/decoders reais**:
- escritas mortas `t3[n] = <num>` (bookkeeping nunca lido);
- `local t2 = {}` / `local t3 = {}` vazios da maquinaria + seu gerador
  `local function fN(p1,p2,p3) ... p1+p2-p3 ... end`;
- **NÃO** tocar em `local t3 = { 10, 72, ... }` nem nos decoders `fN(p1): t[p1]+p1*K%4096-C`.
- Validar: parsing OK; contagem de handlers e de transições inalterada.

### Estágio R — Renomear o pool de constantes  — *alto valor, seguro*
- Mapear `p1..pN` de `f1` para os valores passados na chamada final
  (`string.gsub`, `string.len`, `table.remove`, `math.abs`, ...), confirmados pelos
  comentários `--[[ Upvalues ... ]]`.
- Substituir usos: `p5(p1,"\26","")` → `string_gsub(p1,"\26","")` (com cabeçalho de
  aliases locais), tornando as chamadas de stdlib legíveis.

### Estágio C — Estruturação do controle de fluxo (núcleo)  — *difícil, validado*
Para cada handler, reverter a máquina de estados em controle nativo:
1. Construir o CFG a partir das transições já resolvidas (`v = <estado>`).
2. Aplicar algoritmo de estruturação (relooper): `if/elseif/else`, `while`, `repeat`,
   loops — eliminando o despachante `while true / if v==N`.
3. Validar por handler: conjunto de transições preservado (checagem estática) + parsing.
4. **Piloto primeiro:** `t[11]` (trivial), depois um médio, acertar a abordagem e revisar
   com você, **antes** de escalar para os 45.
5. Os 3 monstros (`t[18]`, `t[114]`, `t[119]`, ~65% do arquivo — a VM) por último,
   com cuidado extra. Stubs do decompilador ficam como buracos anotados.

### Estágio D — Decodificação de strings  — *best-effort, pode ser inviável*
As strings reais são blobs criptografados decodificados por aritmética que depende de
estado de runtime (`t[1][...]`). Tentarei reimplementar a aritmética estaticamente; se
exigir execução/estado dinâmico, **documento e não chuto** — deixo o blob + o decoder
identificado. (Instalar um runtime Luau para decodificar de fato é um opcional a discutir.)

## Pontos de decisão para você
- Começo pelo **Estágio 0+B+R** (seguro) e paro no **piloto do Estágio C** para sua
  revisão antes de escalar? (recomendado)
- Nome do arquivo de saída: `gamingchairac.deob.lua` — ok?
- Estágio D (strings): tentar best-effort agora, ou deixar para depois?
