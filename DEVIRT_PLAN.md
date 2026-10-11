# Plano de desvirtualização: `gamingchairac` → código-fonte legível

**Objetivo:** recuperar o programa que roda dentro da VM do ofuscador como Lua legível,
com comportamento equivalente. Recuperar o texto exato do autor não é possível: nomes
locais e comentários se perdem na compilação.

**Ponto de partida:** branch `claude/intelligent-darwin-g33037`. O flattening já foi
desfeito (Stages A–C), o harness Luau existe (`tools/mkharness.py`) e o bloqueio está
documentado em `STATIC_RESOLUTION.md`.

---

## 1. O que já sabemos (pipeline da VM)

Linhas referentes a `gamingchairac.unflat.lua`:

| Passo | Código | Papel | Estado |
|---|---|---|---|
| 1 | `t[19] = t[18]("…blob…")` (l. 21222; `t[18]` em l. 301–5698) | decodifica o blob base-85 → string de bytecode | decompilado ✅ |
| 2 | `t[120] = t[114](t[19])` (l. 16924; `t[114]` em l. 11494) | desserializa → árvore de protótipos | decompilado, mas chama `t[30]` ❌ |
| 3 | `t[121] = t[116](t[120])` (l. 16611; `t[116]` em l. 19682) | pós-processa os protótipos (desconhecido) | **stub** (fn 234) ❌ |
| 4 | `t[122] = t[119](t[121], {}, env)` (l. 20664; `t[119]` em l. 5712) | executor (interpretador) | decompilado ✅ |

Leitores do stream (estado: string em `t[19]`, posição em `t[20]`):
- `t[27]` lê 1 byte (`string.byte(s, t[20])`, depois `t[20] += 1`). ✅
- `t[29]` lê um varint em base 128 (`t[1][21][1]` = 128), com ajuste `v > 127`. ✅
- `t[30]` é outra variante de varint/inteiro, com **127 chamadas**. **Stub** (fn 268). ❌

O executor (`t[119]`) também lê operandos direto de `t[19]` com `t[20] = v16[v11]` e
`t[30](t[19])` (l. 7104+). Ou seja, as instruções são decodificadas sob demanda a partir
da string, não pré-decodificadas.

**Classificação dos 16 buracos do decompilador:**

| Tipo | Funções | Ação |
|---|---|---|
| Caminho crítico | `t[30]` (268), `t[116]` (234) | reconstruir (Fase 2) |
| Chamados uma vez, inferíveis pelo contexto | `t[6]` (3), `t[75]` (228) | reconstruir se o trace passar por eles |
| Polyfills mortos em Luau | 96, 100 (fallback de `bit32`, ver l. 10829 `bit32 or bit`), 156 (`table.move`) | ignorar e verificar com trace |
| Triviais | 173 (comparador de `table.sort`) | inferir pela chamada |
| Sem chamada direta conhecida | `t[22]`, `t[87]`, `t[102]`, `t[103]`, `t[108]`, `t[115]`, 128, 160, 186 | só tratar se o trace os alcançar |

---

## 2. Princípios

1. **Cada fase tem um critério de aprovação objetivo.** Não avançamos com base em "parece certo".
2. **A execução dinâmica é o oráculo.** Toda reconstrução estática é validada rodando no Luau
   isolado (sem rede, ambiente Roblox simulado, nada se conecta a jogo real).
3. **Hipóteses ficam registradas.** Toda função reconstruída por inferência vai para
   `RECONSTRUCTED.md` com: evidência, variantes testadas, por que a escolhida venceu.
4. **Commits pequenos e reversíveis** no branch `claude/keen-cerf-y0y9nx`.
5. **Caminho alternativo sempre aberto** (seção 5): se uma fase empacar, sabemos para onde ir.

---

## 3. Fases

### Fase 0: Base e reprodução *(curta)*
- Trazer para este branch o trabalho de `claude/intelligent-darwin-g33037` (merge): `tools/`,
  `.deob.lua` e os relatórios.
- Instalar o Luau de release (`luau`, `luau-ast`, `luau-compile`) fora do repositório.
- Gerar a cópia executável (`make_runnable.py`) e o harness (`mkharness.py`).
- **Aprovação:** reproduzir exatamente o travamento documentado (`+ nil` em `t2[138] + t[30](p1)`).

### Fase 1: Extrair o bytecode bruto *(curta)*
- Instrumentar a atribuição `t[19] = t[18](…)` e gravar a string em `out/bytecode.bin`.
- Medir tamanho, entropia e histograma de bytes, e procurar cabeçalho ou números mágicos.
- **Aprovação:** dump determinístico (mesmo hash em 3 execuções). Se variar entre execuções,
  há aleatoriedade ou chave dependente do ambiente: anotar e fixar a seed ou o ambiente.

> A partir daqui não dependemos mais de `t[18]`. Todo o resto pode trabalhar em cima de
> `bytecode.bin` mais os handlers.

### Fase 2: Reconstruir o caminho crítico *(curta a média, é a fase decisiva)*

**2a. `t[30]`**
- Candidatos: varint sem sinal LE base-128; varint com sinal (ajuste `>127`, igual a `t[29]`);
  zigzag; inteiro fixo de 2/4 bytes (`string.unpack`, que está no pool de constantes).
- Analisar as 127 chamadas: onde o resultado vira índice (`v72[t[30](…)]` → registrador,
  não negativo), onde vira contador (`t2[138] +=` → tamanho) e onde vira deslocamento de salto
  (pode ser negativo).
- **Oráculo:** a variante certa faz `t[114]` consumir `bytecode.bin` **exatamente até o fim**,
  com contagens plausíveis (nº de protos, constantes e instruções pequenos e positivos)
  e constantes string com texto legível.

**2b. `t[116]`**
- Comparar o que `t[114]` **produz** (campos escritos em `t2[141][t[49..52]]` etc.) com o
  que `t[119]` **lê** de `t[121]`. A diferença entre os dois define a função de `t[116]`.
- Hipóteses em ordem de probabilidade: (1) identidade ou reembrulho; (2) ligar sub-protos ou
  resolver índices de constantes; (3) desembaralhar a tabela de opcodes. Testar cada uma.
- **Oráculo:** `t[119]` executa o programa sem erro de tipo no ambiente simulado.

**2c. `t[6]`, `t[75]` e demais:** só se o trace os alcançar. Mesma metodologia.

- **Aprovação da Fase 2:** o programa virtualizado roda de ponta a ponta no harness
  (ou até travar esperando um objeto real do Roblox, o que já conta como sucesso).
- **Se reprovar:** se nenhuma variante passar no oráculo, ir ao Plano B (seção 5).

### Fase 3: Primeiros resultados: strings e constantes *(curta)*
- Despejar todas as constantes de todos os protótipos: strings, números e nomes globais.
- Gerar `STRINGS.md` agrupado por protótipo.
- **Já responde boa parte de "o que o script faz"** (serviços, remotes, mensagens, limites
  numéricos), antes de traduzir qualquer instrução.

### Fase 4: Ambiente Roblox simulado e trace dinâmico *(média)*
- Mock de `game`, `workspace`, `Instance`, `Players`, `RunService`, `task`, `Enum` etc. com
  proxies registrando **cada acesso** (`index`, `newindex`, `call`) e retornando novos proxies.
- Neutralizar checagens anti-tamper que aparecerem (`debug.info`, `tostring` de funções,
  `getfenv`, timing) **só no harness**, com registro do que foi checado.
- Instrumentar o executor `t[119]`: para cada instrução, registrar `(proto, pc, opcode,
  operandos, registradores antes/depois)`.
- **Aprovação:** trace completo da inicialização mais o log de interações com o ambiente.

### Fase 5: Recuperar o conjunto de instruções (ISA) *(média a longa)*
- Enumerar os handlers de opcode no despachante de `t[119]` (há ~378 comparações de estado
  na região; esperam-se 30–80 opcodes reais).
- Para cada opcode, registrar formato dos operandos (quais leituras `t[27]`/`t[29]`/`t[30]`),
  semântica (o que muda em registradores, constantes, upvalues e pc) e equivalente Luau/Lua 5.1.
- Usar o trace (Fase 4) para confirmar a semântica com valores reais.
- Detectar: opcodes embaralhados por execução, superinstruções (vários ops fundidos),
  opcodes "isca" nunca executados.
- **Aprovação:** 100% dos opcodes **presentes no bytecode** com semântica documentada em `ISA.md`.

### Fase 6: Desmontador *(curta depois da Fase 5)*
- `tools/disasm.py`: `bytecode.bin` → listagem por protótipo (`pc: OPCODE A B C ; comentário`),
  com constantes e upvalues resolvidos.
- **Aprovação:** cobertura total (nenhum byte não explicado) e listagem consistente com o trace.

### Fase 7: Lifter (bytecode da VM → Lua) *(longa)*
1. **Tradução direta:** cada instrução vira um comando Lua sobre `r0..rN`, com `goto`/labels
   (Luau não tem `goto`, então gerar em dialeto intermediário ou usar despachante simples).
2. **CFG e estruturação:** blocos básicos → `if/while/repeat/for` reaproveitando o
   relooper do `stageC2.py`.
3. **Registradores → locais:** análise de vida, junção e propagação de constantes.
4. **Closures e upvalues:** protótipos aninhados viram `function` aninhadas.
- **Aprovação, por equivalência diferencial:** rodar o Lua gerado e a VM original no mesmo
  ambiente simulado e comparar o log de interações com o ambiente. Logs idênticos = protótipo aprovado.

### Fase 8: Legibilidade e entrega *(média)*
- Renomear por uso (`v12` → `humanoid`, `p1` → `player`), agrupar funções e comentar.
- Entregas:
  - `gamingchairac.src.lua`: código desvirtualizado e legível.
  - `REPORT.md`: o que o script faz, confiança por função, o que foi inferido.
  - `RECONSTRUCTED.md`, `ISA.md`, `STRINGS.md`, `tools/`.

---

## 4. Riscos e mitigação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| `t[116]` faz algo não inferível (ex.: decifra com chave interna) | média | inferir pelo consumo em `t[119]`; senão Plano B |
| Handler de opcode está entre os stubs | baixa a média | inferir pelo trace (efeito antes/depois); senão Plano B |
| Opcodes embaralhados por execução ou chave do ambiente | média | fixar ambiente; mapear pela semântica e não pelo número |
| Anti-tamper / detecção de ambiente | média | mocks mais fiéis e neutralização registrada no harness |
| VM aninhada (VM dentro da VM) | baixa | repetir as Fases 4–6 no nível interno |
| Caminhos não executados no trace (código só alcançado em jogo) | alta | o desmontador e o lifter são estáticos e cobrem tudo; o trace só valida |

## 5. Plano B / atalhos

1. **Dump do bytecode Luau original pelo executor** (ex.: `getscriptbytecode`) e execução no
   Luau real via `luau_load` com hooks. Elimina **todos** os buracos do decompilador de uma vez,
   e as Fases 4–8 continuam iguais.
2. **Outro decompilador** sobre o mesmo bytecode. Os buracos são falhas de *structuring* do
   lua.expert, e outra ferramenta pode gerar as 16 funções.
3. **Desmontar o bytecode Luau original** com `luau-compile`/disassembler e ler à mão só as
   funções que faltam (`t[30]`, `t[116]`). É pouco código.

> Se você tiver acesso ao executor, o item 1 do Plano B é o caminho mais rápido e confiável
> para a Fase 2 inteira.

## 6. Esforço estimado

| Fase | Esforço |
|---|---|
| 0–1 | 1 sessão |
| 2 | 1–2 sessões (**ponto de decisão**: é viável?) |
| 3 | junto com a Fase 2 |
| 4–6 | 2–4 sessões |
| 7 | 3–6 sessões |
| 8 | 1–2 sessões |

## 7. Pontos de decisão

1. **Depois da Fase 2:** seguir ou acionar o Plano B?
2. **Depois da Fase 3:** as strings já respondem o que você precisava, ou vale ir até o lifter?
3. **Na Fase 7:** saída em Luau (fiel ao alvo) ou Lua 5.1 (mais ferramentas de leitura)?
