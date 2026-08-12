"""Build a compact, inspectable SUMO network for operations screening.

The benchmark intersection is deliberately labelled as a *representative
geometry*. The project exposes an OSM conversion command for a real study
area, but does not misrepresent this small test network as a surveyed street.
"""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

INCOMING = {"n_in", "s_in", "e_in", "w_in"}
MOVEMENTS = {
    "north_to_south": ("n_in", "s_out"),
    "south_to_north": ("s_in", "n_out"),
    "east_to_west": ("e_in", "w_out"),
    "west_to_east": ("w_in", "e_out"),
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_representative_network(work_dir: str | Path, force: bool = False) -> Path:
    """Create a two-lane, signalized four-leg network with `netconvert`."""

    work_dir = Path(work_dir)
    net_path = work_dir / "representative.net.xml"
    if net_path.exists() and not force:
        return net_path

    _write(
        work_dir / "nodes.nod.xml",
        """<nodes>
  <node id="N" x="0" y="500" type="priority"/>
  <node id="S" x="0" y="-500" type="priority"/>
  <node id="E" x="500" y="0" type="priority"/>
  <node id="W" x="-500" y="0" type="priority"/>
  <node id="J" x="0" y="0" type="traffic_light"/>
</nodes>
""",
    )
    _write(
        work_dir / "edges.edg.xml",
        """<edges>
  <edge id="n_in" from="N" to="J" numLanes="2" speed="13.89"/>
  <edge id="n_out" from="J" to="N" numLanes="2" speed="13.89"/>
  <edge id="s_in" from="S" to="J" numLanes="2" speed="13.89"/>
  <edge id="s_out" from="J" to="S" numLanes="2" speed="13.89"/>
  <edge id="e_in" from="E" to="J" numLanes="2" speed="13.89"/>
  <edge id="e_out" from="J" to="E" numLanes="2" speed="13.89"/>
  <edge id="w_in" from="W" to="J" numLanes="2" speed="13.89"/>
  <edge id="w_out" from="J" to="W" numLanes="2" speed="13.89"/>
</edges>
""",
    )
    command = [
        "netconvert",
        "--node-files", str(work_dir / "nodes.nod.xml"),
        "--edge-files", str(work_dir / "edges.edg.xml"),
        "--output-file", str(net_path),
        "--no-turnarounds", "true",
        "--tls.default-type", "static",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return net_path


def _phase_state(net_path: Path, green_approaches: set[str], yellow: bool = False) -> str:
    tree = ET.parse(net_path)
    connections = [c for c in tree.findall(".//connection") if c.get("tl") == "J"]
    if not connections:
        raise RuntimeError("Expected a signal controller J in the generated network.")
    states = ["r"] * (max(int(c.attrib["linkIndex"]) for c in connections) + 1)
    for connection in connections:
        index = int(connection.attrib["linkIndex"])
        if connection.get("from") in green_approaches:
            states[index] = "y" if yellow else "G"
    return "".join(states)


def write_signal_program(net_path: str | Path, add_path: str | Path, scenario: str) -> Path:
    """Write baseline or peak-direction retiming policy to a SUMO additional file."""

    net_path, add_path = Path(net_path), Path(add_path)
    if scenario not in {"baseline", "peak_retimed"}:
        raise ValueError("scenario must be 'baseline' or 'peak_retimed'")
    if scenario == "baseline":
        ns_green, ew_green = 32, 26
    else:
        ns_green, ew_green = 42, 16

    ns, ew = {"n_in", "s_in"}, {"e_in", "w_in"}
    ns_state, ew_state = _phase_state(net_path, ns), _phase_state(net_path, ew)
    ns_yellow, ew_yellow = _phase_state(net_path, ns, yellow=True), _phase_state(net_path, ew, yellow=True)
    all_red = "r" * len(ns_state)
    xml = f"""<additional>
  <tlLogic id="J" type="static" programID="{scenario}" offset="0">
    <phase duration="{ns_green}" state="{ns_state}"/>
    <phase duration="4" state="{ns_yellow}"/>
    <phase duration="2" state="{all_red}"/>
    <phase duration="{ew_green}" state="{ew_state}"/>
    <phase duration="4" state="{ew_yellow}"/>
    <phase duration="2" state="{all_red}"/>
  </tlLogic>
  <laneAreaDetector id="n_queue" lane="n_in_0" pos="-120" endPos="-2" freq="60" file="lanearea.xml"/>
  <laneAreaDetector id="s_queue" lane="s_in_0" pos="-120" endPos="-2" freq="60" file="lanearea.xml"/>
  <laneAreaDetector id="e_queue" lane="e_in_0" pos="-120" endPos="-2" freq="60" file="lanearea.xml"/>
  <laneAreaDetector id="w_queue" lane="w_in_0" pos="-120" endPos="-2" freq="60" file="lanearea.xml"/>
</additional>
"""
    _write(add_path, xml)
    return add_path


def build_routes(demand_csv: str | Path, route_path: str | Path) -> Path:
    """Create deterministic, count-constrained straight-through flows."""

    import pandas as pd

    demand = pd.read_csv(demand_csv)
    route_path = Path(route_path)
    lines = [
        "<routes>",
        '  <vType id="passenger" vClass="passenger" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.89" emissionClass="HBEFA3/PC_G_EU4"/>',
    ]
    for movement, (from_edge, to_edge) in MOVEMENTS.items():
        lines.append(f'  <route id="{movement}" edges="{from_edge} {to_edge}"/>')
    for i, row in demand.iterrows():
        if row["movement"] not in MOVEMENTS:
            continue
        lines.append(
            f'  <flow id="{row.movement}_{i}" type="passenger" route="{row.movement}" '
            f'begin="{int(row.begin_s)}" end="{int(row.end_s)}" number="{int(row.vehicles_15min)}" '
            'departLane="best" departSpeed="max"/>'
        )
    lines.append("</routes>")
    _write(route_path, "\n".join(lines) + "\n")
    return route_path


def osm_to_sumo_command(osm_file: str | Path, output_net: str | Path) -> list[str]:
    """Return the reviewed command used to convert a real OSM study area."""

    return [
        "netconvert", "--osm-files", str(osm_file), "--output-file", str(output_net),
        "--geometry.remove", "--ramps.guess", "--junctions.join", "--tls.guess-signals",
        "--tls.discard-simple", "--tls.join", "--tls.default-type", "actuated",
        "--remove-edges.isolated",
    ]
