import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load('build')
controls = load('audit_controls')


def fixture(root):
    def put(path, body):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
    put(Path('Scripts/GameRules/SinglePlayer.lua'),
        'SinglePlayer={}\nfunction SinglePlayer:IsUsableForChat(obj) return 0 end\n')
    put(builder.BASE / 'bff_pozdravy_a_rozlouceni/bff_zdravi_hrace_chatem__kubenka.xml',
        '<Database><Response Role="HRAC"><Text StringName="bff__hrac_pochvalen_bud_nrmQ" '
        'Text="Greeting"/></Response></Database>')
    put(builder.BASE / 'combat/nadavani/skirmish_nadavaci_chat.xml',
        '<Database><Response Role="HRAC"><Text StringName="skir_henry_na_me_nemas_bLnx" '
        'Text="Taunt"/></Response></Database>')
    for suffix, graph in [('muz', 'zjednodusena_varianta_zdraveni'),
                          ('zena', 'zjednodusena_varianta_zdraveni_1')]:
        role = 'NPC_ZDRAVI_HRACE_' + suffix.upper()
        put(builder.REACTIONS / graph / (graph + '.xml'),
            '<Database><Skald><Dialog Name="original"><Ports/>'
            '<Dialogue Type="chat"><Decision Name="original"><Sequences>'
            '<Sequence Name="original" EndType="EndDialogue"><Elements>'
            f'<Response Role="{role}"><Text StringName="reply_{suffix}" '
            'Text="Nezdvořák..."/></Response>'
            f'<Response Role="{role}"><Text StringName="angry_{suffix}" '
            'Text="Jako vážně?!"/></Response></Elements></Sequence>'
            '</Sequences></Decision></Dialogue></Dialog></Skald></Database>')
        name = 'pozdravy_k_hraci_ve_svete__' + suffix
        put(builder.REACTIONS / name / (name + '.xml'),
            f'<Database><Response Role="{role}"><Text StringName="hello_{suffix}" '
            'Text="Zdravím."/></Response></Database>')


class BuildTests(unittest.TestCase):
    def test_package_preserves_original_and_orders_native_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'source')
            package = builder.build(root / 'source', root / 'out')
            before = package.read_bytes()
            self.assertEqual(before, builder.build(root / 'source', root / 'out').read_bytes())
            with zipfile.ZipFile(package) as outer:
                import io
                with zipfile.ZipFile(io.BytesIO(outer.read('street_talk/Data/street_talk.pak'))) as pak:
                    self.assertTrue(all(i.compress_type == zipfile.ZIP_STORED for i in pak.infolist()))
                    graphs = [n for n in pak.namelist() if n.startswith('Quests/')]
                    mapping = ET.fromstring(pak.read('Libs/Config/street_talk.xml'))
                    action = mapping.find('./actionmap/action')
                    self.assertEqual(action.get('name'), 'streettalk_open')
                    self.assertEqual(action.find('xboxpad').get('input'), 'xi_shoulderr')
                    rules = pak.read('Scripts/GameRules/SinglePlayer.lua')
                    original = (root / 'source/Scripts/GameRules/SinglePlayer.lua').read_bytes()
                    self.assertTrue(rules.startswith(original))
                    self.assertIn(b'StreetTalk.Install(SinglePlayer)', rules)
                    self.assertEqual(len(graphs), 2)
                    for name in graphs:
                        tree = ET.fromstring(pak.read(name))
                        self.assertIsNotNone(tree.find('.//Sequence[@Name="original"]'))
                        self.assertEqual(tree.find('.//Sequence[@Name="streettalk_alias_container"]').get('EntryCondition'), 'false')
                        choices = tree.findall('.//Decision[@Name="streettalk_menu"]/Sequences/Sequence')
                        self.assertEqual([c.get('ChatPosition') for c in choices], ['First', 'Second'])
                        self.assertEqual([c.find('UiPrompt').get('Text') for c in choices], ['Saluer', 'Provoquer'])
                        self.assertEqual([r.get('Role') for r in choices[0].findall('Elements/Response')][0], 'HRAC')
                        self.assertEqual(choices[1].get('Reputation'), 'greeting_decrease')
                        self.assertEqual(choices[0].get('EntryScript'), "StreetTalk.OnChoice('greet')")
                        self.assertIsNotNone(choices[1].find('.//Sequence[@Name="streettalk_angry"]'))
                report = json.loads(outer.read('street_talk/BUILD_REPORT.json'))
                self.assertEqual(report['status'], 'diagnostic_not_game_validated')

    def test_missing_voice_stops_build_without_partial_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root / 'source')
            p = next((root / 'source').rglob('bff_zdravi*.xml'))
            p.write_text('<Database/>')
            with self.assertRaises(ValueError):
                builder.build(root / 'source', root / 'out')
            self.assertFalse(list((root / 'out').glob('*.zip')))

    def test_duplicate_reference_is_rejected(self):
        tree = ET.fromstring('<Root><Response Role="HRAC"><Text StringName="x"/></Response>'
                             '<Response Role="HRAC"><Text StringName="x"/></Response></Root>')
        with self.assertRaises(ValueError):
            builder.response(tree, key='x')


class ControlTests(unittest.TestCase):
    def test_maps_holds_and_native_chat_are_reported_without_free_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'profile.xml'
            path.write_text('<profile><actionmap name="chat_init_interactor">'
                '<action name="chat_init_with_focus"><xbox input="xi_thumbr" onHold="1"/>'
                '</action></actionmap><actionmap name="combat"><action name="lock">'
                '<xbox input="xi_thumbr"/></action></actionmap></profile>')
            report = controls.audit([path])
            self.assertEqual(len(report['bindings']), 2)
            self.assertEqual(report['native_chat_bindings'][0]['button'], 'xi_thumbr')
            self.assertNotIn('xi_thumbr', report['not_seen_in_supplied_files'])
            self.assertEqual(report['status'], 'static_inventory_only')

    def test_pak_without_config_is_not_a_successful_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'empty.pak'
            builder.write_pak(path, {'unrelated.txt': b'hello'})
            with self.assertRaises(ValueError):
                controls.audit([path])
