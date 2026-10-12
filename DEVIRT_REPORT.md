# Desvirtualização de `gamingchairac`: resultado

Entregas desta fase, na raiz do repositório:

| Arquivo | O que é |
|---|---|
| `gamingchairac.src.lua` | o programa que rodava dentro da VM, como Luau legível e executável |
| `gamingchairac.protos.txt` | listagem do bytecode da VM: ISA, árvore de protótipos, constantes, instruções |
| `tools/devirt/` | o pipeline que produz os dois, mais os verificadores |

Reproduzir tudo a partir do artefato original:

```sh
tools/devirt/run.sh <dir-dos-binarios-luau> <dir-de-trabalho>
```

O script baixa nada e não fala com jogo nenhum: ele roda o artefato num Luau
isolado apenas para obter o que a VM calcula a partir de constantes (o bytecode
decodificado e a árvore de protótipos desserializada) e faz o resto
estaticamente.

---

## 1. O que o programa é

`AntiGamingChair`: um anti-cheat **client-side** de Roblox, publicado dentro de
uma VM própria (bytecode interpretado por `t[119]`) para dificultar leitura.
O que o código recuperado faz, lido das constantes e do fluxo:

- **Canal com o servidor.** Procura `RemoteFunction`/`RemoteEvent` chamados
  `MainRemote` e `CrashSignal`, confere o atributo `AGCRemoteRole` de cada um,
  e reclama em `[AntiGamingChair] Missing replicated remote:` se faltar.
  Responde a `OnClientInvoke`/`OnClientEvent`.
- **Sondas de ambiente.** Chama serviços pouco usados (`AssetService`,
  `GuiService`, `LogService`, `TestService`, `UGCValidationService`,
  `VRService`, `PointsService`, `ContentProvider`) e compara o resultado com o
  esperado. As sondas têm nomes de fachada — `CameraWarmStart`,
  `GuiDiffSampler`, `AvatarPoseAudit`, `AudioCacheProbe`,
  `LocaleFallbackTrace`, `TextureBudgetScan`, `ViewportPulse`,
  `FrameQueueMirror`.
- **Impressão digital por mensagem de erro.** Chama métodos pelo caminho
  errado de propósito e casa a mensagem exata que o Roblox devolve:
  `"Expected ':' not '.' calling member function GetLogHistory"`,
  `"^%a+ is not a valid member of Player"`,
  `"^GetLogHistory is not a valid member of Workspace"`. Um executor que
  reimplementa esses membros erra o texto.
- **Anti-tamper.** `debug.info`/`debug.getinfo` sobre as próprias funções
  (`linedefined`, `lastlinedefined`, `source`, `what`), `debug.gethook`,
  `getfenv`, `getmetatable`, e metatabelas protegidas com
  `__metatable = "<3 STOP LOOKING AT MY METATABLES MAN"`.
- **Reação.** `Kick` com `[AntiGamingChair] Unauthorized activity`,
  `[AntiGamingChair] ClientIntegrity` ou `PROBE`.

Vale registrar: a defesa é inteiramente do lado do cliente, então ela só
atrasa quem já controla o cliente. É o que o artefato faz, não um julgamento
sobre se funciona.

## 2. O bytecode da VM

`gamingchairac.protos.txt`, gerado por `tools/devirt/dumpprotos.py`:

- **179 protótipos**, **11.454 registros de instrução** (10.203 deles
  alcançáveis), **3.067 constantes**.
- **330 dos 512 opcodes** do executor aparecem neste bytecode, em **282
  handlers distintos**. Os outros 182 estão no despachante mas nenhuma
  instrução daqui os usa — se são iscas ou se o empacotador os emite para
  outros programas, este artefato não diz.
- O ISA é impresso nos termos do próprio executor, com os campos resolvidos
  (`R[A] = K[B]`, `pc = B`, `R[A] = ENV[K[B]]`), e cada instrução repete o
  handler com os operandos daquela instrução substituídos.
- Há **superinstruções**: handlers cujos campos `A`/`B`/`C`/`D` são *colunas*
  indexadas por sub-passo (`A[2]` é o `A` do segundo passo), chegando a 80
  passos num opcode só. E handlers **fundidos**, que leem as instruções
  seguintes direto da seção de código (`CODE[pc + 1].A`) e despacham pelo
  campo `D` delas como se fosse um opcode secundário.

## 3. O código recuperado

`gamingchairac.src.lua`, gerado por `tools/devirt/emitsrc.py`:

- **5.618 linhas**, os 179 protótipos como funções Luau aninhadas.
- **Zero `goto`, zero label, zero laço de despacho.** Todo o fluxo é
  `if`/`while`/`repeat`/`for`/`break`/`continue`. Compila com `luau-compile`.
- Chamadas de método (`u3:Kick(...)`), `for in` nativo, `and`/`or`
  preguiçosos, constantes resolvidas: é Lua idiomático, não um interpretador
  reescrito.
- As tabelas antes do corpo não são enfeite: alguns opcodes entregam ao
  programa as suas próprias tabelas de registradores, de código e de
  constantes, então o programa lê o seu próprio bytecode e elas têm de ficar.

**O que não volta de bytecode nenhum:** nomes de locais e comentários do
autor. Todo o resto — fluxo, constantes, globais, nomes de campo, estrutura de
chamada — é do original.

Onde o próprio código diz o que uma variável guarda, ela leva esse nome
(`tools/devirt/names.py`). Nada é inventado: o nome vem do global copiado, do
campo ou método que a produziu, da string de classe passada a `Instance.new`,
da função de biblioteca que ela aliasa. Uma variável cujas definições
discordam entre si, ou que só guarda um intermediário, fica numerada — um nome
errado seria pior que `v12`.

    local v = pcall                       ->  pcall_
    local v = string.char                 ->  char
    local v = v8.LocalPlayer              ->  localPlayer
    local v = v8:GetService("Players")    ->  players
    local v = v8:GetLogHistory()          ->  logHistory
    local v = Instance.new("RemoteEvent") ->  remoteEvent
    local ok, err = pcall(...)            ->  ok, err
    local v = v8                          ->  o nome de v8, mais um número

**362 dos 1.326 locais** ganham nome, o que cobre **2.572 das 6.855
menções** a variável (38%); as outras 4.283 continuam `vN`, e continuam
sendo intermediários sem evidência. Os parâmetros das IIFEs de captura
também são nomeados, então `(function(u6, u8)` virou
`(function(logService, localPlayer)` e a linha do kick se lê sozinha:

```lua
localPlayer:Kick("[AntiGamingChair] Unauthorized activity")
```

O sufixo `_` marca um *snapshot* de global (`pcall_` guarda `pcall`): o
programa compara o snapshot com o global vivo depois, de propósito, então os
dois têm de continuar distinguíveis. Pelo mesmo motivo nenhum local recebe o
nome de um global que o programa leia em algum lugar — o nome capturaria essa
leitura.

## 4. Como isso é verificado

Dois critérios objetivos, ambos automatizados:

**Equivalência de fluxo, por protótipo** (`tools/devirt/checkall.py`). Para
cada protótipo, o grafo original e o código estruturado são executados lado a
lado com condições aleatórias e os caminhos comparados:

```
equivalent 179  divergent 0  unstructured 0  (150 trials each)
```

179 de 179 estruturados, nenhum divergente, nenhum sobrando — ou seja, nenhum
protótipo precisou do despachante de reserva.

**Equivalência de comportamento, do programa inteiro**
(`tools/devirt/difftest.py`). A VM original e o código desvirtualizado rodam
no mesmo ambiente Roblox simulado, registrando cada acesso ao ambiente
global; os dois traces são comparados evento a evento:

```
orig events 4196  devirt events 4196  identical prefix 4196
```

Prefixo idêntico igual ao total: os traces são iguais do início ao fim, mesmo
desfecho.

**Reprodutibilidade.** `emitsrc.py` escreve o mesmo arquivo byte a byte em
execuções diferentes (conferido com `PYTHONHASHSEED` diferentes). Antes isso
não valia: `peval.materialize` percorria um *set* de localizações de origem
para criar os temporários de um laço residual, e a ordem de hash do Python
mudava a numeração dos temporários — e, por tabela, todo nome gerado depois.
O arquivo entregue é o mesmo artefato que o teste diferencial verificou,
tirando o cabeçalho de comentários.

## 5. Um bug encontrado e corrigido na nomeação

Nomear expôs um defeito que a numeração escondia. Um upvalue capturado por
nome é renderizado como o nome que a função *envolvente* dá à variável; se a
função filha declarasse um local com aquele mesmo nome, a referência ligaria
no local errado. Com todas as funções numerando de `v1` para cima, isso
acontecia: **4 casos reais** (protos 8, 127, 177 e 179), onde a filha
referencia o upvalue *e* declara um local homônimo.

A versão anterior deste arquivo (commit `972eb04`) tem esses 4 pontos
errados. O teste diferencial não os pegou porque não estão no caminho que o
ambiente simulado exercita.

A correção é estrutural, não um remendo: cada função recebe o conjunto de
nomes visíveis nas funções que a contêm e nunca entrega um deles a um local
seu. `render()` agora afirma a invariante a cada protótipo, então um
sombreamento futuro quebra a geração em vez de sair silencioso no arquivo.

## 6. Limites conhecidos

- Nomes de locais e comentários originais: perdidos na compilação,
  irrecuperáveis.
- O trace cobre a inicialização no ambiente simulado. Caminhos que só um jogo
  real alcança não são exercitados por ele — mas o lifter é **estático**:
  levanta as **10.203 instruções alcançáveis** a partir do ponto de entrada
  de cada protótipo, com **zero erros**, então esses caminhos estão no
  arquivo; só não têm esse segundo carimbo. As 1.251 instruções restantes dos
  11.454 registros não são alcançáveis de entrada nenhuma; estão na listagem
  do bytecode, não no código gerado.
- Uma função passa do limite de locais do Luau, então parte das suas
  variáveis vive numa tabela local (`spilled_funcs: 1`): elas aparecem como
  `__L.v12` em vez de `v12`. O nome se mantém; só a forma é mais pesada.
- `t[1][21][7]` (um opcode aritmético, 1 uso) é uma função guardada na tabela
  de constantes da VM cujo valor não é escalar; aparece sem resolver na
  listagem.
