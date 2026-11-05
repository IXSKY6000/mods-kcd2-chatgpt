from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

SETUP = '''
clock = 100
timers = {}
sent = {}
actions = {}
native = 0
nativeMessages = 0
useMessages = 0
logs = {}
System = {
  GetCurrTime = function() return clock end,
  LogAlways = function(message) logs[#logs+1]=message end,
  GetEntitiesInSphere = function() return nearby or {npc} end,
  GetEntity = function(id) if id == 1 then return user elseif id == 2 then return npc end end
}
Script = { SetTimerForFunction = function(ms, name) timers[#timers+1] = name end }
table.MakeFromType = function(kind, data) return data end
XGenAIModule = {SendMessageToEntityData = function(wuid, kind, data)
  sent[#sent+1] = {wuid=wuid, kind=kind, data=data}
end}
DialogModule = {IsSoulInDialog = function(id) return inDialog or false end}
IsFemale = function() return female or false end
function makeActor(id)
 return {
   id=id, this={id='wuid' .. id},
   GetWorldPos=function() return {x=0,y=0,z=0} end,
   human={IsInDialog=function() return humanDialog or false end,
          IsPickpocketing=function() return stealing or false end},
   actor={
     IsDead=function() return dead or false end,
     IsUnconscious=function() return unconscious or false end,
     CanInteractWith=function() return not far end,
     HasChatRequest=function() return requested or false end,
     HasAcceptedChat=function() return accepted or false end,
     CanChat=function() return canChat or false end,
     IsWaitingForDialogueReply=function() return waiting or false end,
     AcceptChatRequest=function() error('Must not auto-accept a possible quest chat') end,
     DoChat=function() error('Must not auto-start a possible quest chat') end
   },
   soul={
     IsInCombatDanger=function() return combat or false end,
     IsInTenseCircumstance=function() return tense or false end,
     IsInCombatMode=function() return combat or false end,
     IsDialogRestricted=function() return restricted or false end,
     ModifyPlayerReputation=function(self, kind) penalty=kind end
   },
   player={AddLuaActions=function(self, value) actions=value end,
     IsSitting=function() return sitting or false end,
     IsLaying=function() return laying or false end}
 }
end
user=makeActor(1)
npc=makeActor(2)
g_localActor=user
g_gameRules={
  IsUsableForChat=function() return native end,
  OnChatUsableMessage=function() nativeMessages=nativeMessages+1 end,
  IsUsable=function() return 1 end,
  OnUsableMessage=function() useMessages=useMessages+1 end
}
AHC_CHAT=2; AHC_BASIC=1; AHT_PRESS=1; inr_chatFollow=3
function Action()
  local result={}
  setmetatable(result,{__index=function(self,key)
    return function(self,value) self['_'..key]=value; return self end
  end})
  return result
end
function AddInteractorAction(output,firstFast,action) output[#output+1]=action end
'''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(SETUP)
        self.lua.execute((ROOT / 'src/Scripts/Mods/street_talk.lua').read_text())

    def evaluate(self, expression):
        return self.lua.eval(expression)

    def test_request_uses_native_chat_and_sex_specific_alias(self):
        for female, alias in [(False, 'streettalk_male'), (True, 'streettalk_female')]:
            self.lua.execute('StreetTalk.cooldowns={}; StreetTalk.pending=nil')
            self.lua.globals().female = female
            self.assertTrue(self.evaluate('StreetTalk.Open(npc,user)'))
            self.assertEqual(self.evaluate('sent[#sent].kind'), 'dialog:chatRequest')
            self.assertEqual(self.evaluate('sent[#sent].data.alias'), alias)
            self.assertEqual(self.evaluate('sent[#sent].data.metarole'), 'NPC_ZDRAVI_HRACE')
            self.assertEqual(self.evaluate('sent[#sent].wuid'), 'wuid2')

    def test_rejections_and_missing_capability(self):
        for flag in ['dead', 'unconscious', 'far', 'combat', 'tense', 'restricted',
                     'inDialog', 'requested', 'accepted', 'canChat', 'waiting',
                     'stealing', 'sitting', 'laying', 'humanDialog']:
            self.lua.globals()[flag] = True
            self.assertFalse(self.evaluate('StreetTalk.Available(npc,user)'), flag)
            self.lua.globals()[flag] = False
        self.lua.execute('npc.human=nil')
        self.assertFalse(self.evaluate('StreetTalk.Available(npc,user)'))
        self.lua.execute('npc.human={}; DialogModule=nil')
        self.assertFalse(self.evaluate('StreetTalk.Available(npc,user)'))

    def test_native_quest_and_follow_actions_have_priority(self):
        self.lua.execute('StreetTalk.Install(g_gameRules); native=1')
        self.assertEqual(self.evaluate('g_gameRules:IsUsableForChat(npc)'), 1)
        self.lua.execute('g_gameRules:OnChatUsableMessage(npc)')
        self.assertEqual(self.evaluate('nativeMessages'), 1)
        self.assertEqual(self.evaluate('#sent'), 0)

    def test_no_duplicate_hook_and_no_forced_dialogue(self):
        self.lua.execute('StreetTalk.Install(g_gameRules); saved=g_gameRules.IsUsableForChat; '
                         'StreetTalk.Install(g_gameRules)')
        self.assertTrue(self.evaluate('saved == g_gameRules.IsUsableForChat'))
        self.assertEqual(self.evaluate('g_gameRules:IsUsableForChat(npc)'), 1)
        self.lua.execute('StreetTalk.Open(npc,user); requested=true; StreetTalk.AwaitChat()')
        self.assertTrue(self.evaluate('StreetTalk.pending == nil'))
        self.assertEqual(self.evaluate('#sent'), 1)

    def test_cooldown_and_pending_timeout(self):
        self.assertTrue(self.evaluate('StreetTalk.Open(npc,user)'))
        self.assertFalse(self.evaluate('StreetTalk.Open(npc,user)'))
        self.lua.execute('clock=104; StreetTalk.AwaitChat()')
        self.assertTrue(self.evaluate('StreetTalk.pending == nil'))
        self.assertFalse(self.evaluate('StreetTalk.Available(npc,user)'))
        self.lua.execute('clock=116')
        self.assertTrue(self.evaluate('StreetTalk.Available(npc,user)'))

    def test_failed_send_clears_pending(self):
        self.lua.execute('XGenAIModule.SendMessageToEntityData=function() error("unavailable") end')
        self.assertFalse(self.evaluate('StreetTalk.Open(npc,user)'))
        self.assertTrue(self.evaluate('StreetTalk.pending == nil'))

    def test_target_despawn_cancels_request(self):
        self.lua.execute('StreetTalk.Open(npc,user); npc=nil; StreetTalk.AwaitChat()')
        self.assertTrue(self.evaluate('StreetTalk.pending == nil'))

    def test_greeting_cooldown_is_per_npc_and_not_reset_by_opening(self):
        self.lua.execute("StreetTalk.Open(npc,user); StreetTalk.OnChoice('greet')")
        self.assertFalse(self.evaluate("StreetTalk.OnChoice('greet')"))
        self.lua.execute('clock=103; StreetTalk.pending=nil; StreetTalk.Open(npc,user)')
        self.assertTrue(self.evaluate("StreetTalk.CanChoose('greet')"))
        self.assertTrue(self.evaluate("StreetTalk.OnChoice('greet')"))
        self.lua.execute('clock=106; StreetTalk.pending=nil; StreetTalk.Open(npc,user)')
        self.assertFalse(self.evaluate("StreetTalk.CanChoose('greet')"))
        self.assertTrue(self.evaluate("StreetTalk.CanChoose('antagonize')"))
        self.lua.execute('clock=194; StreetTalk.pending=nil; StreetTalk.Open(npc,user)')
        self.assertTrue(self.evaluate("StreetTalk.CanChoose('greet')"))

    def test_three_provocations_cause_anger_and_refusal(self):
        for time in (100, 116, 132):
            self.lua.execute(f'clock={time}; StreetTalk.pending=nil; StreetTalk.Open(npc,user)')
            self.assertTrue(self.evaluate("StreetTalk.OnChoice('antagonize')"))
        self.assertTrue(self.evaluate('StreetTalk.IsAngry()'))
        self.assertEqual(self.evaluate('penalty'), 'quest_decrease_2_minor')
        self.lua.execute('clock=160')
        self.assertFalse(self.evaluate('StreetTalk.Available(npc,user)'))
        self.lua.execute('clock=313; StreetTalk.pending=nil')
        self.assertTrue(self.evaluate('StreetTalk.Available(npc,user)'))

    def test_provocation_count_decays_and_different_npcs_are_independent(self):
        self.lua.execute("StreetTalk.Open(npc,user); StreetTalk.OnChoice('antagonize'); "
                         'clock=300; StreetTalk.pending=nil; StreetTalk.Open(npc,user); '
                         "StreetTalk.OnChoice('antagonize')")
        self.assertEqual(self.evaluate("StreetTalk.people['wuid2'].strikes"), 1)
        self.lua.execute('clock=316; StreetTalk.pending=nil; npc=makeActor(3); '
                         'StreetTalk.Open(npc,user)')
        self.assertTrue(self.evaluate("StreetTalk.people['wuid3'] == nil"))

    def test_other_npc_quick_reply_preempts_mod(self):
        self.lua.execute('other=makeActor(3); '
                         'other.actor.IsWaitingForDialogueReply=function() return true end; '
                         'nearby={npc,other}')
        self.assertFalse(self.evaluate('StreetTalk.Open(npc,user)'))
        self.assertEqual(self.evaluate('#sent'), 0)

    def test_native_action_appearing_after_render_preempts_r1_callback(self):
        self.lua.execute('StreetTalk.Install(g_gameRules)')
        self.assertEqual(self.evaluate('g_gameRules:IsUsableForChat(npc)'), 1)
        self.lua.execute('native=1')
        self.assertFalse(self.evaluate('StreetTalk.Open(npc,user)'))
        self.assertEqual(self.evaluate('#sent'), 0)

    def test_combat_starting_with_menu_open_blocks_choice(self):
        self.lua.execute('StreetTalk.Open(npc,user); combat=true')
        self.assertFalse(self.evaluate("StreetTalk.OnChoice('antagonize')"))
        self.assertTrue(self.evaluate('penalty == nil'))

    def test_ordinary_interaction_preserves_native_and_adds_r1(self):
        self.lua.execute('StreetTalk.Install(g_gameRules); g_gameRules:OnUsableMessage(npc)')
        self.assertEqual(self.evaluate('useMessages'), 1)
        self.assertEqual(self.evaluate('actions[1]._action'), 'streettalk_open')
        self.assertEqual(self.evaluate('actions[1]._hintClass'), 1)
        self.lua.execute('native=1; actions={}; g_gameRules:OnUsableMessage(npc)')
        self.assertEqual(self.evaluate('useMessages'), 2)
        self.assertEqual(self.evaluate('#actions'), 0)

    def test_timer_reschedules_after_native_failure_and_reports_it(self):
        self.lua.execute('StreetTalk.Update=function() error("native unavailable") end; '
                         'StreetTalk.Tick()')
        self.assertEqual(self.evaluate('timers[#timers]'), 'StreetTalk.Tick')
        self.assertTrue(self.evaluate("string.find(logs[#logs], 'native unavailable') ~= nil"))

    def test_eligibility_errors_are_reported_once(self):
        self.lua.execute('npc.actor.IsDead=function() error("binding failed") end')
        self.assertFalse(self.evaluate('StreetTalk.CheckAvailable(npc,user)'))
        count = self.evaluate('#logs')
        self.assertFalse(self.evaluate('StreetTalk.CheckAvailable(npc,user)'))
        self.assertEqual(self.evaluate('#logs'), count)
        self.assertTrue(self.evaluate("string.find(logs[#logs], 'binding failed') ~= nil"))

    def test_native_numeric_zero_does_not_mean_dead_or_in_combat(self):
        self.lua.execute('''
          for _,entity in ipairs({npc,user}) do
            for _,module in ipairs({'actor','human','soul','player'}) do
              for name,method in pairs(entity[module]) do
                if string.match(name,'^Is') or string.match(name,'^Has')
                  or name=='CanChat' then entity[module][name]=function() return 0 end end
              end
            end
            entity.actor.CanInteractWith=function() return 1 end
          end
          DialogModule.IsSoulInDialog=function() return false end
        ''')
        self.assertTrue(self.evaluate('StreetTalk.CheckAvailable(npc,user)'))
        self.lua.execute('npc.actor.IsDead=function() return 1 end')
        self.assertFalse(self.evaluate('StreetTalk.CheckAvailable(npc,user)'))

    def test_startup_identifies_build_before_a_save_is_loaded(self):
        self.assertTrue(self.evaluate("string.find(logs[1], '0.2.1 diagnostic') ~= nil"))
