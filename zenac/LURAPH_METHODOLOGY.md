# Luraph devirtualization — metodologia (referência destilada)

> Fonte: walkthrough fornecido pelo usuário ("Deobfuscating Luraph", alvo
> `luraph_variant_01.luau`, Luraph v14.7). Aqui fica o playbook reutilizável.
> **CAVEAT:** números de opcode, offsets, contagens de proto e índices de coluna no
> artigo são **específicos do variant_01**. Opcodes são embaralhados **por build**;
> para o ZenAC é preciso **derivar o mapa próprio** (não copiar os números do artigo).

## Arquitetura da VM (Structure-of-Arrays, 11 colunas por prototype)
Luraph não usa tuplas `{op,a,b,c}`; cada proto decompõe em 11 arrays-coluna:
| col | nome | semântica |
|----|------|-----------|
| p[1] | const_immediates | pool A (números/const 32-bit) |
| p[2] | const_globals | pool B (strings/nomes globais/API) |
| p[3] | proto_children | protos filhos (closures aninhadas) |
| p[4] | numparams | nº de parâmetros |
| p[5] | maxstack | largura do registrador de pilha |
| p[6] | captures | descritores de upvalue `{mode,index}` |
| p[7] | opcodes | stream de opcodes (indexado por PC) |
| p[8] | reg_dest | registrador destino |
| p[9] | reg_src1 | fonte1 / alvo de branch |
| p[10] | metadata | flags de runtime |
| p[11] | reg_src2 | fonte2 |
- v14.7 = 11 colunas fixas. **v15 = 32 slots com permutação por-proto (metamap)** — aí é
  preciso extrair o mapa de slots do prólogo de alocação de cada proto.

## Wrapper / fingerprints
- Wrapper externo: `return ({ ... }):t()(...)` (dicionário de helpers + tail call `:t()`).
- Aliases de reader: `"readf64"`, `"readi16"`, `l="copy"` (`\99o\112y`), `"writeu32"`.
- Anti-parser: **numerais com `_` à direita** (`0X2__`=2, `0B110000_`=48) — quirk do lexer
  Luau; quebra formatadores externos. **Parâmetros duplicados** (`function(z,z,a)`) — o 2º
  sombreia o 1º; descarta o `self` de chamadas `:`.
- Payload: string enorme cifrada, desempacotada por uma função (`N[..]=N[..]([=[...]=])`).

## Lei da continuação (crítico)
Interpretador: `op=col7[PC]; handler(...); PC = PC + 1` (pós-incremento). Handler de jump
faz `PC = target`; como o loop soma 1 depois ⇒ **effective_PC = target + 1**. (Branch
relativo: `effective_PC = PC + offset + 1`.) Isso dissolve os anéis de **trampolim decoy**.

## Receita em 5 passos
1. **Dump dos protos no "seam":** hookar a função deserializer (`t`/`U8`) e capturar `D`
   (grafo de protos) **antes** da execução do VM; crawl recursivo acha todos os protos.
   (Estático: replicar o deserializer e fatiar o payload offline.)
2. **Descartar Proto 1/2 (anti-tamper):** em v14.7 o Proto 2 (~4.900 instr., sondas
   Roblox: StarterPlayer/HttpService/Vector3…) é watchdog puro, sem dataflow para os protos
   de aplicação ⇒ pode ser isolado. **v15 encadeia** retornos das sondas no key schedule
   (LCG) ⇒ não dá pra descartar trivialmente.
3. **Decodificar linearmente com a lei da continuação** + tabelas de branch/dispatch do
   build; traduzir aritmética/tabela direto para registradores.
4. **Resolver upvalues via p[6]:** mode 0 = captura registrador local do pai `v[index]`;
   mode 1 = encaminha upvalue do pai `upval[index]`.
5. **Montar e rodar** o proto raiz; closures em opcodes de make-closure (107/216).

## Decriptação de constantes
- v14.7: **LCG** (A=1664525, C=1013904223, M=2^32), key_byte = `rshift(seed,16)&0xFF`,
  `out = bxor(raw, key_byte)` por byte; seed inicial por string (lazy, ~Opcode 10).
- v15: cipher stream **byte-wise (mod 256)** com acumuladores rolantes.
- Pragmático: deixar o deserializer nativo rodar e **hookar após o unbiasing** para pegar
  o pool de constantes pronto (evita divergência de cifra entre versões).

## Passes do decompilador
- **CFG:** líderes = instr 1, alvo de jump (`target+1`), e pós-branch/return (`pc+1`).
  Classificar opcodes de jump incondicional / branch condicional / return (coluna do alvo
  varia por opcode).
- **Dispatch dinâmico vs decoy (def-use):** algumas escritas `vTab[raw]=eff` **remapeiam
  opcodes** em runtime (`handler = handlers[vTab[raw_op]]`); NÃO podar cegamente — fazer
  SSA def-use; só podar tabelas comprovadamente mortas.
- **Predicados opacos / suicide blocks:** const-fold + poda de arestas + BFS de
  alcançabilidade remove `while true do end` de armadilha.
- **CFG irredutível (multi-entrada):** Relooper falha ⇒ **node-splitting** (clonar nós
  compartilhados por entrada) antes do Relooper, para evitar a máquina de estados de 20k
  linhas.
- **Lifting → IR tipada:** registradores como places `v0..maxstack`; SSA com efeitos
  (may_throw/reads/writes); mapa opcode→IR (add/sub/mul/div/mod/pow/concat/not/len/neg/
  move/loadk/newtable/tget/tset/getglobal/closure/getupval/call/return/vararg).

## Chamadas multi-valor / varargs
- Call (op 0/182): A=base com a função; B=argc (0 = até o topo); C=retc (0 = todos).
- Vararg: helper de unrolling em árvore binária (`z[26]`), lift para `f(...)`/`return ...`.
