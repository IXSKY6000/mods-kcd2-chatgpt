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
    result = ET.Element('Response', {'Role': matches[0].get('Role')})
    result.append(copy.deepcopy(matches[0].find('Text')))
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
        attrs = {'Name': 'streettalk_' + kind, 'EndType': 'EndDialogue',
                 'ChatPosition': position,
                 'EntryCondition': f"StreetTalk.CanChoose('{kind}')",
                 'EntryScript': f"StreetTalk.OnChoice('{kind}')"}
        if kind == 'antagonize':
            attrs['Reputation'] = 'greeting_decrease'
            attrs['EndType'] = 'Decision'
        sequence = ET.SubElement(choices, 'Sequence', attrs)
        ET.SubElement(sequence, 'UiPrompt', {
            'StringName': 'ui_streettalk_' + kind, 'Text': label})
        elements = ET.SubElement(sequence, 'Elements')
        elements.append(copy.deepcopy(lines[kind]['henry']))
        if kind == 'greet':
            elements.append(copy.deepcopy(lines[kind]['npc']))
        else:
            reaction = ET.SubElement(sequence, 'Decision', {
                'Name': 'streettalk_reaction', 'Autoselect': 'true', 'Priority': 'General'})
            reactions = ET.SubElement(reaction, 'Sequences')
            for angry, condition in [(False, 'not StreetTalk.IsAngry()'),
                                     (True, 'StreetTalk.IsAngry()')]:
                item = ET.SubElement(reactions, 'Sequence', {
                    'Name': 'streettalk_angry' if angry else 'streettalk_irritated',
                    'EntryCondition': condition, 'EndType': 'EndDialogue'})
                body = ET.SubElement(item, 'Elements')
                body.append(copy.deepcopy(lines[kind]['angry' if angry else 'npc']))
    return result


def write_pak(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, content)


def build(scripts_root: Path, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    henry_greet = response(read(scripts_root,
        BASE / 'bff_pozdravy_a_rozlouceni/bff_zdravi_hrace_chatem__kubenka.xml'),
        key='bff__hrac_pochvalen_bud_nrmQ')
    henry_taunt = response(read(scripts_root,
        BASE / 'combat/nadavani/skirmish_nadavaci_chat.xml'),
        key='skir_henry_na_me_nemas_bLnx')
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
                  rules_path.as_posix(): hashlib.sha256(rules).hexdigest()},
              'voice_references': {}, 'controller': 'R1_xi_shoulderr_engine_test_pending'}
    for gender, suffix, graph in [
        ('male', 'muz', 'zjednodusena_varianta_zdraveni'),
        ('female', 'zena', 'zjednodusena_varianta_zdraveni_1')]:
        path = REACTIONS / graph / (graph + '.xml')
        source = read(scripts_root, path)
        role = 'NPC_ZDRAVI_HRACE_' + suffix.upper()
        greet_path = REACTIONS / ('pozdravy_k_hraci_ve_svete__' + suffix)
        greetings = read(scripts_root, greet_path / (greet_path.name + '.xml'))
        lines = {
            'greet': {'henry': henry_greet,
                      'npc': response(greetings, role=role, text='Zdravím.')},
            'antagonize': {'henry': henry_taunt,
                          'npc': response(source, role=role, text='Nezdvořák...'),
                          'angry': response(source, role=role, text='Jako vážně?!')}}
        entries[path.as_posix()] = xml_bytes(patch_dialog(source, gender, lines))
        report['input_sha256'][path.as_posix()] = hashlib.sha256(
            (scripts_root / path).read_bytes()).hexdigest()
        report['voice_references'][gender] = {
            k: {speaker: node.find('Text').get('StringName')
                for speaker, node in pair.items()} for k, pair in lines.items()}
    localization = ET.Element('Table')
    for key, label in [('greet', 'Saluer'), ('antagonize', 'Provoquer')]:
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
