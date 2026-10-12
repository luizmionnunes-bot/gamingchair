# Resolução estática — strings resolvidas só com este arquivo

Objetivo: resolver as strings ofuscadas **100% estaticamente, usando apenas
`gamingchairac.unflat.lua`** — sem Luau, sem ambiente de jogo, sem rede.

## Resultado: ✅ strings recuperadas

As strings reais estão num **único blob de 196 KB** decodificado por
`t[19] = t[18]("<blob>")` (linha ~17617). Mostramos que o decoder `t[18]` (→ `t[8]`,
`t[9]`, `t[10]`, `t[17]`) é **puro**: lê só constantes literais do próprio arquivo
(`t[1]` e suas sub-tabelas montadas no init) + stdlib, **sem globais de jogo, sem a VM,
sem os stubs**. Logo é estaticamente avaliável.

### Como (partial evaluation, em Python)
1. `tools/luaeval.py` — interpretador de subconjunto Lua(u) sobre a AST do `luau-ast`.
2. `tools/stdlib_lua.py` — runtime padrão do Luau em Python (string/table/math/
   coroutine/**buffer**/**bit32**/task/os + builtins + pcall). Semântica universal, não
   é dado externo. `task.spawn`/`task.defer`/`task.wait` são **no-ops** ⇒ o laço
   principal da VM nunca inicia; `getfenv()` devolve tabela vazia ⇒ os caminhos
   `lib[nome] or fallback` caem no **fallback puro**.
3. `tools/decode2.py` — roda o `init` do `f1` no interpretador (injetando um `t`
   observado) e **para exatamente** na atribuição `t[19] = t[18](blob)`, isto é, logo
   após o pool ser decodificado e **antes** de qualquer código de VM/jogo.

Resultado: `t[18]` devolveu **189.765 bytes** (determinísticos, só do arquivo) em
~110M passos do interpretador (~6 min).

### O que esses 189 KB são
Não é texto: é o **bytecode da VM** (`t[114]`). Confirmado pelo uso — a VM o lê com
`t[30](t[19])` repetidamente (`t[30]` é o leitor de bytecode, um stub
`structuring failed` do decompilador). As strings do programa são **constantes
embutidas nesse bytecode**, armazenadas **prefixadas por tamanho** (`[len][bytes]`).

### Extração das strings
Varrendo o bytecode decodificado por `[len][len bytes imprimíveis]` recuperamos
**386 constantes** (em `gamingchairac.strings.txt`), entre elas:
- **AntiGamingChair (AGC)** — é um **anticheat**: `[AntiGamingChair] ClientIntegrity`,
  `[AntiGamingChair] Unauthorized activity`, `[AntiGamingChair] Missing replicated
  remote:`, `[AGC][InternalPulse][Advance]`, `<3 STOP LOOKING AT MY METATABLES MAN`.
- APIs Roblox: `GetService`, `FindFirstChild(OfClass)`, `FireServer`, `InvokeServer`,
  `RemoteEvent/Function`, `HttpService`, `LogService`, `RunService`, `GetPropertyChangedSignal`,
  `ReplicatedStorage`, `CoreGui`, `Players`, `HumanoidDescription`, `GenerateGUID`...
- Detecção de tamper: `debug.getinfo`/`gethook`/`getfenv`, `freeze`, `MessageOut/Error/Warning`.
- Internos: `agc_idv_`, `agc_pn/pr/pv`, `AGCRemoteRole`, `MainRemote`, `CrashSignal`,
  `InspectPlayerFromHumanoidDescription`, `AvatarPoseAudit`, `AudioCacheProbe`,
  `CameraWarmStart`, `GuiDiffSampler`, `TextureBudgetScan`, `FrameQueueMirror`.

## Limite honesto
Recuperamos o bytecode e suas **constantes-string** de forma totalmente estática. A
**lógica** completa (o que a VM faz instrução a instrução) exigiria o leitor/semântica
da VM — e `t[30]` (o leitor) é um buraco do decompilador (`structuring failed for
function 268`), irrecuperável deste artefato. Para as *strings*, porém, isso não é
necessário: elas foram resolvidas apenas com este arquivo.

## Reproduzir
```
python3 -I tools/decode2.py <ast.json> gamingchairac.unflat.lua   # grava /tmp/pool.bin
# depois varrer /tmp/pool.bin por [len][bytes] -> gamingchairac.strings.txt
```
(A AST vem de `luau-ast gamingchairac.unflat.lua`, após o fix do cabeçalho `--[==[`.)
