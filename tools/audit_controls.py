"""Report controller bindings from supplied game/profile XML or PAK files.

This is a static inventory, not proof a button is free during gameplay.
Pass both game defaults and your current user profile when available.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

BUTTON = re.compile(r'^(xi_|pad_|gamepad_|xinput_).+', re.I)
CANDIDATES = ('xi_dpad_up', 'xi_dpad_down', 'xi_dpad_left', 'xi_dpad_right',
              'xi_thumbl', 'xi_thumbr', 'xi_shoulderl', 'xi_shoulderr',
              'xi_a', 'xi_b', 'xi_x', 'xi_y', 'xi_back', 'xi_start')


def bindings(data: bytes, origin: str) -> list[dict]:
    root = ET.fromstring(data)
    result = []

    def visit(node, action_map='', action=''):
        tag = node.tag.rsplit('}', 1)[-1].lower()
        if tag == 'actionmap':
            action_map = node.get('name', '')
        if tag == 'action':
            action = node.get('name', '')
        for attribute, value in node.attrib.items():
            if BUTTON.fullmatch(value):
                result.append({'source': origin, 'map': action_map, 'action': action,
                               'button': value.lower(), 'attribute': attribute,
                               'parameters': dict(node.attrib)})
        for child in node:
            visit(child, action_map, action)
    visit(root)
    return result


def audit(paths: list[Path]) -> dict:
    rows, inspected = [], []
    for path in paths:
        if path.suffix.lower() == '.xml':
            rows.extend(bindings(path.read_bytes(), str(path)))
            inspected.append(str(path))
        elif zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    name = info.filename.replace('\\', '/').lower()
                    if name.endswith('.xml') and ('libs/config/' in name
                                                  or 'actionmap' in name
                                                  or 'controller' in name):
                        if info.file_size > 16 * 1024 * 1024:
                            raise ValueError(f'Config too large to audit: {info.filename}')
                        origin = f'{path}!{info.filename}'
                        rows.extend(bindings(archive.read(info), origin))
                        inspected.append(origin)
        else:
            raise ValueError(f'Expected XML or PAK/ZIP: {path}')
    if not inspected:
        raise ValueError('No configuration XML found; cannot assess bindings')
    seen = {row['button'] for row in rows}
    return {
        'status': 'static_inventory_only', 'inspected': inspected,
        'bindings': rows,
        'native_chat_bindings': [r for r in rows if 'chat_init' in r['action']],
        'not_seen_in_supplied_files': [key for key in CANDIDATES if key not in seen],
        'warning': 'Not seen does not mean unused. Check active maps, native actions, '
                   'hold/release behavior and user overrides in the actual game.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.files), ensure_ascii=False, indent=2))
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Audit stopped: {error}\n')
