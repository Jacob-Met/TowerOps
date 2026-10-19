"""Offline SVG receiving tests: native worlds, XML, negative controls and CLI."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from plan_world import parse_world
from towerops import Aircraft, WorldState
from world_svg import MAX_HORIZON_MIN, _ticks, render_svg

ROOT = Path(__file__).resolve().parents[1]
SVG = '{http://www.w3.org/2000/svg}'


def raw_world(aircraft: list[dict], version: int = 4) -> bytes:
    return json.dumps({'version': version, 'observed_at': 1000, 'aircraft': aircraft}, separators=(',', ':')).encode()


PAIR = [
    {'aircraft_id': 'A', 'x_nm': -5, 'y_nm': 0, 'altitude_ft': 10000,
     'vx_nm_min': 1, 'vy_nm_min': 0, 'climb_ft_min': 50},
    {'aircraft_id': 'B', 'x_nm': 5, 'y_nm': 4, 'altitude_ft': 12000,
     'vx_nm_min': -1, 'vy_nm_min': 0, 'climb_ft_min': -50},
]


class WorldSvgTests(unittest.TestCase):
    def test_native_pair_produces_valid_self_contained_svg_and_altitude_readout(self) -> None:
        original = parse_world(raw_world(PAIR))
        before = original.to_dict()
        svg = render_svg(original, 5.0)
        document = ET.fromstring(svg)
        self.assertEqual(document.tag, SVG + 'svg')
        self.assertEqual(len(document.findall('.//' + SVG + 'g')), 2)
        self.assertIn('A · 10000 → 10250 FT', svg)
        self.assertIn('B · 12000 → 11750 FT', svg)
        self.assertIn('not geographical', svg)
        self.assertNotIn('<script', svg)
        self.assertNotIn('http://', svg.replace('http://www.w3.org/2000/svg', ''))
        self.assertEqual(original.to_dict(), before)
        group_a = next(g for g in document.findall('.//' + SVG + 'g') if g.get('data-aircraft') == 'A')
        line = group_a.find(SVG + 'line')
        self.assertIsNotNone(line)
        self.assertGreater(float(line.get('x2')), float(line.get('x1')))
        self.assertEqual(line.get('y2'), line.get('y1'))

    def test_permutation_is_byte_identical_and_repeatable(self) -> None:
        forward = render_svg(parse_world(raw_world(PAIR)))
        reverse = render_svg(parse_world(raw_world(list(reversed(PAIR)))))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward, render_svg(parse_world(raw_world(PAIR))))

    def test_empty_world_and_stationary_singleton(self) -> None:
        empty = render_svg(parse_world(raw_world([])))
        self.assertIn('No aircraft in this saved world', empty)
        ET.fromstring(empty)
        still = raw_world([{**PAIR[0], 'vx_nm_min': 0, 'vy_nm_min': 0, 'climb_ft_min': 0}])
        one = ET.fromstring(render_svg(parse_world(still)))
        group = one.find('.//' + SVG + 'g')
        line = group.find(SVG + 'line')
        self.assertEqual(line.get('x1'), line.get('x2'))
        self.assertEqual(line.get('y1'), line.get('y2'))

    def test_escaped_labels_even_for_direct_native_model(self) -> None:
        state = WorldState(1, 0.0, (Aircraft('A&<"', 0, 0, 0, 0, 0),))
        svg = render_svg(state)
        group = ET.fromstring(svg).find('.//' + SVG + 'g')
        self.assertEqual(group.get('data-aircraft'), 'A&<"')
        self.assertNotIn('<script', svg)

    def test_horizon_rejections_and_tick_bound(self) -> None:
        state = parse_world(raw_world(PAIR))
        for horizon in (0, -1, 121, float('nan'), float('inf'), True, '5'):
            with self.subTest(horizon=horizon), self.assertRaises(ValueError):
                render_svg(state, horizon)
        self.assertEqual(len(_ticks(-5, 5)) <= 16, True)
        self.assertTrue(all(math.isfinite(tick) for tick in _ticks(-5, 5)))
        ET.fromstring(render_svg(state, MAX_HORIZON_MIN))

    def test_cli_real_stdin_and_file_path_match(self) -> None:
        raw = raw_world(PAIR)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'original.json'
            path.write_bytes(raw)
            file_result = subprocess.run(
                [sys.executable, str(ROOT / 'world_svg.py'), str(path), '--horizon-min', '2.5'],
                capture_output=True, check=False,
            )
            stdin_result = subprocess.run(
                [sys.executable, str(ROOT / 'world_svg.py'), '-', '--horizon-min', '2.5'],
                input=raw, capture_output=True, check=False,
            )
            self.assertEqual(file_result.returncode, 0, file_result.stderr.decode())
            self.assertEqual(stdin_result.returncode, 0, stdin_result.stderr.decode())
            self.assertEqual(file_result.stdout, stdin_result.stdout)
            self.assertEqual(file_result.stderr, b'')
            ET.fromstring(file_result.stdout)
            self.assertEqual(path.read_bytes(), raw)

    def test_cli_invalid_world_and_horizon_produce_no_svg(self) -> None:
        for raw, argument in (
            (b'{"version": 1, "version": 2}', None),
            (raw_world([PAIR[0], PAIR[0]]), None),
            (raw_world(PAIR), 'NaN'),
            (raw_world(PAIR), '121'),
        ):
            with self.subTest(raw=raw[:35], argument=argument):
                command = [sys.executable, str(ROOT / 'world_svg.py'), '-']
                if argument is not None:
                    command.extend(('--horizon-min', argument))
                result = subprocess.run(command, input=raw, capture_output=True, check=False)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b'')
                self.assertIn(b'error', result.stderr)


if __name__ == '__main__':
    unittest.main()
