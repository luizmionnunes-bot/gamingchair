# Relatório de desofuscação — `gamingchairac`

Entrada: `gamingchairac.unflat.lua` (Stage A — unflatten das transições de estado).
Saída:   `gamingchairac.deob.lua` (em evolução pelos estágios abaixo).

Alvo: Lua/**Luau** mais próximo possível do original, preservando o comportamento.
Toda transformação é validada por `luau-ast` (parse) e verificada quanto à
**preservação do grafo de estados** (o motor `tools/sm.py` reextrai o CFG e compara).

## O que é o script
Módulo Roblox (`Workspace.internal`) decompilado pelo executor "Potassium" (lua.expert)
e fortemente ofuscado por **control-flow flattening**. Uma função `f1` recebe o "pool de
constantes" (funções de stdlib) por parâmetro e constrói uma tabela `t` de 45 handlers
`t[N]`; cada handler era uma máquina de estados achatada. Strings reais são blobs
criptografados decodificados em runtime.

## Estágios

| Estágio | O quê | Status | Verificação |
|---|---|---|---|
| 0 | Toolchain (luau-ast/compile), snapshot, inventário | ✅ | baseline parseia (após fix do cabeçalho) |
| — | **Fix de cabeçalho**: `--[[ … --[[s]] … ]]` fechava o comentário cedo → `--[==[ … ]==]` | ✅ | sem fix, nem parseia |
| B | Remoção de código morto (liveness na AST) | ✅ | grafo de estados idêntico |
| R | Rename do pool de constantes → nomes de stdlib | ✅ | alpha-rename puro; parseia |
| C | Estruturação do controle de fluxo (máquina de estados → nativo) | ✅ 13 handlers | traços simbólicos + cobertura |
| D | Decodificação de strings (best-effort estático) | ✅ (inviável) | decoder identificado |

### Estágio B (feito)
Removidos **3.455 linhas**: 196 tabelas mortas, 103 funções mortas (37 geradores do
flattening `fN(p1,p2,p3)` + 66 decoders `fN(p1)` **nunca chamados** — artefatos do
decompilador) e 320 escritas mortas `t3[n]=num`. Critério: só remove locais com **zero
referências** (não-chamáveis em Lua) e tabelas **somente-escritas** → provadamente morto.
Tabelas de dados reais e decoders realmente chamados foram preservados.
Resultado: 22.066 → 18.611 linhas. **Grafo de estados idêntico ao Stage A.**

### Estágio R (feito)
`f1` recebe o pool de constantes posicionalmente; a chamada final
`return f1(error, next, string.match, …, string.format, …)` fixa o significado de cada
parâmetro. Renomeados 33 parâmetros + 122 referências (desambiguados do shadowing pela
**localização de declaração** na AST). Mapa:

```
p1=error p2=next p3=string.match p4=tonumber p5=string.gsub p6=string.sub
p7=table.insert p8=string.char p9=string.byte p10=coroutine.yield p11=coroutine.wrap
p12=string.rep p13=table.concat p14=math.floor p15=select p16=getfenv/_ENV
p17=setmetatable p18=next p19=table.unpack p20=nil p21=math.min p22=<decoder>
p23=string.len p24=table.remove p25=table.sort p26=string.unpack p27=string.gmatch
p28=string.find p29=string.reverse p30=tostring p31=math.abs p32=rawget p33=string.format
```
Ex.: `p5(p1, p8(226,…), "")` → `str_gsub(p1, str_char(226,…), "")`.

### Estágio C (feito — 13 handlers nativizados)
Motor (`tools/sm.py` + `tools/stageC*.py`): para cada handler, reconstrói o CFG de
blocos básicos a partir das transições resolvidas, separa **efeitos** de **roteamento**
(atribuições ao loopvar, temps `--[[s]]`, `continue`/`break`/`return`, sentinelas de
saída `while v ~= K`), e para os **acíclicos** emite `if/else` nativo via
pós-dominadores. Cada handler nativizado passa por **duas** verificações independentes:
1. **equivalência de traços simbólicos** (enumera atribuições às condições; o traço do
   CFG = o traço da árvore nativa emitida), e
2. **cobertura de efeitos** (toda instrução-efeito do laço — assigns, chamadas,
   `return <valor>` — está coberta por algum corpo de estado; senão, recusa).

Nativizados (máquina de estados → controle nativo, marcados no arquivo):
**t[3, 7, 11, 12, 13, 26, 27, 34, 41, 42, 76, 77, 88]**. Exemplo t[11]:
```lua
p1 = p1 % t[5]
if p1 < 0 then p1 = p1 + t[5] end
return p1
```
Outros **13** handlers já eram straight-line (sem máquina de estados).

**Não nativizados por segurança (19):** handlers com loops reais (cíclicos) ou com
dispatch aninhado que manipula o loopvar dentro de `while`/`repeat` — entre eles os
grandes `t[18]`, `t[92]`, `t[100]`, `t[101]`, `t[114]` (574 estados). Reestruturá-los
com garantia exige um relooper com suporte a loops; deixei-os na forma B+R limpa em vez
de arriscar emitir código nativo sutilmente incorreto. Verificado: o grafo de estados
desses 19 (+ os 13 straight-line) é **idêntico** ao do Stage A/R.

### Estágio D (feito — conclusão: inviável estaticamente)
As strings criptografadas são decodificadas em runtime por **`t[18](<blob>)`**
(ex.: `t[19] = t[18]("nN(\"*?\026...")`). `t[18]` é um handler-máquina-de-estados que
depende de `t[1][...]` inicializado em runtime por outros handlers. Decodificar
estaticamente exigiria emular a VM inteira com seu estado — fora do escopo e não
confiável. Os decoders aritméticos puros `fN(p1)=t3[p1]+p1*K%4096-C` que pareciam
decodificar strings eram, na verdade, **mortos** (nunca chamados; removidos no Stage B).

## Inventário dos handlers (pós-B)
45 handlers, **1.050 estados** no total. 13 handlers não têm máquina de estados de
topo (são straight-line que montam dados via closures decodificadores inline, p.ex.
t[119]) ou stubs do decompilador (t[6], t[108]: `structuring failed`). Maiores:
`t[114]`=574 estados, `t[100]`=68, `t[18]`=53, `t[101]`=47, `t[85]`=43, `t[66]`=27.

## Limites conhecidos (irrecuperável deste artefato)
- Nomes/comentários originais perdidos (damos nomes derivados do uso).
- `t[6]`, `t[108]`: o próprio decompilador falhou (`structuring failed`) — stubs vazios.
- 1 restrição de compilação Luau pré-existente (`continue` sobre `local` em `repeat..until`),
  herdada do decompilador; deve desaparecer quando o `repeat` for reestruturado no Estágio C.
- Decodificação de strings depende de estado de runtime (`t[1][…]`) → majoritariamente
  inviável estaticamente.
