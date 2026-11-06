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
        or not System.GetEntitiesInSphere or not user.GetWorldPos then
        ST.Report('reply_api_missing', 'Blocked: quick-reply readiness binding unavailable.')
        return true
    end
    if ST.Flag(user.actor:IsWaitingForDialogueReply()) then return true end
    for _, other in pairs(System.GetEntitiesInSphere(user:GetWorldPos(), 35) or {}) do
        if other.actor and other.human then
            if not other.actor.IsWaitingForDialogueReply then
                ST.Report('nearby_reply_api_missing', 'Blocked: nearby actor reply status unavailable.')
                return true
            end
            if ST.Flag(other.actor:IsWaitingForDialogueReply()) or ST.Flag(other.actor:HasChatRequest())
                or ST.Flag(other.actor:HasAcceptedChat()) then return true end
        end
    end
    return false
end

function ST.ContextSafe(npc, user)
    if not user.player or not user.human or not user.player.IsSitting
        or not user.player.IsLaying or not user.human.IsPickpocketing
        or not user.human.IsInDialog or not npc.human.IsInDialog then
        ST.Report('context_api_missing', 'Blocked: sitting/lying/pickpocket/dialogue binding unavailable.')
        return false
    end
    if ST.Flag(user.player:IsSitting()) or ST.Flag(user.player:IsLaying())
        or ST.Flag(user.human:IsPickpocketing()) then return false end
    if ST.Flag(user.soul:IsInCombatDanger()) or ST.Flag(user.soul:IsInTenseCircumstance())
        or ST.Flag(user.soul:IsInCombatMode()) or ST.Flag(npc.soul:IsInCombatMode())
        or ST.Flag(npc.soul:IsInCombatDanger()) or ST.Flag(npc.soul:IsInTenseCircumstance()) then return false end
    if ST.Flag(user.human:IsInDialog()) or ST.Flag(npc.human:IsInDialog()) then return false end
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

-- Some engine bindings return 0/1; Lua treats numeric zero as truthy.
function ST.Flag(value)
    if type(value) == 'boolean' then return value end
    if type(value) == 'number' then return value ~= 0 end
    error('Unsupported native boolean result: ' .. type(value))
end

function ST.Report(key, message)
    ST.reported = ST.reported or {}
    if ST.reported[key] then return end
    ST.reported[key] = true
    log(message)
end

function ST.CheckAvailable(npc, user)
    local ok, available = pcall(ST.Available, npc, user)
    if not ok then
        ST.Report('availability_error:' .. tostring(available),
            'Eligibility error (interaction disabled): ' .. tostring(available))
        return false
    end
    return available
end

function ST.Eligible(npc, user)
    if not npc or not user or npc == user or not npc.human or not npc.actor
        or not npc.soul or not npc.this or not user.actor or not user.soul
        or not user.this then return false end
    if ST.Flag(npc.actor:IsDead()) or ST.Flag(npc.actor:IsUnconscious())
        or ST.Flag(user.actor:IsDead()) or ST.Flag(user.actor:IsUnconscious()) then return false end
    if not ST.ContextSafe(npc, user) or ST.NativeReplyBusy(user) then return false end
    if ST.Flag(user.soul:IsInCombatDanger()) or ST.Flag(user.soul:IsInTenseCircumstance())
        or ST.Flag(npc.soul:IsInCombatMode()) then return false end
    if not ST.Flag(user.actor:CanInteractWith(npc.id)) then return false end
    if ST.Flag(npc.soul:IsDialogRestricted(user.id)) then return false end
    -- Fail closed if the current runtime cannot check dialogue ownership.
    if not DialogModule or not DialogModule.IsSoulInDialog then
        ST.Report('dialog_api_missing', 'Blocked: DialogModule.IsSoulInDialog unavailable.')
        return false
    end
    if ST.Flag(DialogModule.IsSoulInDialog(user.this.id))
        or ST.Flag(DialogModule.IsSoulInDialog(npc.this.id)) then return false end
    -- CanChat only means a native chat is available. It does not mean a reply
    -- is currently requested. Preserve actual requests/accepted conversations.
    if ST.Flag(npc.actor:HasChatRequest()) or ST.Flag(npc.actor:HasAcceptedChat()) then return false end
    ST.Report('eligible', 'At least one NPC passed the eligibility checks.')
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
    if ST.Flag(npc.actor:IsDead()) or ST.Flag(npc.actor:IsUnconscious()) or ST.Flag(user.actor:IsDead())
        or ST.Flag(user.actor:IsUnconscious()) or ST.Flag(user.soul:IsInCombatDanger())
        or ST.Flag(user.soul:IsInTenseCircumstance()) or ST.Flag(user.soul:IsInCombatMode())
        or ST.Flag(npc.soul:IsInCombatMode()) or ST.Flag(npc.soul:IsInCombatDanger())
        or ST.Flag(npc.soul:IsInTenseCircumstance()) or ST.Flag(user.player:IsSitting())
        or ST.Flag(user.player:IsLaying()) or ST.Flag(user.human:IsPickpocketing())
        or ST.Flag(npc.soul:IsDialogRestricted(user.id))
        or not ST.Flag(user.actor:CanInteractWith(npc.id)) then return false end
    local state = ST.people[session.key] or {}
    if now() < (state.angryUntil or 0) or now() < ST.globalUntil then return false end
    if kind == 'greet' then return now() >= (state.greetUntil or 0) end
    return kind == 'antagonize'
end

function ST.OnChoice(kind)
    if not ST.CanChoose(kind) then
        ST.Report('choice_rejected', 'Choice callback rejected by session/context checks.')
        return false
    end
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
        ST.cooldowns[session.key] = now() + ST.cooldownSeconds
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
    log('Choice committed: ' .. kind)
    return true
end

-- Dialogue conditions use the engine expression language, not arbitrary Lua.
function ST.CanGreet() return ST.CanChoose('greet') end
function ST.CanAntagonize() return ST.CanChoose('antagonize') end

function ST.IsAngry()
    return ST.session and ST.session.angry == true or false
end

-- These callbacks have the same (target, user, slotId) convention as BasicAIActions.
function ST.Open(npc, user)
    -- Recheck active replies at the press, not the mere presence of native hints.
    if not ST.CheckAvailable(npc, user) then
        ST.SetControls(false)
        return false
    end
    if not XGenAIModule or not table.MakeFromType or not IsFemale then
        log('Required native bindings unavailable; no chat was started.')
        return false
    end
    local kind = 'dialog:chatRequest'
    local built, request = pcall(table.MakeFromType, kind, {
        alias = IsFemale(npc) and 'streettalk_female' or 'streettalk_male',
        metarole = 'NPC_ZDRAVI_HRACE',
        canBeDelayed = false,
        important = false,
        lookAtId = user.this.id
    })
    if not built then
        log('Unable to create native chat request: ' .. tostring(request))
        return false
    end
    log('Sending native chat request: alias=' .. request.alias)
    ST.pending = { npcId = npc.id, userId = user.id, expires = now() + 3 }
    ST.session = { npcId = npc.id, userId = user.id, npc = npc, user = user,
        key = tostring(npc.this.id), expires = now() + 30, angry = false }
    -- Opening/cancelling is not a provocation: reserve the 15s delay for a
    -- committed antagonize choice. Pending/native conversations still block R1.
    ST.cooldowns[tostring(npc.this.id)] = now() + 2
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
        or now() > pending.expires or ST.Flag(npc.actor:IsDead())
        or ST.Flag(npc.actor:IsUnconscious()) or ST.Flag(user.soul:IsInCombatDanger())
        or ST.Flag(user.soul:IsInTenseCircumstance())
        or not ST.Flag(user.actor:CanInteractWith(npc.id)) then
        ST.pending = nil
        ST.session = nil
        log('Chat request cancelled or timed out.')
        return
    end
    -- Request processing is asynchronous; do not assume that sending means playing.
    -- Never auto-accept: the public API has no request ID and a quest could have
    -- requested a chat in the meantime. Let the native Reply action arbitrate.
    if ST.Flag(npc.actor:HasChatRequest()) then
        ST.pending = nil
        log('Native Reply prompt available; confirm with the native chat button.')
    elseif ST.Flag(npc.actor:HasAcceptedChat())
        or ST.Flag(npc.actor:IsWaitingForDialogueReply()) then
        ST.pending = nil
        log('Native chat prompt available.')
    else
        Script.SetTimerForFunction(100, 'StreetTalk.AwaitChat')
    end
end

function ST.Actions(hintClass)
    local result = {}
    AddInteractorAction(result, false,
        Action():hint('@ui_streettalk_open'):action('streettalk_open')
            :hintType(AHT_PRESS):uiOrder(5):func(ST.Open)
            :interaction(inr_chatFollow):enabled(true)
            :actionMap('street_talk'):hintClass(hintClass or AHC_CHAT))
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
    local originalMessage = rules.OnChatUsableMessage
    -- Also expose the opener through the ordinary NPC interaction path. The
    -- engine may not query the chat interactor for a NPC that has no native chat.
    local originalUseCheck = rules.IsUsable
    local originalUseMessage = rules.OnUsableMessage
    rules.IsUsableForChat = function(self, npc)
        local native = originalCheck(self, npc)
        if ST.CheckAvailable(npc, g_localActor) then return 1 end
        ST.SetControls(false)
        return native -- Keep every native interaction available when ST is blocked.
    end
    rules.OnChatUsableMessage = function(self, npc)
        -- A nonempty GetChatActions may just contain Follow or a chat opener.
        -- R1 goes to ST when safe; active native replies always go to the game.
        if ST.CheckAvailable(npc, g_localActor) then
            ST.focus = { npc = npc, seen = now() }
            g_localActor.player:AddLuaActions(ST.Actions())
            ST.SetControls(true)
        else
            ST.SetControls(false)
            return originalMessage(self, npc)
        end
    end
    if type(originalUseCheck) == 'function' and type(originalUseMessage) == 'function' then
        rules.IsUsable = function(self, npc)
            local native = originalUseCheck(self, npc)
            if native ~= 0 then return native end
            if ST.CheckAvailable(npc, g_localActor) then
                return 1
            end
            return native
        end
        rules.OnUsableMessage = function(self, npc)
            originalUseMessage(self, npc)
            if ST.CheckAvailable(npc, g_localActor) then
                ST.focus = { npc = npc, seen = now() }
                g_localActor.player:AddLuaActions(ST.Actions(AHC_BASIC))
                ST.SetControls(true)
                ST.Report('normal_hint', 'R1 opener supplied through ordinary NPC interaction.')
            else
                ST.SetControls(false)
            end
        end
    end
    rules.__streetTalkInstalled = true
    log('Native chat hooks installed (experimental).')
end

function ST.Update()
    -- Hook the live rules object, not just a prototype copied into NPC classes.
    if not g_localActor then
        ST.Report('waiting_player', 'Waiting for a loaded game/player.')
        return
    end
    ST.Report('player_ready', 'Player available; starting runtime checks.')
    ST.Install(g_gameRules)
    if not g_gameRules or not g_gameRules.__streetTalkInstalled then
        ST.Report('rules_missing', 'Game rules callbacks not accessible; waiting for class hook.')
    end
    if not ST.controlsLoaded and ActionMapManager and ActionMapManager.LoadFromXML then
        local ok = pcall(ActionMapManager.LoadFromXML, 'Libs/Config/street_talk.xml')
        ST.controlsLoaded = ok
        ST.Report('controls_load:' .. tostring(ok),
            'R1 map load call completed=' .. tostring(ok) .. ' (check engine XML errors too).')
    end
    local focus = ST.focus
    local enabled = false
    if focus and now() - focus.seen < 0.2 then
        enabled = ST.CheckAvailable(focus.npc, g_localActor)
    end
    ST.SetControls(enabled)
end

function ST.Tick()
    -- Always reschedule, even when a native API raises an error. Previously a
    -- single error permanently stopped all subsequent startup/input checks.
    local ok, err = pcall(ST.Update)
    if not ok then
        ST.Report('update_error:' .. tostring(err), 'Runtime update error: ' .. tostring(err))
        pcall(ST.SetControls, false)
    end
    Script.SetTimerForFunction(ok and 100 or 1000, 'StreetTalk.Tick')
end

function ST.OnGameplayStarted()
    ST.Report('gameplay_event', 'OnGameplayStarted received.')
    local ok, err = pcall(ST.Update)
    if not ok then ST.Report('event_error', 'Gameplay startup error: ' .. tostring(err)) end
end

log('Script loaded: 0.2.3 diagnostic build; gameplay not yet validated.')
ST.Install(SinglePlayer)
if UIAction and UIAction.RegisterEventSystemListener then
    local ok, err = pcall(UIAction.RegisterEventSystemListener,
        ST, 'System', 'OnGameplayStarted', 'OnGameplayStarted')
    if not ok then log('Gameplay event registration failed: ' .. tostring(err)) end
end
if Script and Script.SetTimerForFunction then
    Script.SetTimerForFunction(1000, 'StreetTalk.Tick')
else
    log('ERROR: Script.SetTimerForFunction unavailable; no polling loop was started.')
end
