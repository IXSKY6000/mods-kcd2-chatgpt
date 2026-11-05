-- Experimental KCD2 integration. See docs/VALIDATION.md before installing.
-- Uses the game's chat interactor, never RequestDialog / ForceDialog.
StreetTalk = StreetTalk or { cooldowns = {}, pending = nil }
local ST = StreetTalk
ST.cooldownSeconds = 15
ST.people = ST.people or {}
ST.globalUntil = 0
ST.greetSeconds = 90
ST.angerSeconds = 180

-- A missing readiness check must not turn into permission to steal R1.
function ST.NativeReplyBusy(user)
    if not user or not user.actor.IsWaitingForDialogueReply
        or not System.GetEntitiesInSphere or not user.GetWorldPos then return true end
    if user.actor:IsWaitingForDialogueReply() then return true end
    for _, other in pairs(System.GetEntitiesInSphere(user:GetWorldPos(), 35) or {}) do
        if other.actor and other.human then
            if not other.actor.IsWaitingForDialogueReply then return true end
            if other.actor:IsWaitingForDialogueReply() or other.actor:HasChatRequest()
                or other.actor:HasAcceptedChat() then return true end
        end
    end
    return false
end

function ST.ContextSafe(npc, user)
    if not user.player or not user.human or not user.player.IsSitting
        or not user.player.IsLaying or not user.human.IsPickpocketing
        or not user.human.IsInDialog or not npc.human.IsInDialog then return false end
    if user.player:IsSitting() or user.player:IsLaying()
        or user.human:IsPickpocketing() then return false end
    if user.soul:IsInCombatDanger() or user.soul:IsInTenseCircumstance()
        or user.soul:IsInCombatMode() or npc.soul:IsInCombatMode()
        or npc.soul:IsInCombatDanger() or npc.soul:IsInTenseCircumstance() then return false end
    if user.human:IsInDialog() or npc.human:IsInDialog() then return false end
    return true
end

local function log(message)
    if System and System.LogAlways then
        System.LogAlways('[StreetTalk] ' .. message)
    end
end

local function now()
    return System.GetCurrTime()
end

function ST.Eligible(npc, user)
    if not npc or not user or npc == user or not npc.human or not npc.actor
        or not npc.soul or not npc.this or not user.actor or not user.soul
        or not user.this then return false end
    if npc.actor:IsDead() or npc.actor:IsUnconscious()
        or user.actor:IsDead() or user.actor:IsUnconscious() then return false end
    if not ST.ContextSafe(npc, user) or ST.NativeReplyBusy(user) then return false end
    if user.soul:IsInCombatDanger() or user.soul:IsInTenseCircumstance()
        or npc.soul:IsInCombatMode() then return false end
    if not user.actor:CanInteractWith(npc.id) then return false end
    if npc.soul:IsDialogRestricted(user.id) then return false end
    -- Fail closed if the current runtime cannot check dialogue ownership.
    if not DialogModule or not DialogModule.IsSoulInDialog then return false end
    if DialogModule.IsSoulInDialog(user.this.id)
        or DialogModule.IsSoulInDialog(npc.this.id) then return false end
    if npc.actor:HasChatRequest() or npc.actor:HasAcceptedChat()
        or npc.actor:CanChat(user.id) then return false end
    return true
end

function ST.Available(npc, user)
    if ST.pending or not ST.Eligible(npc, user) then return false end
    local state = ST.people[tostring(npc.this.id)] or {}
    return now() >= ST.globalUntil and now() >= (state.angryUntil or 0)
        and now() >= (ST.cooldowns[tostring(npc.this.id)] or 0)
end

function ST.CanChoose(kind)
    local session = ST.session
    if not session or now() > session.expires then return false end
    local npc, user = System.GetEntity(session.npcId), System.GetEntity(session.userId)
    if not npc or not user or npc ~= session.npc or user ~= session.user then return false end
    if npc.actor:IsDead() or npc.actor:IsUnconscious() or user.actor:IsDead()
        or user.actor:IsUnconscious() or user.soul:IsInCombatDanger()
        or user.soul:IsInTenseCircumstance() or user.soul:IsInCombatMode()
        or npc.soul:IsInCombatMode() or npc.soul:IsInCombatDanger()
        or npc.soul:IsInTenseCircumstance() or user.player:IsSitting()
        or user.player:IsLaying() or user.human:IsPickpocketing()
        or not user.actor:CanInteractWith(npc.id) then return false end
    local state = ST.people[session.key] or {}
    if now() < (state.angryUntil or 0) or now() < ST.globalUntil then return false end
    if kind == 'greet' then return now() >= (state.greetUntil or 0) end
    return kind == 'antagonize'
end

function ST.OnChoice(kind)
    if not ST.CanChoose(kind) then return false end
    local session = ST.session
    local state = ST.people[session.key] or {}
    ST.people[session.key] = state
    ST.globalUntil = now() + 5
    session.expires = 0 -- One committed choice, even if a callback fires twice.
    if kind == 'greet' then
        if now() >= (state.greetUntil or 0) and (state.greets or 0) >= 2
            or now() > (state.lastGreet or -math.huge) + ST.greetSeconds then
            state.greets = 0
        end
        state.greets = (state.greets or 0) + 1
        state.lastGreet = now()
        if state.greets >= 2 then state.greetUntil = now() + ST.greetSeconds end
        -- Allow the second greeting as soon as the short exchange has finished.
        ST.globalUntil = now() + 2
        ST.cooldowns[session.key] = now() + 2
    else
        if now() > (state.lastProvoked or -math.huge) + ST.angerSeconds then
            state.strikes = 0
        end
        state.strikes = (state.strikes or 0) + 1
        state.lastProvoked = now()
        session.angry = state.strikes >= 3
        if session.angry then
            state.angryUntil = now() + ST.angerSeconds
            -- Native NPC relationship penalty, not a forced attack or a crime.
            session.npc.soul:ModifyPlayerReputation('quest_decrease_2_minor', true)
        end
    end
    return true
end

function ST.IsAngry()
    return ST.session and ST.session.angry == true or false
end

-- These callbacks have the same (target, user, slotId) convention as BasicAIActions.
function ST.Open(npc, user)
    if ST.nativeCheck and ST.nativeCheck(g_gameRules, npc) ~= 0 then return false end
    if not ST.Available(npc, user) then return false end
    if not XGenAIModule or not table.MakeFromType or not IsFemale then
        log('Required native bindings unavailable; no chat was started.')
        return false
    end
    local kind = 'dialog:chatRequest'
    local request = table.MakeFromType(kind, {
        alias = IsFemale(npc) and 'streettalk_female' or 'streettalk_male',
        metarole = 'NPC_ZDRAVI_HRACE',
        canBeDelayed = false,
        important = false,
        lookAtId = user.this.id
    })
    ST.pending = { npcId = npc.id, userId = user.id, expires = now() + 3 }
    ST.session = { npcId = npc.id, userId = user.id, npc = npc, user = user,
        key = tostring(npc.this.id), expires = now() + 30, angry = false }
    ST.cooldowns[tostring(npc.this.id)] = now() + ST.cooldownSeconds
    local ok, err = pcall(XGenAIModule.SendMessageToEntityData, npc.this.id, kind, request)
    if not ok then
        ST.pending = nil
        ST.session = nil
        log('Chat request failed: ' .. tostring(err))
        return false
    end
    Script.SetTimerForFunction(100, 'StreetTalk.AwaitChat')
    return true
end

function ST.AwaitChat()
    local pending = ST.pending
    if not pending then return end
    local npc = System.GetEntity(pending.npcId)
    local user = System.GetEntity(pending.userId)
    if not npc or not user or not npc.actor or not user.actor
        or now() > pending.expires or npc.actor:IsDead()
        or npc.actor:IsUnconscious() or user.soul:IsInCombatDanger()
        or user.soul:IsInTenseCircumstance()
        or not user.actor:CanInteractWith(npc.id) then
        ST.pending = nil
        ST.session = nil
        log('Chat request cancelled or timed out.')
        return
    end
    -- Request processing is asynchronous; do not assume that sending means playing.
    -- Never auto-accept: the public API has no request ID and a quest could have
    -- requested a chat in the meantime. Let the native Reply action arbitrate.
    if npc.actor:HasChatRequest() then
        ST.pending = nil
        log('Native Reply prompt available; confirm with the native chat button.')
    elseif npc.actor:CanChat(user.id) then
        ST.pending = nil
        log('Native chat prompt available.')
    else
        Script.SetTimerForFunction(100, 'StreetTalk.AwaitChat')
    end
end

function ST.Actions()
    local result = {}
    AddInteractorAction(result, false,
        Action():hint('Saluer / Provoquer'):action('streettalk_open')
            :hintType(AHT_PRESS):uiOrder(5):func(ST.Open)
            :interaction(inr_chatFollow):enabled(true)
            :actionMap('street_talk'):hintClass(AHC_CHAT))
    return result
end

function ST.SetControls(enabled)
    if not ActionMapManager or not ActionMapManager.EnableActionMap then return end
    if enabled and (not ST.controlsLoaded or not g_localActor) then enabled = false end
    if enabled and ActionMapManager.SetActionListener then
        ActionMapManager.SetActionListener('street_talk', g_localActor.id)
    end
    ActionMapManager.EnableActionMap('street_talk', enabled)
end

function ST.Install(rules)
    if not rules or rules.__streetTalkInstalled
        or type(rules.IsUsableForChat) ~= 'function'
        or type(rules.OnChatUsableMessage) ~= 'function' then return end
    local originalCheck = rules.IsUsableForChat
    ST.nativeCheck = originalCheck
    local originalMessage = rules.OnChatUsableMessage
    rules.IsUsableForChat = function(self, npc)
        local native = originalCheck(self, npc)
        if native ~= 0 then
            ST.SetControls(false)
            return native -- Quest chats and Follow take priority.
        end
        local ok, available = pcall(ST.Available, npc, g_localActor)
        return ok and available and 1 or 0
    end
    rules.OnChatUsableMessage = function(self, npc)
        if originalCheck(self, npc) ~= 0 then
            ST.SetControls(false)
            return originalMessage(self, npc)
        end
        local ok, available = pcall(ST.Available, npc, g_localActor)
        if ok and available then
            ST.focus = { npc = npc, seen = now() }
            g_localActor.player:AddLuaActions(ST.Actions())
            ST.SetControls(true)
        else
            ST.SetControls(false)
            return originalMessage(self, npc)
        end
    end
    rules.__streetTalkInstalled = true
    log('Native chat hooks installed (experimental).')
end

function ST.Tick()
    -- Hook the live rules object, not just a prototype copied into NPC classes.
    ST.Install(g_gameRules)
    if not ST.controlsLoaded and ActionMapManager and ActionMapManager.LoadFromXML then
        local ok = pcall(ActionMapManager.LoadFromXML, 'Libs/Config/street_talk.xml')
        ST.controlsLoaded = ok
    end
    local focus = ST.focus
    local enabled = false
    if focus and now() - focus.seen < 0.2 and ST.nativeCheck
        and g_gameRules and ST.nativeCheck(g_gameRules, focus.npc) == 0 then
        local ok, available = pcall(ST.Available, focus.npc, g_localActor)
        enabled = ok and available
    end
    ST.SetControls(enabled)
    Script.SetTimerForFunction(100, 'StreetTalk.Tick')
end

if Script and Script.SetTimerForFunction then
    Script.SetTimerForFunction(1000, 'StreetTalk.Tick')
end
