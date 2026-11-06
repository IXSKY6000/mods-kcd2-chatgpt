"""Build experimental native-chat overrides from the user's extracted Scripts.pak.

No audio or original game XML is stored in this repository. Python 3.10+ only.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
BASE = Path('Quests/Final/Barbora/open_world')
REACTIONS = BASE / 'reakce_na_stav_hrace'


def read(root: Path, path: Path) -> ET.Element:
    return ET.parse(root / path).getroot()


def response(root: ET.Element, *, key: str | None = None,
             role: str | None = None, text: str | None = None) -> ET.Element:
    matches = []
    for item in root.findall('.//Response'):
        line = item.find('Text')
        if line is None:
            continue
        if key is not None and line.get('StringName') != key:
            continue
        if role is not None and item.get('Role') != role:
            continue
        if text is not None and line.get('Text', '').strip() != text:
            continue
        matches.append(item)
    if len(matches) != 1:
        raise ValueError(f'Expected one voice reference: {key or text!r}; found {len(matches)}')
    # Keep the original StringName and Role. Strip situational animations and scripts.
    result = ET.Element('Response', {k: v for k, v in matches[0].attrib.items()
        if k in ('Role', 'ReferenceLength', 'StartDelay', 'EndDelay', 'Volume')})
    result.append(copy.deepcopy(matches[0].find('Text')))
    return result


def reply_pool(source: ET.Element, name: str, prefix: str) -> ET.Element:
    """Keep native voice selection/category metadata instead of forcing one take."""
    matches = source.findall(f'.//Decision[@Name="{name}"]')
    if len(matches) != 1:
        raise ValueError(f'Expected one native reply pool: {name}')
    result = copy.deepcopy(matches[0])
    for sequence in result.findall('.//Sequence'):
        if sequence.get('EndType') != 'EndDialogue' or sequence.find('Triggers') is not None:
            raise ValueError('Reply pool contains nonterminal gameplay logic')
        if any(k.endswith('Script') for k in sequence.attrib):
            raise ValueError('Reply pool contains gameplay scripts')
    for node in result.iter():
        if node.tag in ('Decision', 'Sequence'):
            node.set('Name', prefix + '_' + node.get('Name', 'node'))
    result.set('Autoselect', 'true')
    return result


def xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def patch_dialog(source: ET.Element, gender: str, lines: dict) -> ET.Element:
    result = copy.deepcopy(source)
    dialogue = result.find('./Skald/Dialog/Dialogue')
    if dialogue is None or dialogue.get('Type') != 'chat':
        raise ValueError('Unsupported game data: expected a native chat dialogue')
    initial = dialogue.find('Decision/Sequences')
    if initial is None or result.findall('.//Decision[@Alias="streettalk_' + gender + '"]'):
        raise ValueError('Missing entry decision or data already patched')
    # An alias addresses this nested decision directly. Normal greetings never enter
    # this false branch; their original conditions, ports and content stay intact.
    branch = ET.SubElement(initial, 'Sequence', {
        'Name': 'streettalk_alias_container', 'EntryCondition': 'false',
        'EndType': 'Decision'})
    decision = ET.SubElement(branch, 'Decision', {
        'Name': 'streettalk_menu', 'Priority': 'General',
        'Alias': 'streettalk_' + gender, 'TimeLimit': '0'})
    choices = ET.SubElement(decision, 'Sequences')
    for kind, position, label in [('greet', 'First', 'Saluer'),
                                  ('antagonize', 'Second', 'Provoquer')]:
        method = 'CanGreet' if kind == 'greet' else 'CanAntagonize'
        attrs = {'Name': 'streettalk_' + kind, 'EndType': 'Decision',
                 'ChatPosition': position,
                 'GrayOutIfSequencesUsed': 'Never',
                 'EntryCondition': f"CallScriptFunctionInTable('StreetTalk','{method}')",
                 'ExitScript': f"StreetTalk.OnChoice('{kind}')"}
        if kind == 'antagonize':
            attrs['Reputation'] = 'greeting_decrease'
            attrs['EndType'] = 'Decision'
        sequence = ET.SubElement(choices, 'Sequence', attrs)
        ET.SubElement(sequence, 'UiPrompt', {
            'StringName': 'ui_streettalk_' + kind, 'Text': label})
        elements = ET.SubElement(sequence, 'Elements')
        elements.append(copy.deepcopy(lines[kind]['henry']))
        if kind == 'greet':
            sequence.append(copy.deepcopy(lines[kind]['pool']))
        else:
            reaction = ET.SubElement(sequence, 'Decision', {
                'Name': 'streettalk_reaction', 'Autoselect': 'true', 'Priority': 'General'})
            reactions = ET.SubElement(reaction, 'Sequences')
            for angry, condition in [(False, "!CallScriptFunctionInTable('StreetTalk','IsAngry')"),
                                     (True, "CallScriptFunctionInTable('StreetTalk','IsAngry')")]:
                item = ET.SubElement(reactions, 'Sequence', {
                    'Name': 'streettalk_angry' if angry else 'streettalk_irritated',
                    'EntryCondition': condition, 'EndType': 'Decision'})
                body = ET.SubElement(item, 'Elements')
                ET.SubElement(body, 'Response', {'Role': lines[kind]['npc_role']})
                pool = copy.deepcopy(lines[kind]['pool'])
                for node in pool.iter():
                    if node.tag in ('Decision', 'Sequence'):
                        node.set('Name', ('angry_' if angry else 'irritated_') + node.get('Name'))
                item.append(pool)
    return result


def write_pak(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, content)


def build(scripts_root: Path, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    # Stay inside the original reakce_na_stav_hrace voice namespace. StringName
    # alone cannot relocate audio from the BFF/combat namespaces used before.
    henry_greet_path = REACTIONS / 'npc_zdravi_hrace_chatem__straz/npc_zdravi_hrace_chatem__straz.xml'
    henry_greet = response(read(scripts_root, henry_greet_path),
                           key='npc__henry_bud_zdrav_KYdF')
    rules_path = Path('Scripts/GameRules/SinglePlayer.lua')
    rules = (scripts_root / rules_path).read_bytes()
    # Install at class definition time, before the engine can cache callbacks.
    # Keep the original file byte-for-byte and append only this bridge.
    if b'function SinglePlayer:IsUsableForChat' not in rules:
        raise ValueError('Unsupported SinglePlayer script; cannot install the early hook')
    entries = {rules_path.as_posix(): rules + b'\n\n-- Street Talk early class hook\n'
               b'if StreetTalk and StreetTalk.Install then StreetTalk.Install(SinglePlayer) end\n',
               'Scripts/Mods/street_talk.lua':
               (PROJECT / 'src/Scripts/Mods/street_talk.lua').read_bytes(),
               'Libs/Config/street_talk.xml':
               (PROJECT / 'src/Libs/Config/street_talk.xml').read_bytes()}
    report = {'status': 'diagnostic_not_game_validated', 'input_sha256': {
                  rules_path.as_posix(): hashlib.sha256(rules).hexdigest(),
                  henry_greet_path.as_posix(): hashlib.sha256((scripts_root / henry_greet_path).read_bytes()).hexdigest()},
              'voice_namespace': 'reakce_na_stav_hrace',
              'audio_resolution_status': 'references_repaired_not_auditioned',
              'voice_references': {}, 'controller': 'R1_xi_shoulderr_engine_test_pending'}
    for gender, suffix, graph in [
        ('male', 'muz', 'zjednodusena_varianta_zdraveni'),
        ('female', 'zena', 'zjednodusena_varianta_zdraveni_1')]:
        path = REACTIONS / graph / (graph + '.xml')
        source = read(scripts_root, path)
        role = 'NPC_ZDRAVI_HRACE_' + suffix.upper()
        greet_path = REACTIONS / ('pozdravy_k_hraci_ve_svete__' + suffix)
        greetings = read(scripts_root, greet_path / (greet_path.name + '.xml'))
        greeting_source = greet_path / (greet_path.name + '.xml')
        report['input_sha256'][greeting_source.as_posix()] = hashlib.sha256(
            (scripts_root / greeting_source).read_bytes()).hexdigest()
        henry_taunt = response(source, key=(
            'zjed_hrac_starej_se_o_svy_IfYh' if gender == 'male'
            else 'zjed_hrac_starej_se_o_svy_jLKM'))
        lines = {
            'greet': {'henry': henry_greet,
                      'pool': reply_pool(greetings, 'dec57', 'streettalk_greetings')},
            'antagonize': {'henry': henry_taunt,
                          'npc_role': role,
                          'pool': reply_pool(source, 'dec2', 'streettalk_replies')}}
        entries[path.as_posix()] = xml_bytes(patch_dialog(source, gender, lines))
        report['input_sha256'][path.as_posix()] = hashlib.sha256(
            (scripts_root / path).read_bytes()).hexdigest()
        report['voice_references'][gender] = {
            k: {'henry': pair['henry'].find('Text').get('StringName'),
                'npc_candidates': [t.get('StringName') for t in pair['pool'].findall('.//Response/Text')]}
            for k, pair in lines.items()}
    localization = ET.Element('Table')
    for key, label in [('open', 'Parler'), ('greet', 'Saluer'), ('antagonize', 'Provoquer')]:
        row = ET.SubElement(localization, 'Row')
        for cell in ['ui_streettalk_' + key, label, label]:
            ET.SubElement(row, 'Cell').text = cell
    # Build atomically: missing/ambiguous references never produce a new partial ZIP.
    with tempfile.TemporaryDirectory(dir=output) as temp:
        folder = Path(temp) / 'street_talk'
        (folder / 'Data').mkdir(parents=True)
        (folder / 'Localization').mkdir()
        (folder / 'mod.manifest').write_bytes((PROJECT / 'src/mod.manifest').read_bytes())
        write_pak(folder / 'Data/street_talk.pak', entries)
        for language in ('French', 'English'):
            write_pak(folder / f'Localization/{language}_xml.pak',
                      {'text__street_talk.xml': xml_bytes(localization)})
        (folder / 'BUILD_REPORT.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (folder / 'LIRE_AVANT_INSTALLATION.md').write_bytes(
            (PROJECT / 'docs/VALIDATION.md').read_bytes())
        package = output / 'street_talk-prototype.zip'
        staging = Path(temp) / 'package.zip'
        write_pak(staging, {p.relative_to(Path(temp)).as_posix(): p.read_bytes()
                            for p in folder.rglob('*') if p.is_file()})
        staging.replace(package)
    return package


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scripts-root', required=True, type=Path,
                        help='Extracted Scripts.pak directory containing Quests/')
    parser.add_argument('--output', type=Path, default=PROJECT / 'dist')
    args = parser.parse_args()
    try:
        print(build(args.scripts_root, args.output))
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, f'Build stopped: {error}\n')
