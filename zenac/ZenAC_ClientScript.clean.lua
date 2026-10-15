-- Script Path: game:GetService("CoreGui").stuff.ZenAC.Client.Modules.ClientScript
-- Took 0.74s to decompile.
-- Executor: Volt (1.3.14.1)

local char_upv_1 = string.char
local byte_upv_1 = string.byte
local bxor_upv_1 = bit32.bxor
local u1 = function(a1, a2)
    local v1 = ""
    for n_1 = 247, (#a1 - 1) + 247 do
        v1 = v1 .. char_upv_1(bxor_upv_1(byte_upv_1(a1, (n_1 - 247) + 1), byte_upv_1(a2, ((n_1 - 247) % #a2) + 1)))
    end
    return v1
end
return (function(a1, ...)
    local u2 = game.GetService(game, "Players")
    local u3 = game.GetService(game, "RunService")
    local u4 = game.GetService(game, "Workspace")
    local function n_(a2)
        return a1[a2 - 2075]
    end
    local u5 = game.GetService(game, "Lighting")
    local u6 = game.GetService(game, "ContentProvider")
    local u7 = game.GetService(game, "Chat")
    local u8 = game.GetService(game, "LogService")
    local u9 = game.GetService(game, "UserInputService")
    local tbl_upv_1 = {}
    tbl_upv_1[Enum.HumanoidStateType.Jumping] = true
    tbl_upv_1[Enum.HumanoidStateType.Freefall] = true
    tbl_upv_1[Enum.HumanoidStateType.Swimming] = true
    tbl_upv_1[Enum.HumanoidStateType.Climbing] = true
    tbl_upv_1[Enum.HumanoidStateType.GettingUp] = true
    tbl_upv_1[Enum.HumanoidStateType.FallingDown] = true
    tbl_upv_1[Enum.HumanoidStateType.PlatformStanding] = true
    local tbl_upv_2 = {Vector3.new(0, 0, 0), Vector3.new(1.2, 0, 0), Vector3.new(-1.2, 0, 0), Vector3.new(0, 0, 1.2), Vector3.new(0, 0, -1.2)}
    RaycastParams.new().FilterType = Enum.RaycastFilterType.Exclude
    RaycastParams.new().FilterType = Enum.RaycastFilterType.Exclude
    RaycastParams.new().FilterType = Enum.RaycastFilterType.Exclude
    local u10 = RaycastParams.new()
    u10.FilterType = Enum.RaycastFilterType.Exclude
    local u11 = RaycastParams.new()
    u11.FilterType = Enum.RaycastFilterType.Exclude
    local u12 = RaycastParams.new()
    u12.FilterType = Enum.RaycastFilterType.Exclude
    local tbl_upv_3 = nil
    local tbl_upv_4 = {}
    tbl_upv_4.__index = tbl_upv_4
    tbl_upv_4._report = function(a3, a4)
        if not a3._reportFunc then
            return
        end
        a3._reportFunc(a4)
    end
    local function Bd(a5)
        return a5:FindFirstChildOfClass("Humanoid")
    end
    local function u_(a6)
        return (function(a7)
            for _, value_1 in a6.GetChildren(a6) do
                local v2 = value_1.IsA(value_1, "Tool")
                if not (v2) then
                    continue
                end
                return true
            end
            local function bd_1(a8)
                return a7[a8 - 9993]
            end
            return false
        end)({[-10110] = false})
    end
    local function Ad(a9, a10)
        return (function(a11)
            local v3 = RaycastParams.new()
            v3.FilterType = Enum.RaycastFilterType.Exclude
            local function t__1(a12)
                return a11[a12 + -1667]
            end
            v3.FilterDescendantsInstances = {a10}
            local v4 = workspace.Raycast(workspace, a9.Position, a9.CFrame.LookVector * 1.5, v3)
            if v4 and v4.Instance then
                local Instance_1 = v4.Instance
                local v5 = Instance_1.IsA(Instance_1, "TrussPart")
                if not (v5) then
                    local v6 = Instance_1.Name.lower(Instance_1.Name).find(Instance_1.Name.lower(Instance_1.Name), "ladder")
                    if not (v6) then
                        if math.abs(v4.Normal.Y) < 0.1 then
                            return true
                        end
                        return false
                    end
                end
                return t__1(24591)
            end
            return false
        end)({[22924] = true})
    end
    local function ne(a13, a14, a15)
        return (function(a16)
            local function wf_1(a17)
                return a16[a17 + 10556]
            end
            if a15.FloorMaterial == Enum.Material.Air then
                for _, value_2 in tbl_upv_2 do
                    if not (u4.Raycast(u4, a13.Position + value_2, Vector3.new(0, -4.8, 0), a14)) then
                        continue
                    end
                    return true
                end
                return false
            end
            return true
        end)({[-2979] = true})
    end
    local function Ah(a18)
        local v7 = 0
        for _, value_3 in a18 do
            v7 = v7 + value_3
        end
        return v7 / #a18
    end
    local function va(a19, a20, a21)
        return (function(a22)
            local function ze_1(a23)
                return a22[a23 - -4395]
            end
            if Ad(a19, a20) and math.abs(a19.AssemblyLinearVelocity.Y) > 0.1 then
                return workspace
            end
            local v8 = RaycastParams.new()
            v8.FilterType = Enum.RaycastFilterType.Exclude
            v8.FilterDescendantsInstances = {a20}
            local v9 = nil
            for _, value_4 in ipairs({Vector3.new(0, 0, 0), Vector3.new(0.8, 0, 0), Vector3.new(-0.8, 0, 0), Vector3.new(0, 0, 0.8), Vector3.new(0, 0, -0.8)}) do
                local v10 = workspace.Raycast(workspace, a19.Position + value_4, Vector3.new(ze_1(-32366), -3.8, 0), v8)
                if not (v10) or not (v10.Instance) then
                    continue
                end
                v9 = v10.Instance
                local v11 = v10.Normal.Y > 0.5
                if v9.IsDescendantOf(v9, a20) or not (v9.CanCollide) or not (v11) then
                    continue
                end
                return v9
            end
            return nil
        end)({[-27971] = 0})
    end
    local function ch(a24)
        local v12 = a24:FindFirstChild("HumanoidRootPart") or (a24:FindFirstChild("Torso"))
        return v12
    end
    local function yh(a25)
        return (function(a26)
            local success_1, v13 = pcall(
                function()
                    return (function(a27)
                        local v14 = a25 - Vector3.new(2, 2, 2)
                        local function hb_1(a28)
                            return a27[a28 - 17836]
                        end
                        local v15 = a25 + Vector3.new(2, 2, 2)
                        return u4.Terrain.ReadVoxels(u4.Terrain, Region3.new(v14, v15).ExpandToGrid(Region3.new(v14, v15), 4), 4)
                    end)({[-10639] = 2})
                end
            )
            local function Kg_1(a29)
                return a26[a29 + -15695]
            end
            if success_1 then
                for n_2 = 85, #v13 + 84 do
                    for n_3 = Kg_1(9455), #v13[n_2 - 84] do
                        for n_4 = 131, #v13[n_2 - 84][n_3] + 130 do
                            if v13[n_2 - 84][n_3][n_4 - 130] ~= Enum.Material.Water then
                                continue
                            end
                            return true, true
                        end
                    end
                end
                return false, true
            end
            return true, false
        end)({[-6240] = 1})
    end
    tbl_upv_4._startLoop = function(a30, a31, a32)
        return (function(a33)
            local u13 = ch(a32)
            if not u13 then
                return
            end
            local tbl_upv_5 = {violationBuf = 0, swimGrace = 0, lastJumpTime = 0, jumpDebounce = false, noclipTick = 0, floatTime = 0, jumpCount = 0, lastSeatedTime = 0, climb = 0, velHistIdx = 1, lastVelY = 0, spinCount = 0, jumpGrace = 0, flyViolations = 0}
            tbl_upv_5.lastPos = u13.Position
            tbl_upv_5.lastCFrame = u13.CFrame
            tbl_upv_5.lastRotation = u13.CFrame.LookVector
            local function Oe(a34)
                return a33[a34 + -26590]
            end
            tbl_upv_5.airTime = Oe(49387)
            tbl_upv_5.velHistory = table.create(8, 0)
            tbl_upv_5.obstructionTime = Oe(43494)
            u11.FilterDescendantsInstances = {a32}
            u10.FilterDescendantsInstances = {a32}
            tbl_upv_3 = {a32}
            u3.Heartbeat.Connect(
                u3.Heartbeat,
                function(a35)
                    local v16 = function(a36)
                        local v41
                        local function a__1(a37)
                            return a36[a37 + 1051]
                        end
                        if a31.Health <= 0 or not u13.Parent then
                            return
                        end
                        local _settings_1 = a30._settings
                        if not _settings_1 or not _settings_1.CharacterService then
                            return
                        end
                        local MaxWalkSpeed_1 = _settings_1.CharacterService.MaxWalkSpeed
                        local MaxJumpHeight_1 = _settings_1.CharacterService.MaxJumpHeight
                        local MaxJumpPower_1 = _settings_1.CharacterService.MaxJumpPower
                        local MaxHealth_1 = _settings_1.CharacterService.MaxHealth
                        local MaxHipHeight_1 = _settings_1.CharacterService.MaxHipHeight
                        local MaxSlopeHeight_1 = _settings_1.CharacterService.MaxSlopeHeight
                        if MaxWalkSpeed_1 < a31.WalkSpeed and not (_settings_1.DisableSpeedCheck) then
                            a30._report(a30, "Tampering AC-C detected")
                            a31.WalkSpeed = MaxWalkSpeed_1
                        end
                        if MaxJumpHeight_1 < a31.JumpHeight then
                            a30._report(a30, "Tampering AC-C detected")
                            a31.JumpHeight = MaxJumpHeight_1
                        end
                        if MaxJumpPower_1 < a31.JumpPower then
                            a30._report(a30, "Tampering AC-C detected")
                            a31.JumpPower = MaxJumpPower_1
                        end
                        if MaxHealth_1 < a31.MaxHealth then
                            a30._report(a30, "Tampering AC-C detected")
                            a31.MaxHealth = MaxHealth_1
                        end
                        if MaxHipHeight_1 < a31.HipHeight then
                            a30._report(a30, "Tampering AC-C detected")
                            a31.HipHeight = MaxHipHeight_1
                        end
                        if MaxSlopeHeight_1 < a31.MaxSlopeAngle then
                            a30._report(a30, "Tampering AC-C detected")
                            a31.MaxSlopeAngle = MaxSlopeHeight_1
                        end
                        if (1 / a35 < 15) then
                            return
                        end
                        if a31.SeatPart then
                            tbl_upv_5.lastPos = u13.Position
                        else
                            a35 = math.clamp(a35, 0.008333333333333333, 0.05)
                            local v17 = u13.Position
                            local v18 = v17 - tbl_upv_5.lastPos
                            local Magnitude_1 = v18.Magnitude
                            local AssemblyLinearVelocity_1 = u13.AssemblyLinearVelocity
                            local v19 = ne(u13, u10, a31)
                            local v20 = a31.GetState(a31)
                            local CurrentCamera_1 = workspace.CurrentCamera
                            local v21 = u4.Raycast(u4, u13.Position, Vector3.new(0, -5, 0), u11)
                            local v22 = a31.WalkSpeed + 25 < Vector2.new(AssemblyLinearVelocity_1.X, AssemblyLinearVelocity_1.Z).Magnitude
                            tbl_upv_5.velHistory[tbl_upv_5.velHistIdx] = AssemblyLinearVelocity_1.Y
                            tbl_upv_5.velHistIdx = (tbl_upv_5.velHistIdx % 8) + 1
                            local Position_1 = u13.Position
                            local v23 = os.clock()
                            if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                tbl_upv_5.jumpGrace = 0.35
                            else
                                tbl_upv_5.jumpGrace = math.max(tbl_upv_5.jumpGrace - a35, 0)
                            end
                            local Magnitude_2 = Vector2.new(v17.X - tbl_upv_5.lastPos.X, v17.Z - tbl_upv_5.lastPos.Z).Magnitude
                            local v24 = Magnitude_2 / a35
                            local WalkSpeed_1 = a31.WalkSpeed
                            local v25 = false
                            local v26 = RaycastParams.new()
                            v26.FilterType = Enum.RaycastFilterType.Exclude
                            v26.FilterDescendantsInstances = {a32}
                            local v27 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v26)
                            if v27 and v27.Instance and v27.Instance.CanCollide then
                                v25 = true
                            end
                            if v22 or v25 then
                                tbl_upv_5.spoofBuffer = math.max(0, (tbl_upv_5.spoofBuffer or 0) - 1)
                            elseif not (WalkSpeed_1 + 24 < v24) or _settings_1.DisableSpeedCheck then
                                tbl_upv_5.spoofBuffer = math.max(0, (tbl_upv_5.spoofBuffer or 0) - 0.5)
                            else
                                tbl_upv_5.spoofBuffer = (tbl_upv_5.spoofBuffer or 0) + 1
                            end
                            if tbl_upv_5.spoofBuffer > 35 then
                                a30._report(a30, "Tampering AC-C Detected")
                                tbl_upv_5.spoofBuffer = 0
                            end
                            if Magnitude_2 >= 0.8 and not (_settings_1.DisableSpeedCheck) then
                                if _settings_1.CharacterService.TeleportLimit < Magnitude_2 then
                                    tbl_upv_5.lastPos = v17
                                    tbl_upv_5.lastCFrame = u13.CFrame
                                else
                                    local v28 = math.clamp(Vector2.new(AssemblyLinearVelocity_1.X, AssemblyLinearVelocity_1.Z).Magnitude, 0, 140)
                                    local v29 = ((u_(a32)) and 8) or 0
                                    local v30
                                    if (v19) and (math.abs(AssemblyLinearVelocity_1.Y) > 1.5) then
                                        v30 = 10
                                    else
                                        v30 = 0
                                    end
                                    local v31 = math.max(a31.WalkSpeed, v28) * a35
                                    if ((((v31 + ((v19 and 12) or 22) + (((tbl_upv_5.jumpGrace > 0) and 14) or 0)) + v29) + 5) + v30 < Magnitude_2) and (tbl_upv_5.jumpGrace <= 0) then
                                        tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                    else
                                        tbl_upv_5.violationBuf = math.max(tbl_upv_5.violationBuf - 0.5, 0)
                                    end
                                    if tbl_upv_5.violationBuf >= 4 then
                                        a30._report(a30, "Tampering AC-C3 detected")
                                        u13.CFrame = tbl_upv_5.lastCFrame
                                        u13.AssemblyLinearVelocity = Vector3.zero
                                        tbl_upv_5.violationBuf = 0
                                    end
                                end
                            end
                            local v32, v33 = nil, nil
                            if not (_settings_1.WorldService.DisableSizeCheck) then
                                v32 = u13.Size
                                v33 = _settings_1.WorldService.MaxRootSize or 5
                                if v33 < v32.X or v33 < v32.Y or v33 < v32.Z then
                                    a30._report(a30, "Tampering AC-I detected")
                                    u13.Size = Vector3.new(2, 2, 1)
                                end
                            end
                            if not (_settings_1.PlayerService.DisableCamFov) then
                                if _settings_1.PlayerService.MaxFov < CurrentCamera_1.FieldOfView then
                                    a30._report(a30, "Tampering AC-V detected")
                                    CurrentCamera_1.FieldOfView = _settings_1.PlayerService.MaxFov
                                end
                                if (CurrentCamera_1.CFrame.Position - u13.Position).Magnitude > 500 then
                                    a30._report(a30, "Tampering AC-V0 detected")
                                end
                            end
                            local v34 = nil
                            if not (_settings_1.CharacterService.DisableCFrameCheck) then
                                v34 = _settings_1.CharacterService.MaxCFrameSize
                                if v34 < math.abs(v17.X) or v34 < math.abs(v17.Y) or v34 < math.abs(v17.Z) then
                                    a30._report(a30, "Tampering AC-I detected")
                                    u13.CFrame = tbl_upv_5.lastSafeCFrame or CFrame.new(0, 50, 0)
                                end
                            end
                            local v36 = tbl_upv_1[v20] or (tbl_upv_5.jumpGrace > 0)
                            if v19 or v36 then
                                tbl_upv_5.airTime = 0
                                tbl_upv_5.floatTime = 0
                                tbl_upv_5.flyViolations = math.max(tbl_upv_5.flyViolations - 1, 0)
                            else
                                local v37 = nil
                                if _settings_1.CharacterService.DisableFlyCheck then
                                    tbl_upv_5.airTime = 0
                                    tbl_upv_5.floatTime = 0
                                    tbl_upv_5.flyViolations = math.max(tbl_upv_5.flyViolations - 1, 0)
                                else
                                    tbl_upv_5.airTime = tbl_upv_5.airTime + a35
                                    if math.abs(Ah(tbl_upv_5.velHistory)) < 0.08 then
                                        tbl_upv_5.floatTime = tbl_upv_5.floatTime + a35
                                        if tbl_upv_5.floatTime >= 1.6 then
                                            a30._report(a30, "Tampering AC-F detected")
                                            tbl_upv_5.floatTime = 0
                                        end
                                    else
                                        tbl_upv_5.floatTime = math.max(tbl_upv_5.floatTime - (a35 * 2), 0)
                                    end
                                    local v38 = AssemblyLinearVelocity_1.Magnitude * a35
                                    v37 = (v17 - tbl_upv_5.lastPos).Magnitude
                                    if (0.8 < v37) and (v38 < v37 * 0.55) then
                                        tbl_upv_5.flyViolations = tbl_upv_5.flyViolations + 1
                                        if tbl_upv_5.flyViolations >= 5 then
                                            a30._report(a30, "Tampering AC-F1 detected")
                                            u13.CFrame = tbl_upv_5.lastCFrame
                                            u13.AssemblyLinearVelocity = Vector3.zero
                                            tbl_upv_5.flyViolations = 0
                                        end
                                    else
                                        tbl_upv_5.flyViolations = math.max(tbl_upv_5.flyViolations - 1, 0)
                                    end
                                    if _settings_1.CharacterService.AirTime < tbl_upv_5.airTime then
                                        a30._report(a30, "Tampering AC-C detected")
                                        u13.AssemblyLinearVelocity = Vector3.new(0, -60, 0)
                                        tbl_upv_5.airTime = 0
                                    end
                                end
                            end
                            if Magnitude_1 > 0.05 and Magnitude_1 < 70 then
                                local v39, v40 = nil, nil
                                if _settings_1.CharacterService.DisableNoclipCheck then
                                    if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                        a30._report(a30, "Tampering AC-C detected")
                                        u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                        u13.AssemblyLinearVelocity = Vector3.zero
                                    end
                                    v41 = u13.CFrame.LookVector
                                    if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                        if _settings_1.CharacterService.DisableVelocityCheck then
                                            tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                        else
                                            tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                            if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                a30._report(a30, "Tampering AC-C detected")
                                                tbl_upv_5.spinCount = 0
                                            end
                                        end
                                    else
                                        tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                    end
                                    local v42 = va(u13, a32, a31) ~= nil
                                    local v43 = false
                                    local v44 = RaycastParams.new()
                                    v44.FilterType = Enum.RaycastFilterType.Exclude
                                    v44.FilterDescendantsInstances = {a32}
                                    local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                    if v45 and v45.Instance then
                                        local v80 = ((v45.Instance.CanCollide) and true) or v43
                                    end
                                    if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                        if not (tbl_upv_5.jumpDebounce) then
                                            tbl_upv_5.jumpDebounce = true
                                            tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                            tbl_upv_5.lastJumpTime = v23
                                            if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                a30._report(a30, "Tampering AC-C1 Detected")
                                                u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                u13.AssemblyLinearVelocity = Vector3.zero
                                            end
                                        end
                                    else
                                        tbl_upv_5.jumpDebounce = false
                                    end
                                    if v42 or v43 then
                                        tbl_upv_5.jumpCount = 0
                                        if v42 then
                                            tbl_upv_5.lastSafeCFrame = u13.CFrame
                                        end
                                    elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                        tbl_upv_5.jumpCount = 0
                                    end
                                    if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                        tbl_upv_5.climb = 0
                                    elseif a31.MoveDirection.Magnitude > 0.2 then
                                        local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                        local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                        local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                        if v46 then
                                            tbl_upv_5.climb = 0
                                        else
                                            tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                            if tbl_upv_5.climb > 0.5 then
                                                a30._report(a30, "Tampering AC-C3 detected")
                                                a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                tbl_upv_5.climb = 0
                                            end
                                        end
                                    end
                                    if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                        tbl_upv_5.swimGrace = 0
                                    else
                                        local v47, v48 = yh(v17)
                                        local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                        if v48 and v50 then
                                            if v47 or v49 then
                                                tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                            else
                                                tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                if tbl_upv_5.swimGrace >= 2 then
                                                    a30._report(a30, "Tampering AC-C55 detected")
                                                    a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                    tbl_upv_5.swimGrace = 0
                                                end
                                            end
                                        else
                                            tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                        end
                                    end
                                    if v21 and v21.Instance then
                                        local v51 = nil
                                        if not (_settings_1.CharacterService.DisableFlyCheck) then
                                            v51 = v21.Instance
                                            if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                                tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                if tbl_upv_5.violationBuf > 5 then
                                                    a30._report(a30, "Tampering AC-F4 detected")
                                                    v51.Destroy(v51)
                                                end
                                            end
                                        end
                                    end
                                    tbl_upv_5.lastRotation = v41
                                    tbl_upv_5.lastPos = v17
                                    tbl_upv_5.lastCFrame = u13.CFrame
                                    tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                    tbl_upv_5.lastY = v17.Y
                                else
                                    v41 = false
                                    local v52 = RaycastParams.new()
                                    v52.FilterType = Enum.RaycastFilterType.Exclude
                                    v52.FilterDescendantsInstances = {a32}
                                    v39 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 5, 0), v52)
                                    if v39 and v39.Instance and v39.Instance.CanCollide then
                                        v41 = true
                                    end
                                    u12.FilterDescendantsInstances = tbl_upv_3
                                    v52 = workspace.Blockcast(workspace, u13.CFrame * CFrame.new(0, 1, 0), Vector3.new(1.8, 0.1, 1.8), Vector3.new(0, -3.5, 0), u12)
                                    local v53 = (v52) and v52.Instance or a31.FloorMaterial == Enum.Material.Air
                                    if not (v53) then
                                        tbl_upv_5.lastSafeCFrame = u13.CFrame
                                    end
                                    local v54 = ((Magnitude_1 > 12) and 0.5) or (0.05)
                                    v40 = workspace.Blockcast(workspace, CFrame.new(Position_1), Vector3.new(0.5, 0.5, 0.5), v18, u12)
                                    if (v40) and (v40.Instance) then
                                        local Instance_2 = v40.Instance
                                        local v55 = Instance_2.IsA(Instance_2, "Terrain") and (v40.Material ~= Enum.Material.Water)
                                        local v56 = Instance_2.IsA(Instance_2, "Seat")
                                        if not (v56) then
                                            v56 = Instance_2.IsA(Instance_2, "VehicleSeat")
                                            if not v56 then
                                                if Instance_2.Parent then
                                                    v56 = Instance_2.Parent.IsA(Instance_2.Parent, "Seat")
                                                    v56 = v56 or Instance_2.Parent.IsA(Instance_2.Parent, "VehicleSeat") or Instance_2.FindFirstAncestorOfClass(Instance_2, "Seat") or Instance_2.FindFirstAncestorOfClass(Instance_2, "VehicleSeat")
                                                else
                                                    v56 = Instance_2.FindFirstAncestorOfClass(Instance_2, "Seat") or (Instance_2.FindFirstAncestorOfClass(Instance_2, "VehicleSeat"))
                                                end
                                            end
                                        end
                                        if Instance_2.IsA(Instance_2, "BasePart") then
                                            if Instance_2.CanCollide and Instance_2.Transparency < 1 then
                                                if Instance_2.IsA(Instance_2, "TrussPart") or v56 or Instance_2.IsDescendantOf(Instance_2, a32) or yh(v17) then
                                                    tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.15)
                                                else
                                                    local v57 = true
                                                    if v53 and Magnitude_1 - v54 < v40.Distance then
                                                        v57 = false
                                                    end
                                                    if v40.Distance <= Magnitude_1 and v57 then
                                                        local v58 = ((v40.Normal) and (v40.Normal.Y)) or 0
                                                        local v59
                                                        if v58 < -0.35 then
                                                            v59 = true
                                                        else
                                                            v59 = false
                                                        end
                                                        local v60 = v58 > 0.4
                                                        local v61 = v19 and (AssemblyLinearVelocity_1.Y > 0.4)
                                                        if v41 or v59 or v60 or v61 then
                                                            tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.2)
                                                        else
                                                            local v62 = ((Magnitude_1 > 15) and 0.02) or (0.05)
                                                            tbl_upv_5.obstructionTime = tbl_upv_5.obstructionTime + v62
                                                            if (((Magnitude_1 > 15) and 0.5) or 0.4) <= tbl_upv_5.obstructionTime and tbl_upv_5.lastSafeCFrame then
                                                                u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                                u13.AssemblyLinearVelocity = Vector3.zero
                                                                local Position_2 = tbl_upv_5.lastSafeCFrame.Position
                                                                tbl_upv_5.obstructionTime = 0
                                                                a30._report(a30, "Tampering AC-C60 detected")
                                                                v17 = Position_2
                                                            end
                                                        end
                                                    end
                                                end
                                            else
                                                tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.15)
                                            end
                                        elseif v55 and Instance_2.CanCollide and Instance_2.Transparency < 1 then
                                            if Instance_2.IsA(Instance_2, "TrussPart") or v56 or Instance_2.IsDescendantOf(Instance_2, a32) or yh(v17) then
                                                tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.15)
                                            else
                                                local v57 = true
                                                if v53 and Magnitude_1 - v54 < v40.Distance then
                                                    v57 = false
                                                end
                                                if v40.Distance <= Magnitude_1 and v57 then
                                                    local v58 = ((v40.Normal) and (v40.Normal.Y)) or 0
                                                    local v59
                                                    if v58 < -0.35 then
                                                        v59 = true
                                                    else
                                                        v59 = false
                                                    end
                                                    local v60 = v58 > 0.4
                                                    local v61 = v19 and (AssemblyLinearVelocity_1.Y > 0.4)
                                                    if v41 or v59 or v60 or v61 then
                                                        tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.2)
                                                    else
                                                        local v62 = ((Magnitude_1 > 15) and 0.02) or (0.05)
                                                        tbl_upv_5.obstructionTime = tbl_upv_5.obstructionTime + v62
                                                        if (((Magnitude_1 > 15) and 0.5) or 0.4) <= tbl_upv_5.obstructionTime and tbl_upv_5.lastSafeCFrame then
                                                            u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                            u13.AssemblyLinearVelocity = Vector3.zero
                                                            local Position_2 = tbl_upv_5.lastSafeCFrame.Position
                                                            tbl_upv_5.obstructionTime = 0
                                                            a30._report(a30, "Tampering AC-C60 detected")
                                                            v17 = Position_2
                                                        end
                                                    end
                                                end
                                            end
                                        else
                                            tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.15)
                                        end
                                    else
                                        tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.15)
                                    end
                                    if Magnitude_1 > 0.02 then
                                        local v63 = nil
                                        if Magnitude_1 < 15 then
                                            local tbl_6 = {a32, workspace.CurrentCamera}
                                            for _, value_5 in pairs(u2.GetPlayers(u2)) do
                                                if value_5.Character then
                                                    table.insert(tbl_6, value_5.Character)
                                                end
                                            end
                                            local v64 = RaycastParams.new()
                                            v64.FilterType = Enum.RaycastFilterType.Exclude
                                            v64.FilterDescendantsInstances = tbl_6
                                            local v65 = false
                                            local v66 = RaycastParams.new()
                                            v66.FilterType = Enum.RaycastFilterType.Exclude
                                            v66.FilterDescendantsInstances = {a32}
                                            v63 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v66)
                                            local v67
                                            if v63 and v63.Instance and v63.Instance.CanCollide then
                                                v67 = true
                                            else
                                                v67 = v65
                                            end
                                            local Y_1 = u13.AssemblyLinearVelocity.Y
                                            tbl_upv_5.lastYVelocity = tbl_upv_5.lastYVelocity or Y_1
                                            local v68 = (tbl_upv_5.lastYVelocity > 2) and (Y_1 < -2)
                                            tbl_upv_5.lastYVelocity = Y_1
                                            if not (v67) then
                                                local v69 = nil
                                                if not (v68) then
                                                    local v70 = (v53 and (Vector3.new(0.5, (v67 and 1.2) or 1.8, 0.5))) or (Vector3.new(0.9, 1.8, 0.9))
                                                    local v71 = CFrame.new(Position_1)
                                                    local v72 = nil
                                                    if v53 and Magnitude_1 > 5 then
                                                        v69 = (v67 and 0.2) or 0.8
                                                        v71, v72 = u13.CFrame * CFrame.new(-v18.Unit * v69), v18.Unit * v69
                                                    end
                                                    v69 = workspace.Blockcast(workspace, v71, v70, v72, v64)
                                                    if v69 and v69.Instance then
                                                        local Instance_3 = v69.Instance
                                                        local v73 = Instance_3.IsA(Instance_3, "Terrain") and (v69.Material ~= Enum.Material.Water)
                                                        if not (Instance_3.Parent.FindFirstChild(Instance_3.Parent, "Humanoid")) and not (Instance_3.Parent.Parent.FindFirstChild(Instance_3.Parent.Parent, "Humanoid")) then
                                                            local v74 = Instance_3.IsA(Instance_3, "Seat")
                                                            if not (v74) then
                                                                v74 = Instance_3.IsA(Instance_3, "VehicleSeat")
                                                                if not v74 then
                                                                    if Instance_3.Parent then
                                                                        v74 = Instance_3.Parent.IsA(Instance_3.Parent, "Seat")
                                                                        v74 = v74 or Instance_3.Parent.IsA(Instance_3.Parent, "VehicleSeat") or Instance_3.FindFirstAncestorOfClass(Instance_3, "Seat") or Instance_3.FindFirstAncestorOfClass(Instance_3, "VehicleSeat")
                                                                    else
                                                                        v74 = Instance_3.FindFirstAncestorOfClass(Instance_3, "Seat") or (Instance_3.FindFirstAncestorOfClass(Instance_3, "VehicleSeat"))
                                                                    end
                                                                end
                                                            end
                                                            if (Instance_3.CanCollide or v73) and Instance_3.Transparency < 1 and not (Instance_3.IsA(Instance_3, "TrussPart")) and not (v74) and not (Instance_3.IsDescendantOf(Instance_3, a32)) then
                                                                if v69.Distance <= ((v53 and (v72.Magnitude + 0.1)) or (Magnitude_1 + 0.35)) then
                                                                    local v76 = nil
                                                                    if Instance_3.IsA(Instance_3, "Terrain") and v69.Material == Enum.Material.Water or not (tbl_upv_5.lastSafeCFrame) then
                                                                        if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                                                            a30._report(a30, "Tampering AC-C detected")
                                                                            u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                                                            u13.AssemblyLinearVelocity = Vector3.zero
                                                                        end
                                                                        v41 = u13.CFrame.LookVector
                                                                        if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                                                            if _settings_1.CharacterService.DisableVelocityCheck then
                                                                                tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                                            else
                                                                                tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                                                                if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                                                    a30._report(a30, "Tampering AC-C detected")
                                                                                    tbl_upv_5.spinCount = 0
                                                                                end
                                                                            end
                                                                        else
                                                                            tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                                        end
                                                                        local v42 = va(u13, a32, a31) ~= nil
                                                                        local v43 = false
                                                                        local v44 = RaycastParams.new()
                                                                        v44.FilterType = Enum.RaycastFilterType.Exclude
                                                                        v44.FilterDescendantsInstances = {a32}
                                                                        local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                                                        if v45 and v45.Instance then
                                                                            local v80 = ((v45.Instance.CanCollide) and true) or v43
                                                                        end
                                                                        if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                                                            if not (tbl_upv_5.jumpDebounce) then
                                                                                tbl_upv_5.jumpDebounce = true
                                                                                tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                                                                tbl_upv_5.lastJumpTime = v23
                                                                                if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                                                    a30._report(a30, "Tampering AC-C1 Detected")
                                                                                    u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                                                    u13.AssemblyLinearVelocity = Vector3.zero
                                                                                end
                                                                            end
                                                                        else
                                                                            tbl_upv_5.jumpDebounce = false
                                                                        end
                                                                        if v42 or v43 then
                                                                            tbl_upv_5.jumpCount = 0
                                                                            if v42 then
                                                                                tbl_upv_5.lastSafeCFrame = u13.CFrame
                                                                            end
                                                                        elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                                                            tbl_upv_5.jumpCount = 0
                                                                        end
                                                                        if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                                                            tbl_upv_5.climb = 0
                                                                        elseif a31.MoveDirection.Magnitude > 0.2 then
                                                                            local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                                                            local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                                                            local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                                                            if v46 then
                                                                                tbl_upv_5.climb = 0
                                                                            else
                                                                                tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                                                                if tbl_upv_5.climb > 0.5 then
                                                                                    a30._report(a30, "Tampering AC-C3 detected")
                                                                                    a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                                                    tbl_upv_5.climb = 0
                                                                                end
                                                                            end
                                                                        end
                                                                        if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                                                            tbl_upv_5.swimGrace = 0
                                                                        else
                                                                            local v47, v48 = yh(v17)
                                                                            local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                                                            if v48 and v50 then
                                                                                if v47 or v49 then
                                                                                    tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                                                else
                                                                                    tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                                                    if tbl_upv_5.swimGrace >= 2 then
                                                                                        a30._report(a30, "Tampering AC-C55 detected")
                                                                                        a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                                                        tbl_upv_5.swimGrace = 0
                                                                                    end
                                                                                end
                                                                            else
                                                                                tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                                            end
                                                                        end
                                                                        if v21 and v21.Instance then
                                                                            if not (_settings_1.CharacterService.DisableFlyCheck) then
                                                                                v76 = v21.Instance
                                                                                if v76.IsDescendantOf(v76, a32) and v76.Anchored then
                                                                                    tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                                                    if tbl_upv_5.violationBuf > 5 then
                                                                                        a30._report(a30, "Tampering AC-F4 detected")
                                                                                        v76.Destroy(v76)
                                                                                    end
                                                                                end
                                                                            end
                                                                        end
                                                                        tbl_upv_5.lastRotation = v41
                                                                        tbl_upv_5.lastPos = v17
                                                                        tbl_upv_5.lastCFrame = u13.CFrame
                                                                        tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                                                        tbl_upv_5.lastY = v17.Y
                                                                        return
                                                                    end
                                                                    local v75 = (v69.Normal) and (v69.Normal.Y) or 0
                                                                    if v75 < -0.35 then
                                                                        v76 = true
                                                                    else
                                                                        v76 = false
                                                                    end
                                                                    local v77 = v75 > 0.45
                                                                    local v78 = v19 and (AssemblyLinearVelocity_1.Y > 0.4)
                                                                    if v76 or v77 or v78 or v41 then
                                                                        local v79 = tbl_upv_5.c61Threshold or (0)
                                                                        tbl_upv_5.c61Threshold = math.max(0, v79 - 1)
                                                                    else
                                                                        tbl_upv_5.c61Threshold = (tbl_upv_5.c61Threshold or 0) + 1
                                                                        if ((v67 and 7) or 5) <= tbl_upv_5.c61Threshold then
                                                                            tbl_upv_5.c61Threshold = 0
                                                                            a30._report(a30, "Tampering AC-C detected")
                                                                            u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                                            v17 = tbl_upv_5.lastSafeCFrame.Position
                                                                        end
                                                                    end
                                                                end
                                                                if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                                                    a30._report(a30, "Tampering AC-C detected")
                                                                    u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                                                    u13.AssemblyLinearVelocity = Vector3.zero
                                                                end
                                                                v41 = u13.CFrame.LookVector
                                                                if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                                                    if _settings_1.CharacterService.DisableVelocityCheck then
                                                                        tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                                    else
                                                                        tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                                                        if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                                            a30._report(a30, "Tampering AC-C detected")
                                                                            tbl_upv_5.spinCount = 0
                                                                        end
                                                                    end
                                                                else
                                                                    tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                                end
                                                                local v42 = va(u13, a32, a31) ~= nil
                                                                local v43 = false
                                                                local v44 = RaycastParams.new()
                                                                v44.FilterType = Enum.RaycastFilterType.Exclude
                                                                v44.FilterDescendantsInstances = {a32}
                                                                local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                                                if v45 and v45.Instance then
                                                                    local v80 = ((v45.Instance.CanCollide) and true) or v43
                                                                end
                                                                if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                                                    if not (tbl_upv_5.jumpDebounce) then
                                                                        tbl_upv_5.jumpDebounce = true
                                                                        tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                                                        tbl_upv_5.lastJumpTime = v23
                                                                        if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                                            a30._report(a30, "Tampering AC-C1 Detected")
                                                                            u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                                            u13.AssemblyLinearVelocity = Vector3.zero
                                                                        end
                                                                    end
                                                                else
                                                                    tbl_upv_5.jumpDebounce = false
                                                                end
                                                                if v42 or v43 then
                                                                    tbl_upv_5.jumpCount = 0
                                                                    if v42 then
                                                                        tbl_upv_5.lastSafeCFrame = u13.CFrame
                                                                    end
                                                                elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                                                    tbl_upv_5.jumpCount = 0
                                                                end
                                                                if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                                                    tbl_upv_5.climb = 0
                                                                elseif a31.MoveDirection.Magnitude > 0.2 then
                                                                    local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                                                    local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                                                    local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                                                    if v46 then
                                                                        tbl_upv_5.climb = 0
                                                                    else
                                                                        tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                                                        if tbl_upv_5.climb > 0.5 then
                                                                            a30._report(a30, "Tampering AC-C3 detected")
                                                                            a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                                            tbl_upv_5.climb = 0
                                                                        end
                                                                    end
                                                                end
                                                                if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                                                    tbl_upv_5.swimGrace = 0
                                                                else
                                                                    local v47, v48 = yh(v17)
                                                                    local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                                                    if v48 and v50 then
                                                                        if v47 or v49 then
                                                                            tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                                        else
                                                                            tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                                            if tbl_upv_5.swimGrace >= 2 then
                                                                                a30._report(a30, "Tampering AC-C55 detected")
                                                                                a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                                                tbl_upv_5.swimGrace = 0
                                                                            end
                                                                        end
                                                                    else
                                                                        tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                                    end
                                                                end
                                                                if v21 and v21.Instance then
                                                                    local v51 = nil
                                                                    if not (_settings_1.CharacterService.DisableFlyCheck) then
                                                                        v51 = v21.Instance
                                                                        if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                                                            tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                                            if tbl_upv_5.violationBuf > 5 then
                                                                                a30._report(a30, "Tampering AC-F4 detected")
                                                                                v51.Destroy(v51)
                                                                            end
                                                                        end
                                                                    end
                                                                end
                                                                tbl_upv_5.lastRotation = v41
                                                                tbl_upv_5.lastPos = v17
                                                                tbl_upv_5.lastCFrame = u13.CFrame
                                                                tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                                                tbl_upv_5.lastY = v17.Y
                                                                return
                                                            end
                                                            tbl_upv_5.c61Threshold = math.max(0, (tbl_upv_5.c61Threshold or 0) - 1)
                                                            if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                                                a30._report(a30, "Tampering AC-C detected")
                                                                u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                                                u13.AssemblyLinearVelocity = Vector3.zero
                                                            end
                                                            v41 = u13.CFrame.LookVector
                                                            if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                                                if _settings_1.CharacterService.DisableVelocityCheck then
                                                                    tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                                else
                                                                    tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                                                    if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                                        a30._report(a30, "Tampering AC-C detected")
                                                                        tbl_upv_5.spinCount = 0
                                                                    end
                                                                end
                                                            else
                                                                tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                            end
                                                            local v42 = va(u13, a32, a31) ~= nil
                                                            local v43 = false
                                                            local v44 = RaycastParams.new()
                                                            v44.FilterType = Enum.RaycastFilterType.Exclude
                                                            v44.FilterDescendantsInstances = {a32}
                                                            local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                                            if v45 and v45.Instance then
                                                                local v80 = ((v45.Instance.CanCollide) and true) or v43
                                                            end
                                                            if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                                                if not (tbl_upv_5.jumpDebounce) then
                                                                    tbl_upv_5.jumpDebounce = true
                                                                    tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                                                    tbl_upv_5.lastJumpTime = v23
                                                                    if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                                        a30._report(a30, "Tampering AC-C1 Detected")
                                                                        u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                                        u13.AssemblyLinearVelocity = Vector3.zero
                                                                    end
                                                                end
                                                            else
                                                                tbl_upv_5.jumpDebounce = false
                                                            end
                                                            if v42 or v43 then
                                                                tbl_upv_5.jumpCount = 0
                                                                if v42 then
                                                                    tbl_upv_5.lastSafeCFrame = u13.CFrame
                                                                end
                                                            elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                                                tbl_upv_5.jumpCount = 0
                                                            end
                                                            if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                                                tbl_upv_5.climb = 0
                                                            elseif a31.MoveDirection.Magnitude > 0.2 then
                                                                local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                                                local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                                                local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                                                if v46 then
                                                                    tbl_upv_5.climb = 0
                                                                else
                                                                    tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                                                    if tbl_upv_5.climb > 0.5 then
                                                                        a30._report(a30, "Tampering AC-C3 detected")
                                                                        a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                                        tbl_upv_5.climb = 0
                                                                    end
                                                                end
                                                            end
                                                            if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                                                tbl_upv_5.swimGrace = 0
                                                            else
                                                                local v47, v48 = yh(v17)
                                                                local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                                                if v48 and v50 then
                                                                    if v47 or v49 then
                                                                        tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                                    else
                                                                        tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                                        if tbl_upv_5.swimGrace >= 2 then
                                                                            a30._report(a30, "Tampering AC-C55 detected")
                                                                            a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                                            tbl_upv_5.swimGrace = 0
                                                                        end
                                                                    end
                                                                else
                                                                    tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                                end
                                                            end
                                                            if v21 and v21.Instance then
                                                                local v51 = nil
                                                                if not (_settings_1.CharacterService.DisableFlyCheck) then
                                                                    v51 = v21.Instance
                                                                    if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                                                        tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                                        if tbl_upv_5.violationBuf > 5 then
                                                                            a30._report(a30, "Tampering AC-F4 detected")
                                                                            v51.Destroy(v51)
                                                                        end
                                                                    end
                                                                end
                                                            end
                                                            tbl_upv_5.lastRotation = v41
                                                            tbl_upv_5.lastPos = v17
                                                            tbl_upv_5.lastCFrame = u13.CFrame
                                                            tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                                            tbl_upv_5.lastY = v17.Y
                                                            return
                                                        end
                                                        return
                                                    end
                                                    tbl_upv_5.c61Threshold = math.max(0, (tbl_upv_5.c61Threshold or 0) - 1)
                                                    if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                                        a30._report(a30, "Tampering AC-C detected")
                                                        u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                                        u13.AssemblyLinearVelocity = Vector3.zero
                                                    end
                                                    v41 = u13.CFrame.LookVector
                                                    if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                                        if _settings_1.CharacterService.DisableVelocityCheck then
                                                            tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                        else
                                                            tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                                            if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                                a30._report(a30, "Tampering AC-C detected")
                                                                tbl_upv_5.spinCount = 0
                                                            end
                                                        end
                                                    else
                                                        tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                    end
                                                    local v42 = va(u13, a32, a31) ~= nil
                                                    local v43 = false
                                                    local v44 = RaycastParams.new()
                                                    v44.FilterType = Enum.RaycastFilterType.Exclude
                                                    v44.FilterDescendantsInstances = {a32}
                                                    local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                                    if v45 and v45.Instance then
                                                        local v80 = ((v45.Instance.CanCollide) and true) or v43
                                                    end
                                                    if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                                        if not (tbl_upv_5.jumpDebounce) then
                                                            tbl_upv_5.jumpDebounce = true
                                                            tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                                            tbl_upv_5.lastJumpTime = v23
                                                            if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                                a30._report(a30, "Tampering AC-C1 Detected")
                                                                u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                                u13.AssemblyLinearVelocity = Vector3.zero
                                                            end
                                                        end
                                                    else
                                                        tbl_upv_5.jumpDebounce = false
                                                    end
                                                    if v42 or v43 then
                                                        tbl_upv_5.jumpCount = 0
                                                        if v42 then
                                                            tbl_upv_5.lastSafeCFrame = u13.CFrame
                                                        end
                                                    elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                                        tbl_upv_5.jumpCount = 0
                                                    end
                                                    if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                                        tbl_upv_5.climb = 0
                                                    elseif a31.MoveDirection.Magnitude > 0.2 then
                                                        local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                                        local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                                        local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                                        if v46 then
                                                            tbl_upv_5.climb = 0
                                                        else
                                                            tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                                            if tbl_upv_5.climb > 0.5 then
                                                                a30._report(a30, "Tampering AC-C3 detected")
                                                                a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                                tbl_upv_5.climb = 0
                                                            end
                                                        end
                                                    end
                                                    if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                                        tbl_upv_5.swimGrace = 0
                                                    else
                                                        local v47, v48 = yh(v17)
                                                        local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                                        if v48 and v50 then
                                                            if v47 or v49 then
                                                                tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                            else
                                                                tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                                if tbl_upv_5.swimGrace >= 2 then
                                                                    a30._report(a30, "Tampering AC-C55 detected")
                                                                    a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                                    tbl_upv_5.swimGrace = 0
                                                                end
                                                            end
                                                        else
                                                            tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                        end
                                                    end
                                                    if v21 and v21.Instance then
                                                        local v51 = nil
                                                        if not (_settings_1.CharacterService.DisableFlyCheck) then
                                                            v51 = v21.Instance
                                                            if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                                                tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                                if tbl_upv_5.violationBuf > 5 then
                                                                    a30._report(a30, "Tampering AC-F4 detected")
                                                                    v51.Destroy(v51)
                                                                end
                                                            end
                                                        end
                                                    end
                                                    tbl_upv_5.lastRotation = v41
                                                    tbl_upv_5.lastPos = v17
                                                    tbl_upv_5.lastCFrame = u13.CFrame
                                                    tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                                    tbl_upv_5.lastY = v17.Y
                                                    return
                                                end
                                            end
                                            tbl_upv_5.c61Threshold = math.max(0, (tbl_upv_5.c61Threshold or 0) - 2)
                                            tbl_upv_5.obstructionTime = math.max(0, tbl_upv_5.obstructionTime - 0.3)
                                        else
                                            if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                                a30._report(a30, "Tampering AC-C detected")
                                                u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                                u13.AssemblyLinearVelocity = Vector3.zero
                                            end
                                            v41 = u13.CFrame.LookVector
                                            if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                                if _settings_1.CharacterService.DisableVelocityCheck then
                                                    tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                                else
                                                    tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                                    if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                        a30._report(a30, "Tampering AC-C detected")
                                                        tbl_upv_5.spinCount = 0
                                                    end
                                                end
                                            else
                                                tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                            end
                                            local v42 = va(u13, a32, a31) ~= nil
                                            local v43 = false
                                            local v44 = RaycastParams.new()
                                            v44.FilterType = Enum.RaycastFilterType.Exclude
                                            v44.FilterDescendantsInstances = {a32}
                                            local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                            if v45 and v45.Instance then
                                                local v80 = ((v45.Instance.CanCollide) and true) or v43
                                            end
                                            if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                                if not (tbl_upv_5.jumpDebounce) then
                                                    tbl_upv_5.jumpDebounce = true
                                                    tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                                    tbl_upv_5.lastJumpTime = v23
                                                    if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                        a30._report(a30, "Tampering AC-C1 Detected")
                                                        u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                        u13.AssemblyLinearVelocity = Vector3.zero
                                                    end
                                                end
                                            else
                                                tbl_upv_5.jumpDebounce = false
                                            end
                                            if v42 or v43 then
                                                tbl_upv_5.jumpCount = 0
                                                if v42 then
                                                    tbl_upv_5.lastSafeCFrame = u13.CFrame
                                                end
                                            elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                                tbl_upv_5.jumpCount = 0
                                            end
                                            if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                                tbl_upv_5.climb = 0
                                            elseif a31.MoveDirection.Magnitude > 0.2 then
                                                local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                                local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                                local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                                if v46 then
                                                    tbl_upv_5.climb = 0
                                                else
                                                    tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                                    if tbl_upv_5.climb > 0.5 then
                                                        a30._report(a30, "Tampering AC-C3 detected")
                                                        a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                        tbl_upv_5.climb = 0
                                                    end
                                                end
                                            end
                                            if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                                tbl_upv_5.swimGrace = 0
                                            else
                                                local v47, v48 = yh(v17)
                                                local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                                if v48 and v50 then
                                                    if v47 or v49 then
                                                        tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                    else
                                                        tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                        if tbl_upv_5.swimGrace >= 2 then
                                                            a30._report(a30, "Tampering AC-C55 detected")
                                                            a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                            tbl_upv_5.swimGrace = 0
                                                        end
                                                    end
                                                else
                                                    tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                end
                                            end
                                            if v21 and v21.Instance then
                                                local v51 = nil
                                                if not (_settings_1.CharacterService.DisableFlyCheck) then
                                                    v51 = v21.Instance
                                                    if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                                        tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                        if tbl_upv_5.violationBuf > 5 then
                                                            a30._report(a30, "Tampering AC-F4 detected")
                                                            v51.Destroy(v51)
                                                        end
                                                    end
                                                end
                                            end
                                            tbl_upv_5.lastRotation = v41
                                            tbl_upv_5.lastPos = v17
                                            tbl_upv_5.lastCFrame = u13.CFrame
                                            tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                            tbl_upv_5.lastY = v17.Y
                                        end
                                    else
                                        if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                            a30._report(a30, "Tampering AC-C detected")
                                            u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                            u13.AssemblyLinearVelocity = Vector3.zero
                                        end
                                        v41 = u13.CFrame.LookVector
                                        if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, v41), -1, 1)) > 2.6 and a35 < 0.1 then
                                            if _settings_1.CharacterService.DisableVelocityCheck then
                                                tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                            else
                                                tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                                if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                                    a30._report(a30, "Tampering AC-C detected")
                                                    tbl_upv_5.spinCount = 0
                                                end
                                            end
                                        else
                                            tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                        end
                                        local v42 = va(u13, a32, a31) ~= nil
                                        local v43 = false
                                        local v44 = RaycastParams.new()
                                        v44.FilterType = Enum.RaycastFilterType.Exclude
                                        v44.FilterDescendantsInstances = {a32}
                                        local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                        if v45 and v45.Instance then
                                            local v80 = ((v45.Instance.CanCollide) and true) or v43
                                        end
                                        if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                            if not (tbl_upv_5.jumpDebounce) then
                                                tbl_upv_5.jumpDebounce = true
                                                tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                                tbl_upv_5.lastJumpTime = v23
                                                if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                                    a30._report(a30, "Tampering AC-C1 Detected")
                                                    u13.CFrame = tbl_upv_5.lastSafeCFrame
                                                    u13.AssemblyLinearVelocity = Vector3.zero
                                                end
                                            end
                                        else
                                            tbl_upv_5.jumpDebounce = false
                                        end
                                        if v42 or v43 then
                                            tbl_upv_5.jumpCount = 0
                                            if v42 then
                                                tbl_upv_5.lastSafeCFrame = u13.CFrame
                                            end
                                        elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                            tbl_upv_5.jumpCount = 0
                                        end
                                        if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                            tbl_upv_5.climb = 0
                                        elseif a31.MoveDirection.Magnitude > 0.2 then
                                            local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                            local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                            local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                            if v46 then
                                                tbl_upv_5.climb = 0
                                            else
                                                tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                                if tbl_upv_5.climb > 0.5 then
                                                    a30._report(a30, "Tampering AC-C3 detected")
                                                    a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                                    tbl_upv_5.climb = 0
                                                end
                                            end
                                        end
                                        if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                            tbl_upv_5.swimGrace = 0
                                        else
                                            local v47, v48 = yh(v17)
                                            local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                            if v48 and v50 then
                                                if v47 or v49 then
                                                    tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                                else
                                                    tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                                    if tbl_upv_5.swimGrace >= 2 then
                                                        a30._report(a30, "Tampering AC-C55 detected")
                                                        a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                        tbl_upv_5.swimGrace = 0
                                                    end
                                                end
                                            else
                                                tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                            end
                                        end
                                        if v21 and v21.Instance then
                                            local v51 = nil
                                            if not (_settings_1.CharacterService.DisableFlyCheck) then
                                                v51 = v21.Instance
                                                if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                                    tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                                    if tbl_upv_5.violationBuf > 5 then
                                                        a30._report(a30, "Tampering AC-F4 detected")
                                                        v51.Destroy(v51)
                                                    end
                                                end
                                            end
                                        end
                                        tbl_upv_5.lastRotation = v41
                                        tbl_upv_5.lastPos = v17
                                        tbl_upv_5.lastCFrame = u13.CFrame
                                        tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                        tbl_upv_5.lastY = v17.Y
                                    end
                                end
                            else
                                if v17.Y < workspace.FallenPartsDestroyHeight + 50 and not (_settings_1.WorldService.DisableVoidCheck) and _settings_1.WorldService.MaxVoidLimit < tbl_upv_5.lastY - v17.Y then
                                    a30._report(a30, "Tampering AC-C detected")
                                    u13.CFrame = CFrame.new(v17.X, 100, v17.Z)
                                    u13.AssemblyLinearVelocity = Vector3.zero
                                end
                                local LookVector_3 = u13.CFrame.LookVector
                                if math.acos(math.clamp(tbl_upv_5.lastRotation.Dot(tbl_upv_5.lastRotation, LookVector_3), -1, 1)) > 2.6 and a35 < 0.1 then
                                    if _settings_1.CharacterService.DisableVelocityCheck then
                                        tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                    else
                                        tbl_upv_5.spinCount = tbl_upv_5.spinCount + 1
                                        if _settings_1.CharacterService.SpinSpeed < tbl_upv_5.spinCount then
                                            a30._report(a30, "Tampering AC-C detected")
                                            tbl_upv_5.spinCount = 0
                                        end
                                    end
                                else
                                    tbl_upv_5.spinCount = math.max(0, tbl_upv_5.spinCount - 0.5)
                                end
                                local v42 = va(u13, a32, a31) ~= nil
                                local v43 = false
                                local v44 = RaycastParams.new()
                                v44.FilterType = Enum.RaycastFilterType.Exclude
                                v44.FilterDescendantsInstances = {a32}
                                local v45 = workspace.Raycast(workspace, u13.Position, Vector3.new(0, 4.5, 0), v44)
                                if v45 and v45.Instance then
                                    local v80 = ((v45.Instance.CanCollide) and true) or v43
                                end
                                if v20 == Enum.HumanoidStateType.Jumping or v20 == Enum.HumanoidStateType.Freefall then
                                    if not (tbl_upv_5.jumpDebounce) then
                                        tbl_upv_5.jumpDebounce = true
                                        tbl_upv_5.jumpCount = tbl_upv_5.jumpCount + 1
                                        tbl_upv_5.lastJumpTime = v23
                                        if a31.FloorMaterial == Enum.Material.Air and not (v42) and not (yh(v17)) and _settings_1.CharacterService.MaxJumpAllowed < tbl_upv_5.jumpCount and not (v43) then
                                            a30._report(a30, "Tampering AC-C1 Detected")
                                            u13.CFrame = tbl_upv_5.lastSafeCFrame
                                            u13.AssemblyLinearVelocity = Vector3.zero
                                        end
                                    end
                                else
                                    tbl_upv_5.jumpDebounce = false
                                end
                                if v42 or v43 then
                                    tbl_upv_5.jumpCount = 0
                                    if v42 then
                                        tbl_upv_5.lastSafeCFrame = u13.CFrame
                                    end
                                elseif _settings_1.CharacterService.JumpCooldown < v23 - tbl_upv_5.lastJumpTime then
                                    tbl_upv_5.jumpCount = 0
                                end
                                if v20 ~= Enum.HumanoidStateType.Climbing or _settings_1.DisableSpeedCheck then
                                    tbl_upv_5.climb = 0
                                elseif a31.MoveDirection.Magnitude > 0.2 then
                                    local LookVector_1 = (u13.CFrame * CFrame.Angles(0, math.rad(45), 0)).LookVector
                                    local LookVector_2 = (u13.CFrame * CFrame.Angles(0, math.rad(-45), 0)).LookVector
                                    local v46 = u4.Raycast(u4, u13.Position, u13.CFrame.LookVector * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_1 * 2, u11) or (u4.Raycast(u4, u13.Position, LookVector_2 * 2, u11)))
                                    if v46 then
                                        tbl_upv_5.climb = 0
                                    else
                                        tbl_upv_5.climb = (tbl_upv_5.climb or 0) + a35
                                        if tbl_upv_5.climb > 0.5 then
                                            a30._report(a30, "Tampering AC-C3 detected")
                                            a31.ChangeState(a31, Enum.HumanoidStateType.Freefall)
                                            tbl_upv_5.climb = 0
                                        end
                                    end
                                end
                                if v20 ~= Enum.HumanoidStateType.Swimming or _settings_1.DisableSpeedCheck then
                                    tbl_upv_5.swimGrace = 0
                                else
                                    local v47, v48 = yh(v17)
                                    local v49, v50 = yh(v17 - Vector3.new(0, 2, 0))
                                    if v48 and v50 then
                                        if v47 or v49 then
                                            tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                        else
                                            tbl_upv_5.swimGrace = tbl_upv_5.swimGrace + a35
                                            if tbl_upv_5.swimGrace >= 2 then
                                                a30._report(a30, "Tampering AC-C55 detected")
                                                a31.ChangeState(a31, Enum.HumanoidStateType.FallingDown)
                                                tbl_upv_5.swimGrace = 0
                                            end
                                        end
                                    else
                                        tbl_upv_5.swimGrace = math.max(0, tbl_upv_5.swimGrace - (a35 * 2))
                                    end
                                end
                                if v21 and v21.Instance then
                                    local v51 = nil
                                    if not (_settings_1.CharacterService.DisableFlyCheck) then
                                        v51 = v21.Instance
                                        if v51.IsDescendantOf(v51, a32) and v51.Anchored then
                                            tbl_upv_5.violationBuf = tbl_upv_5.violationBuf + 1
                                            if tbl_upv_5.violationBuf > 5 then
                                                a30._report(a30, "Tampering AC-F4 detected")
                                                v51.Destroy(v51)
                                            end
                                        end
                                    end
                                end
                                tbl_upv_5.lastRotation = LookVector_3
                                tbl_upv_5.lastPos = v17
                                tbl_upv_5.lastCFrame = u13.CFrame
                                tbl_upv_5.lastVelY = AssemblyLinearVelocity_1.Y
                                tbl_upv_5.lastY = v17.Y
                            end
                        end
                    end
                    local tbl_7 = {}
                    tbl_7[9776] = -2
                    tbl_7[-22752] = 2
                    tbl_7[-24233] = 0
                    tbl_7[-22119] = 8
                    tbl_7[16749] = "Tampering AC-C detected"
                    tbl_7[-11019] = 4.5
                    tbl_7[13606] = 0.05
                    tbl_7[-29345] = true
                    tbl_7[29593] = 0
                    tbl_7[-9476] = "Tampering AC-C detected"
                    tbl_7[14017] = 0
                    tbl_7[-26207] = 0
                    tbl_7[26738] = 0.8
                    tbl_7[-21248] = "TrussPart"
                    tbl_7[6178] = 0.5
                    tbl_7[18566] = 0
                    tbl_7[-3957] = 0
                    tbl_7[-27422] = 0.05
                    tbl_7[-32736] = 0
                    tbl_7[28845] = 0
                    tbl_7[-14230] = 0.5
                    return v16(tbl_7)
                end
            )
        end)({[22797] = 0, [16904] = 0})
    end
    tbl_upv_4._protectHumanoid = function(a38, a39)
        a39.StateChanged.Connect(
            a39.StateChanged,
            function(a40, a41)
                if (a41 ~= Enum.HumanoidStateType.PlatformStanding or (a39.SeatPart)) and a41 ~= Enum.HumanoidStateType.StrafingNoPhysics then
                    return
                end
                a39.ChangeState(a39, Enum.HumanoidStateType.FallingDown)
                a38._report(a38, "Tampering AC-C detected")
            end
        )
    end
    local function W()
        return u9.TouchEnabled and (not u9.MouseEnabled)
    end
    tbl_upv_4._startAimbotDetect = function(a42)
        return (function(a43)
            if u9.TouchEnabled and not (u9.MouseEnabled) then
                return
            end
            local LocalPlayer_upv_1 = u2.LocalPlayer
            local _aimbotState_upv_1 = a42._aimbotState
            local CurrentCamera_upv_2 = u4.CurrentCamera
            _aimbotState_upv_1.lockFrames = (function(a44)
                return a43[a44 - 25988]
            end)(13331)
            _aimbotState_upv_1.lastRelativePos = Vector3.zero
            _aimbotState_upv_1.lastCamCFrame = CurrentCamera_upv_2.CFrame
            u3.RenderStepped.Connect(
                u3.RenderStepped,
                function(a45)
                    local Character_1 = LocalPlayer_upv_1.Character
                    local v80 = Character_1 and (ch(Character_1))
                    if not v80 or not CurrentCamera_upv_2 then
                        return
                    end
                    local LookVector_4 = CurrentCamera_upv_2.CFrame.LookVector
                    local v81 = nil
                    local v82 = math.rad(5)
                    local v83, _, v84 = nil, nil, nil
                    v84 = LookVector_4
                    for v90, value_6 in u2.GetPlayers(u2) do
                        if value_6 == LocalPlayer_upv_1 or not (value_6.Character) then
                            continue
                        end
                        local v85 = ch(value_6.Character)
                        if not (v85) then
                            continue
                        end
                        local v86 = math.acos(math.clamp(v84.Dot(v84, (v85.Position - CurrentCamera_upv_2.CFrame.Position).Unit), -1, 1))
                        if v86 < v82 then
                            v82, v81 = v86, v85
                        end
                    end
                    if v81 then
                        local v87 = true
                        if (CurrentCamera_upv_2.CFrame - _aimbotState_upv_1.lastCamCFrame.p).Magnitude > 0.01 then
                            v83 = v87
                        else
                            v83 = math.acos(math.clamp(CurrentCamera_upv_2.CFrame.LookVector.Dot(CurrentCamera_upv_2.CFrame.LookVector, _aimbotState_upv_1.lastCamCFrame.LookVector), -1, 1)) > 0.001
                        end
                        local v88 = v81.AssemblyLinearVelocity.Magnitude > 0.1
                        local v89 = v81.CFrame.PointToObjectSpace(v81.CFrame, CurrentCamera_upv_2.CFrame.Position + (v84 * 10))
                        if not (v83) and not (v88) or not ((v89 - _aimbotState_upv_1.lastRelativePos).Magnitude < 1e-04) then
                            _aimbotState_upv_1.lockFrames = math.max(0, _aimbotState_upv_1.lockFrames - 2)
                            if _aimbotState_upv_1.lockFrames > 80 then
                                a42._report(a42, "Tampering AC-A2 detected")
                                _aimbotState_upv_1.lockFrames = 0
                            end
                            _aimbotState_upv_1.lastRelativePos = v89
                            _aimbotState_upv_1.lastCamCFrame = CurrentCamera_upv_2.CFrame
                            return
                        end
                        _aimbotState_upv_1.lockFrames = _aimbotState_upv_1.lockFrames + 1
                        if _aimbotState_upv_1.lockFrames > 80 then
                            a42._report(a42, "Tampering AC-A2 detected")
                            _aimbotState_upv_1.lockFrames = 0
                        end
                        _aimbotState_upv_1.lastRelativePos = v89
                    else
                        _aimbotState_upv_1.lockFrames = math.max(0, _aimbotState_upv_1.lockFrames - 5)
                    end
                    _aimbotState_upv_1.lastCamCFrame = CurrentCamera_upv_2.CFrame
                end
            )
        end)({[-12657] = 0})
    end
    tbl_upv_4.tfg = function(a46)
        local _triggerState_upv_1 = a46._triggerState
        u9.WindowFocused.Connect(
            u9.WindowFocused,
            function()
                _triggerState_upv_1.lastFocused = true
            end
        )
        u9.WindowFocusReleased.Connect(
            u9.WindowFocusReleased,
            function()
                _triggerState_upv_1.lastFocused = false
            end
        )
        u9.InputBegan.Connect(
            u9.InputBegan,
            function(a47, a48)
                return (function(a49)
                    local function df(a50)
                        return a49[a50 + -20650]
                    end
                    if a47.UserInputType ~= Enum.UserInputType.MouseButton1 then
                        return
                    end
                    if _triggerState_upv_1.lastFocused then
                        _triggerState_upv_1.unfocusedClicks = df(31551)
                        local time_1 = tick()
                        _triggerState_upv_1.clickHistory[_triggerState_upv_1.histIdx] = time_1
                        _triggerState_upv_1.histIdx = (_triggerState_upv_1.histIdx % 32) + 1
                        local v90 = 0
                        for _, value_7 in _triggerState_upv_1.clickHistory do
                            if not (value_7 > 0) then
                                continue
                            end
                            if time_1 - value_7 <= 0.6 then
                                v90 = v90 + 1
                            end
                        end
                        if v90 > 8 then
                            a46._report(a46, "nice macro")
                        end
                    else
                        _triggerState_upv_1.unfocusedClicks = _triggerState_upv_1.unfocusedClicks + 1
                        if _triggerState_upv_1.unfocusedClicks >= 2 then
                            a46._report(a46, "Tampering AC-T2 detected")
                            _triggerState_upv_1.unfocusedClicks = 0
                        end
                    end
                end)({[10901] = 0})
            end
        )
    end
    tbl_upv_4.vsa = function(a51)
        return (function(a52)
            local _lightingSnap_upv_1 = a51._lightingSnap
            local _settings_upv_2 = a51._settings
            task.spawn(
                function()
                    task.wait(4)
                    local v91 = math.abs(u5.ClockTime - _lightingSnap_upv_1.lastClockTime)
                    if v91 > 12 then
                        v91 = 24 - v91
                    end
                    if not (v91 <= 2) then
                        return
                    end
                    _lightingSnap_upv_1.lastClockTime = u5.ClockTime
                    _lightingSnap_upv_1.Brightness = u5.Brightness
                end
            )
            u5.GetPropertyChangedSignal(u5, "Ambient").Connect(
                u5.GetPropertyChangedSignal(u5, "Ambient"),
                function()
                    if not _settings_upv_2.WorldService then
                        return
                    end
                    if not (_settings_upv_2.WorldService.DisableAmbientCheck) then
                        local Ambient_1 = u5.Ambient
                        if Ambient_1.R > 0.95 or Ambient_1.G > 0.95 or Ambient_1.B > 0.95 then
                            a51._report(a51, "Tampering AC-L detected")
                            u5.Ambient = _lightingSnap_upv_1.Ambient
                        end
                    end
                end
            )
            u5.GetPropertyChangedSignal(u5, "OutdoorAmbient").Connect(
                u5.GetPropertyChangedSignal(u5, "OutdoorAmbient"),
                function()
                    return (function(a53)
                        local function Eh(a54)
                            return a53[a54 + -13849]
                        end
                        if not _settings_upv_2.WorldService then
                            return
                        end
                        if not (_settings_upv_2.WorldService.DisableAmbientCheck) then
                            local OutdoorAmbient_1 = u5.OutdoorAmbient
                            if not (Eh(-14778) < OutdoorAmbient_1.R) and not (OutdoorAmbient_1.G > 0.95) and not (OutdoorAmbient_1.B > 0.95) then
                                return
                            end
                            a51._report(a51, "Tampering AC-L detected")
                            u5.OutdoorAmbient = _lightingSnap_upv_1.OutdoorAmbient
                        end
                    end)({[-28627] = 0.95})
                end
            )
            u5.GetPropertyChangedSignal(u5, "Brightness").Connect(
                u5.GetPropertyChangedSignal(u5, "Brightness"),
                function()
                    return (function(a55)
                        local function y(a56)
                            return a55[a56 + 12260]
                        end
                        if not _settings_upv_2.WorldService or (_settings_upv_2.WorldService.DisableBrightnessCheck) or not (math.max(_lightingSnap_upv_1.Brightness + 5, 10) < u5.Brightness) then
                            return
                        end
                        a51._report(a51, "Tampering AC-L detected")
                        u5.Brightness = _lightingSnap_upv_1.Brightness
                    end)({[13576] = 5, [8072] = 10})
                end
            )
            u5.GetPropertyChangedSignal(u5, "FogEnd").Connect(
                u5.GetPropertyChangedSignal(u5, "FogEnd"),
                function()
                    return (function(a57)
                        local function rh(a58)
                            return a57[a58 - 14313]
                        end
                        if not _settings_upv_2.WorldService or (_settings_upv_2.WorldService.DisableFogCheck) then
                            return
                        end
                        if _lightingSnap_upv_1.FogEnd + 5000 < u5.FogEnd then
                            a51._report(a51, "Tampering AC-L detected")
                            u5.FogEnd = _lightingSnap_upv_1.FogEnd
                        end
                    end)({[-26599] = "Tampering AC-L detected"})
                end
            )
            local function Hf(a59)
                return a52[a59 - -6005]
            end
            u5.GetPropertyChangedSignal(u5, Hf(18442)).Connect(
                u5.GetPropertyChangedSignal(u5, Hf(18442)),
                function()
                    if not _settings_upv_2.WorldService or (_settings_upv_2.WorldService.DisableShadowCheck) then
                        return
                    end
                    if _lightingSnap_upv_1.GlobalShadows == true and u5.GlobalShadows == false then
                        a51._report(a51, "Tampering AC-L detected")
                        u5.GlobalShadows = true
                    end
                end
            )
            u5.GetPropertyChangedSignal(u5, "ClockTime").Connect(
                u5.GetPropertyChangedSignal(u5, "ClockTime"),
                function()
                    return (function(a60)
                        local function kd(a61)
                            return a60[a61 + -8808]
                        end
                        if not _settings_upv_2.WorldService then
                            return
                        end
                        if not (_settings_upv_2.WorldService.DisableTimeCheck) then
                            local ClockTime_1 = u5.ClockTime
                            local v92 = math.abs(ClockTime_1 - _lightingSnap_upv_1.lastClockTime)
                            if v92 > 12 then
                                v92 = 24 - v92
                            end
                            if kd(-13722) < v92 then
                                a51._report(a51, "Tampering AC-L Detected")
                                u5.ClockTime = _lightingSnap_upv_1.lastClockTime
                            else
                                _lightingSnap_upv_1.lastClockTime = ClockTime_1
                            end
                        end
                    end)({[-22530] = 2})
                end
            )
        end)({[24447] = "GlobalShadows"})
    end
    local u14 = 0
    tbl_upv_4.xry = function(a62, a63)
        task.spawn(
            function()
                return (function(a64)
                    local v93 = nil
                    local function N(a65)
                        return a64[a65 + 25947]
                    end
                    while task.wait(2) do
                        if not a62._settings.WorldService or a62._settings.WorldService.DisableXrayCheck then
                            return
                        end
                        local v94 = OverlapParams.new()
                        v94.FilterType = Enum.RaycastFilterType.Exclude
                        v94.FilterDescendantsInstances = {a63}
                        v93 = 0
                        for _, value_8 in workspace.GetPartBoundsInRadius(workspace, workspace.CurrentCamera.CFrame.Position, 50, v94) do
                            local v95 = value_8.IsDescendantOf(value_8, a63)
                            if v95 or not (value_8.LocalTransparencyModifier > 0.1) then
                                continue
                            end
                            local v96 = value_8.IsA(value_8, "Decal")
                            if v96 then
                                continue
                            end
                            if value_8.Material ~= Enum.Material.Glass then
                                v93 = v93 + 1
                            end
                        end
                        if not (v93 > 8) then
                            u14 = math.max(0, u14 - 1)
                            continue
                        end
                        u14 = u14 + 1
                        if not (u14 >= 2) then
                            continue
                        end
                        a62._report(a62, "Tampering AC-X2 Detected")
                        return
                    end
                end)({[18555] = 0, [-25277] = 2})
            end
        )
    end
    tbl_upv_4._startService = function(a66, a67)
        return (function(a68)
            local _settings_upv_3 = a66._settings
            local u15 = _settings_upv_3 and (_settings_upv_3.EncryptionService)
            local function Gc(a69)
                return a68[a69 + 28827]
            end
            if not u15 then
                return
            end
            if u15.Enabled == true then
                a67.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
                local Character_upv_2 = u2.LocalPlayer.Character
                if not Character_upv_2 then
                    return
                end
                local u16 = Character_upv_2.FindFirstChild(Character_upv_2, "HumanoidRootPart")
                if not u16 then
                    return
                end
                local u17 = false
                local u18 = game.GetService(game, "HttpService")
                local v97 = game.GetService(game, "VoiceChatService")
                local tbl_upv_8 = {
                    "BanIDFrame",
                    "BanIDLabel",
                    "BanIDTitle",
                    "BanReasonFrame",
                    "ReasonLabel",
                    "ReasonTitle",
                    "StatusFrame",
                    "StatusLabel",
                    "StatusTitle",
                    "FirstFrame",
                    "SecondFrame",
                    "ThirdFrame",
                    "MainDesc",
                    "MainTitle",
                    "AboutLabel",
                    "BG",
                    "ImageBG"
                }
                local function Qf(a70)
                    return (function(a71)
                        local function Ce_1(a72)
                            return a71[a72 - -1597]
                        end
                        if not a70 then
                            return Ce_1(-18436)
                        end
                        if table.find(tbl_upv_8, a70.Name) or a70.Parent and table.find(u15.IgnoredParents or {}, a70.Parent.Name) or u2.GetPlayerFromCharacter(u2, a70.Parent) or a70.IsA(a70, "Humanoid") then
                            return true
                        end
                        local Name_1 = a70.Name
                        local v98 = ((a70.Parent) and (a70.Parent.Name)) or ""
                        if Name_1 ~= "ZenAC" and Name_1 ~= "Character" and Name_1 ~= "Event" and Name_1 ~= Ce_1(-21584) and Name_1 ~= Ce_1(-11216) and v98 ~= "Settings" and v98 ~= "Integrity" and v98 ~= "Network" then
                            return false
                        end
                        return true
                    end)({[-9619] = "AntiCheatModules", [-19987] = "AntiCheatLoader", [-16839] = true})
                end
                local function Gb(a73)
                    if a73 == game then
                        return
                    end
                    pcall(
                        function()
                            local v99 = "OtherService"
                            if a73.IsDescendantOf(a73, a67.Parent) then
                                v99 = "Character"
                            else
                                local v100 = a73
                                while v100.Parent and v100.Parent ~= game do
                                    v100 = v100.Parent
                                end
                                if v100.Parent == game then
                                    v99 = v100.ClassName
                                end
                            end
                            if table.find(u15.IgnoredServices or {}, v99) then
                                return
                            end
                            local v101 = u15["Service" .. v99 .. "Encryption"]
                            local v102 = u15["Service" .. v99 .. "Attributes"]
                            if v101 == true and not (Qf(a73)) then
                                if u15.SmartNaming then
                                    a73.Name = a73.Name .. " "
                                else
                                    a73.Name = u18.GenerateGUID(u18, false).sub(u18.GenerateGUID(u18, false), 1, 35)
                                end
                            end
                            if v102 ~= true then
                                return
                            end
                            if not Qf(a73) then
                                for _ = 88, 97 do
                                    a73.SetAttribute(a73, tostring(math.random(1e+05, 9998889)), u18.GenerateGUID(u18, false).sub(u18.GenerateGUID(u18, false), 1, 30))
                                end
                            end
                        end
                    )
                end
                task.spawn(
                    function()
                        for key_1, value_9 in ipairs(game.GetDescendants(game)) do
                            Gb(value_9)
                            if key_1 % 200 == 0 then
                                task.wait()
                            end
                        end
                    end
                )
                game.DescendantAdded.Connect(game.DescendantAdded, Gb)
                u8.MessageOut.Connect(
                    u8.MessageOut,
                    function(a74)
                        return (function(a75)
                            local function m(a76)
                                return a75[a76 - 27109]
                            end
                            if typeof(a74) ~= "string" or not _settings_upv_3.ClientBridge or not _settings_upv_3.ClientBridge.Injection or not _settings_upv_3.ClientBridge.Injection.Logging then
                                return
                            end
                            local v103 = a74.lower(a74)
                            for _, value_10 in ipairs(_settings_upv_3.ClientBridge.lg or {}) do
                                if typeof(value_10) ~= "string" then
                                    continue
                                end
                                local success_2, v104 = pcall(string.find, v103, value_10.lower(value_10))
                                if not (success_2) or not (v104) then
                                    continue
                                end
                                a66._report(a66, "Tampering AC-S detected")
                                return
                            end
                            if not v103.find(v103, "loadstring:%d+") then
                                return
                            end
                            a66._report(a66, "Tampering AC-S detected")
                        end)({[-797] = "string", [-32165] = "Tampering AC-S detected", [31311] = "Tampering AC-S detected"})
                    end
                )
                local u19 = 0
                local u20 = os.clock()
                v97.DescendantAdded.Connect(
                    v97.DescendantAdded,
                    function(a77)
                        return (function(a78)
                            local function Cg(a79)
                                return a78[a79 - -7115]
                            end
                            if not a77.IsA(a77, "RemoteEvent") or (a77.Name.find(a77.Name, "Zen")) then
                                return
                            end
                            u19 = u19 + Cg(21820)
                        end)({[28935] = 1})
                    end
                )
                u3.Heartbeat.Connect(
                    u3.Heartbeat,
                    function()
                        return (function(a80)
                            local v105 = os.clock()
                            if v105 - u20 >= 5 then
                                if u19 > 80 then
                                    a66._report(a66, "Tampering AC-S detected")
                                end
                                u19 = 0
                                u20 = v105
                            end
                            local v106 = OverlapParams.new()
                            v106.FilterType = Enum.RaycastFilterType.Exclude
                            v106.FilterDescendantsInstances = {Character_upv_2}
                            local function Ab(a81)
                                return a80[a81 + -11344]
                            end
                            for _, value_11 in ipairs(workspace.GetPartBoundsInRadius(workspace, u16.Position, 20, v106)) do
                                if value_11.Anchored or not (value_11.FindFirstChildOfClass(value_11, Ab(18692))) then
                                    continue
                                end
                                if not (u17) then
                                    u17 = true
                                    a66._report(a66, "Tampering AC-I detected")
                                end
                                local v107 = value_11.FindFirstChildOfClass(value_11, "BodyPosition")
                                if v107 then
                                    value_11.FindFirstChildOfClass(value_11, "BodyPosition").Destroy(value_11.FindFirstChildOfClass(value_11, "BodyPosition"))
                                end
                                value_11.AssemblyLinearVelocity = Vector3.new(0, Ab(11246), 0)
                                value_11.AssemblyAngularVelocity = Vector3.new(0, 0, 0)
                            end
                        end)({[-98] = 0, [7348] = "BodyPosition"})
                    end
                )
            end
        end)({[-24202] = "StatusTitle", [17283] = "FirstFrame", [-16105] = "BanIDTitle"})
    end
    tbl_upv_4.CL = function(a82)
        return (function(a83)
            local _settings_upv_4 = a82._settings
            local env_upv_1 = getfenv()
            local tbl_9 = {}
            local tbl_10 = {}
            function tbl_10.__index(a84, a85)
                return (function(a86)
                    local function Ch(a87)
                        return a86[a87 + 16458]
                    end
                    local env_2 = getfenv(2)
                    if env_2 and (env_2.getgenv or env_2.syn or env_2.hookfunction) then
                        a82._report(a82, "Tampering AC-I Detected")
                    end
                    return env_upv_1[a85]
                end)({[19296] = 2})
            end
            tbl_10.__metatable = "The metatable is locked"
            setfenv(1, (setmetatable(tbl_9, tbl_10)))
            setfenv(0, getfenv(1))
            task.spawn(
                function()
                    if not pcall(
                        function()
                            return game.findpartonraywithwhitelist(game)
                        end
                    ) then
                        return
                    end
                    a82._report(a82, "Tampering AC-I Detected")
                end
            )
            task.spawn(
                function()
                    local u21 = nil
                    xpcall(
                        function()
                            return game.___
                        end,
                        function()
                            return (function(a88)
                                local function kf(a89)
                                    return a88[a89 + -12377]
                                end
                                u21 = debug.info(kf(9567), "f")
                            end)({[-2810] = 2})
                        end
                    )
                    if u21 then
                        local userdata_1 = newproxy(true)
                        getmetatable(userdata_1).__namecall = function(...)
                            return (function(a90, ...)
                                local env_3 = getfenv(2)
                                local function if_(a91)
                                    return a90[a91 + -5157]
                                end
                                if env_3 and (env_3.getgenv or env_3.syn) then
                                    a82._report(a82, if_(30605))
                                end
                                return nil
                            end)({[25448] = "Tampering AC-I Detected"}, ...)
                        end
                        pcall(u21, userdata_1)
                    end
                end
            )
            local function Hc()
                local u22 = false
                pcall(
                    function()
                        game.GetObjects(game, "rbxasset://levels/Test.rbxl")
                        u22 = true
                    end
                )
                if u22 then
                    return true
                end
                if pcall(
                    function()
                        local v108 = false
                        if gethiddenproperty ~= nil then
                            v108 = gethiddenproperty
                        end
                        return v108
                    end
                ) then
                    local _, v109 = pcall(
                        function()
                            return gethiddenproperty
                        end
                    )
                    if v109 then
                        return true
                    end
                end
                return false
            end
            local function ee()
                return (function(a92)
                    local u23 = false
                    pcall(
                        function()
                            u23 = __LOADSTRING_ENABLED__ == true
                        end
                    )
                    if u23 then
                        return true, "loadstring enabled"
                    end
                    local function ab_1(a93)
                        return a92[a93 + 22438]
                    end
                    local u24 = false
                    pcall(
                        function()
                            return (function(a94)
                                local v110 = debug.info(0, "s")
                                local function Ze_1(a95)
                                    return a94[a95 - -6111]
                                end
                                if type(v110) ~= "string" or v110 == Ze_1(-27621) or not (v110.find(v110, "%.exe")) and not (v110.find(v110, "Injector")) and not (v110.find(v110, "exploit")) then
                                    return
                                end
                                u24 = true
                            end)({[-21510] = ""})
                        end
                    )
                    if u24 then
                        return true, "injected call stack"
                    end
                    return false, ""
                end)({[-323] = false, [-18363] = ""})
            end
            local function na()
                local u25 = false
                pcall(
                    function()
                        local v111 = true
                        if hookfunction == nil then
                            v111 = getrawmetatable ~= nil
                        end
                        u25 = v111
                    end
                )
                if not u25 then
                    return false
                end
                local u26 = false
                pcall(
                    function()
                        local v112 = true
                        if getsignal == nil then
                            v112 = getconnections ~= nil
                        end
                        u26 = v112
                    end
                )
                local v113 = u25 and u26
                return v113
            end
            local function Dg()
                local v114 = 0
                for _, value_12 in {
                    function()
                        return getgenv ~= nil
                    end,
                    function()
                        return getrenv ~= nil
                    end,
                    function()
                        return getrawmetatable ~= nil
                    end,
                    function()
                        return hookfunction ~= nil
                    end,
                    function()
                        return newcclosure ~= nil
                    end,
                    function()
                        return cclosure ~= nil
                    end,
                    function()
                        return readfile ~= nil
                    end,
                    function()
                        return writefile ~= nil
                    end
                } do
                    local success_3, v115 = pcall(value_12)
                    if not (success_3) then
                        continue
                    end
                    if v115 == true then
                        v114 = v114 + 1
                    end
                end
                return v114
            end
            task.spawn(
                function()
                    task.wait(3)
                    local v116 = Dg()
                    local v117 = Hc()
                    local v118 = na()
                    local v119 = ee()
                    local v120 = 0
                    if v116 >= 2 then
                        v120 = v120 + 1
                    end
                    if v116 >= 4 then
                        v120 = v120 + 1
                    end
                    v120 = v117 and v120 + 1
                    v120 = (v118 and (v120 + 1)) or v120
                    if v119 then
                        v120 = v120 + 1
                    end
                    if v120 >= 2 then
                        a82._report(a82, "Tampering AC-I Detected")
                    end
                    local u27 = getfenv()["error"]
                    task.wait(30)
                    local v121 = Dg()
                    local v122 = na()
                    if v121 >= 3 then
                        a82._report(a82, "Tampering AC-I Detected")
                        pcall(
                            function()
                                local v123 = getrawmetatable(game)
                                if not v123 or not rawget(v123, "__index") then
                                    return
                                end
                                a82._report(a82, "Tampering AC-I Detected")
                            end
                        )
                        xpcall(
                            function()
                                return u27()
                            end,
                            function(a96)
                                return (function(a97)
                                    local v124 = debug.traceback()
                                    local v125 = true
                                    if v124 ~= nil then
                                        v125 = string.gsub(v124, "%s+", "") == ""
                                    end
                                    local v126
                                    local function jc(a98)
                                        return a97[a98 - 3888]
                                    end
                                    if debug.info(2, jc(-11216)) ~= u27 then
                                        v126 = true
                                    else
                                        v126 = false
                                    end
                                    if v125 or v126 then
                                        local v127 = debug.info(2, "n")
                                        if v127 == "" or v127 == "error" or v125 then
                                            return
                                        end
                                        a82._report(a82, "Tampering AC-I Detected")
                                    end
                                end)({[-15104] = "f"})
                            end
                        )
                    elseif v122 then
                        a82._report(a82, "Tampering AC-I Detected")
                        pcall(
                            function()
                                local v123 = getrawmetatable(game)
                                if not v123 or not rawget(v123, "__index") then
                                    return
                                end
                                a82._report(a82, "Tampering AC-I Detected")
                            end
                        )
                        xpcall(
                            function()
                                return u27()
                            end,
                            function(a96)
                                return (function(a97)
                                    local v124 = debug.traceback()
                                    local v125 = true
                                    if v124 ~= nil then
                                        v125 = string.gsub(v124, "%s+", "") == ""
                                    end
                                    local v126
                                    local function jc(a98)
                                        return a97[a98 - 3888]
                                    end
                                    if debug.info(2, jc(-11216)) ~= u27 then
                                        v126 = true
                                    else
                                        v126 = false
                                    end
                                    if v125 or v126 then
                                        local v127 = debug.info(2, "n")
                                        if v127 == "" or v127 == "error" or v125 then
                                            return
                                        end
                                        a82._report(a82, "Tampering AC-I Detected")
                                    end
                                end)({[-15104] = "f"})
                            end
                        )
                    else
                        pcall(
                            function()
                                local v123 = getrawmetatable(game)
                                if not v123 or not rawget(v123, "__index") then
                                    return
                                end
                                a82._report(a82, "Tampering AC-I Detected")
                            end
                        )
                        xpcall(
                            function()
                                return u27()
                            end,
                            function(a96)
                                return (function(a97)
                                    local v124 = debug.traceback()
                                    local v125 = true
                                    if v124 ~= nil then
                                        v125 = string.gsub(v124, "%s+", "") == ""
                                    end
                                    local v126
                                    local function jc(a98)
                                        return a97[a98 - 3888]
                                    end
                                    if debug.info(2, jc(-11216)) ~= u27 then
                                        v126 = true
                                    else
                                        v126 = false
                                    end
                                    if v125 or v126 then
                                        local v127 = debug.info(2, "n")
                                        if v127 == "" or v127 == "error" or v125 then
                                            return
                                        end
                                        a82._report(a82, "Tampering AC-I Detected")
                                    end
                                end)({[-15104] = "f"})
                            end
                        )
                    end
                end
            )
            local function wg(a99)
                return a83[a99 + -19181]
            end
            local tbl_upv_11 = {
                wg(7360),
                "1204397029",
                "2764171053",
                "1352543873",
                "14806198159",
                "14806221310",
                "14806229032",
                "14806239733",
                "14806252030",
                "11559270573",
                "13363121645",
                "11558444554",
                "12730597972",
                "11702779517",
                "13462268450",
                "13462270380",
                "13462271348",
                "13462269327",
                wg(11646),
                "13365407660"
            }
            local tbl_upv_12 = {"evon", "codex", "delta", "hydro", "undtc"}
            local u28 = setmetatable({}, {__mode = "v"})
            local str_1 = tostring(math.random())
            Instance.new("BoolValue", u7).Name = str_1
            task.spawn(
                function()
                    return (function(a100)
                        task.wait(0.5)
                        pcall(
                            function()
                                local LocalPlayer_2 = u2.LocalPlayer
                                if not LocalPlayer_2 then
                                    return
                                end
                                u6.PreloadAsync(
                                    u6,
                                    {game.GetService(game, "CoreGui"), LocalPlayer_2.FindFirstChildOfClass(LocalPlayer_2, "PlayerGui")},
                                    function(a101)
                                        local v128 = a101.gsub(a101, "rbxassetid://", "").gsub(a101.gsub(a101, "rbxassetid://", ""), "http://www%.roblox%.com/asset/%?id=", "").lower(
                                            a101.gsub(a101, "rbxassetid://", "").gsub(a101.gsub(a101, "rbxassetid://", ""), "http://www%.roblox%.com/asset/%?id=", "")
                                        )
                                        if table.find(tbl_upv_11, v128) then
                                            a82._report(a82, "Tampering AC-I Detected")
                                        else
                                            for _, value_13 in tbl_upv_12 do
                                                if not (v128.find(v128, value_13, 1, true)) then
                                                    continue
                                                end
                                                a82._report(a82, "Tampering AC-I Detected")
                                                return
                                            end
                                        end
                                    end
                                )
                            end
                        )
                        local v129 = game.GetService(game, "WebSocketService")
                        local v130 = setmetatable({}, {__mode = "v"})
                        table.insert(v130, v129)
                        local function Wb(a102)
                            return a100[a102 - -4988]
                        end
                        if v130[1] then
                            if u3.IsStudio(u3) then
                                u28[4] = {}
                                local v131 = Wb(-14947)
                                u28[v131] = u7.FindFirstChildOfClass(u7, "BoolValue")
                                local v132 = tick() + 1
                                while u28[4] ~= nil do
                                    if tick() < v132 then
                                        u28[6] = string.rep("ab", 512)
                                        u28[6] = nil
                                        task.wait()
                                        continue
                                    else
                                        break
                                    end
                                end
                            else
                                a82._report(a82, "Tampering AC-I Detected")
                                u28[4] = {}
                                local v131 = Wb(-14947)
                                u28[v131] = u7.FindFirstChildOfClass(u7, "BoolValue")
                                local v132 = tick() + 1
                                while u28[4] ~= nil do
                                    if tick() < v132 then
                                        u28[6] = string.rep("ab", 512)
                                        u28[6] = nil
                                        task.wait()
                                        continue
                                    else
                                        break
                                    end
                                end
                            end
                        else
                            u28[4] = {}
                            local v131 = Wb(-14947)
                            u28[v131] = u7.FindFirstChildOfClass(u7, "BoolValue")
                            local v132 = tick() + 1
                            while u28[4] ~= nil do
                                if tick() < v132 then
                                    u28[6] = string.rep("ab", 512)
                                    u28[6] = nil
                                    task.wait()
                                    continue
                                else
                                    break
                                end
                            end
                        end
                    end)({[-9959] = 5})
                end
            )
            local tbl_upv_13 = {}
            local v133 = "rbxasset://custom_gloop/"
            tbl_upv_13[v133] = wg(2811)
            local v134 = "rbxasset://RonixExploit/"
            tbl_upv_13[v134] = "Ronix"
            local tbl_upv_14 = {{pattern = "service=", match = "pandadevelopment%.net", name = "PandaDev proxy"}, {pattern = wg(20646), name = "loadstring usage"}}
            u8.MessageOut.Connect(
                u8.MessageOut,
                function(a103)
                    return (function(a104)
                        if type(a103) ~= "string" then
                            return
                        end
                        local v135 = a103.lower(a103)
                        local function Je(a105)
                            return a104[a105 + 2123]
                        end
                        for key_2, _ in tbl_upv_13 do
                            local v136 = v135.find(v135, key_2.lower(key_2), 1, true)
                            if not (v136) or _settings_upv_4.ClientService.Injection.MobileExploitDetection then
                                continue
                            end
                            a82._report(a82, "Tampering AC-I Detected")
                            return
                        end
                        for _, value_14 in tbl_upv_14 do
                            local success_4, v137 = pcall(string.find, v135, value_14.pattern)
                            if not (success_4) or not (v137) or value_14.match and (not (v135.find(v135, value_14.match)) or _settings_upv_4.ClientService.Injection.MobileExploitDetection) then
                                continue
                            end
                            a82._report(a82, "Tampering AC-I Detected")
                            return
                        end
                    end)({[32565] = true})
                end
            )
            pcall(
                function()
                    game.GetService(game, "GuiService").SetInspectMenuEnabled(game.GetService(game, "GuiService"), false)
                end
            )
            task.spawn(
                function()
                    repeat
                        task.wait(10)
                    until not (pcall(
                        function()
                            return game.GetService(game, "GuiService").GetInspectMenuEnabled(game.GetService(game, "GuiService"))
                        end
                    ))
                    a82._report(a82, "Tampering AC-F Detected")
                end
            )
        end)({[-11821] = "137842439297855", [1465] = "loadstring:%d+", [-7535] = "13569242972", [-16370] = "Delta"})
    end
    tbl_upv_4.qwe = function(a106)
        task.spawn(
            function()
                return (function(a107)
                    local function Jg(a108)
                        return a107[a108 - -31284]
                    end
                    while task.wait(5) do
                        for v140, value_15 in ipairs(u2.GetPlayers(u2)) do
                            if value_15 == u2.LocalPlayer then
                                continue
                            end
                            local Character_3 = value_15.Character
                            local v138 = Character_3 and (Character_3.FindFirstChild(Character_3, "HumanoidRootPart"))
                            if not (v138) or not (v138.IsA(v138, "BasePart")) then
                                continue
                            end
                            if v138.Size.Magnitude > 10 then
                                v138.Size = Vector3.new(2, Jg(-16321), 1)
                                v138.Transparency = 1
                                v138.CanCollide = true
                            end
                        end
                    end
                end)({[14963] = 2})
            end
        )
    end
    tbl_upv_4.OnCharacterAdded = function(a109, a110)
        local v139 = a110:WaitForChild("Humanoid", 10)
        local v140 = a110:WaitForChild("HumanoidRootPart", 10)
        if not v139 or not v140 then
            return
        end
        a109._protectHumanoid(a109, v139)
        a109._startLoop(a109, v139, a110)
        a109.xry(a109, a110)
        a109._startService(a109, v139)
    end
    tbl_upv_4.Start = function(a111, a112, a113)
        a111._reportFunc = a112
        if a113 and type(a113) == "table" then
            a111._settings = a113
        end
        a111.vsa(a111)
        a111._startAimbotDetect(a111)
        a111.tfg(a111)
        a111.CL(a111)
        a111.qwe(a111)
        local LocalPlayer_upv_3 = u2.LocalPlayer
        if LocalPlayer_upv_3.Character then
            task.defer(
                function()
                    a111.OnCharacterAdded(a111, LocalPlayer_upv_3.Character)
                end
            )
        end
        LocalPlayer_upv_3.CharacterAdded.Connect(
            LocalPlayer_upv_3.CharacterAdded,
            function(a114)
                a111.OnCharacterAdded(a111, a114)
            end
        )
    end
    local v142 = (function()
        local v141 = setmetatable({}, tbl_upv_4)
        v141._settings = {}
        v141._reportFunc = nil
        v141._aimbotState = {snapCount = 0, fovIdx = 1, fovViolations = 0, lastCamCF = CFrame.new(), fovTrackBuf = table.create(20, 0)}
        v141._triggerState = {lastFocused = true, unfocusedClicks = 0, histIdx = 1, clickHistory = table.create(32, 0)}
        v141._lightingSnap = {Ambient = u5.Ambient, OutdoorAmbient = u5.OutdoorAmbient, Brightness = u5.Brightness, ClockTime = u5.ClockTime, FogEnd = u5.FogEnd, GlobalShadows = u5.GlobalShadows, lastClockTime = u5.ClockTime}
        return v141
    end)()
    local v144 = (function(a115)
        local tbl_15 = {}
        local tbl_16 = {__tostring = 0, __metatable = false, __newindex = 0}
        function tbl_16.__index(a116, a117)
            local v143 = debug.info(2, "s")
            if v143 ~= "" and v143 ~= nil then
                if string.find(v143, "Loadstring") then
                    u2.LocalPlayer.Kick(u2.LocalPlayer, "Tampering.")
                    return nil
                else
                    local u29 = a115[a117]
                    if type(u29) ~= "function" then
                        return u29
                    end
                    return function(a118, ...)
                        return u29(a115, ...)
                    end
                end
            end
            return nil
        end
        function tbl_16.__newindex(a119, a120, a121)
            return a121
        end
        function tbl_16.__tostring()
            return ""
        end
        return (setmetatable(tbl_15, tbl_16))
    end)(v142)
    return v144
end)({[4371] = true, [-17424] = "Lighting", [4592] = "LogService", [32064] = 0}, ...)