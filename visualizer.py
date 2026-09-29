"""Generacion de diagramas de automatas mediante Graphviz."""

import json
import shutil
import subprocess
from pathlib import Path


def automaton_to_dot(automaton, title):
	"""Convierte un automata en texto DOT, el formato de entrada de Graphviz.

	Args:
		automaton: Automata que se quiere representar.
		title: Titulo que aparecera en el grafico.

	Returns:
		Texto DOT listo para ser procesado por Graphviz.
	"""
	lines = [
		"digraph automaton {",
		'\trankdir=LR;',
		'\tnode [shape=circle, fontname="sans-serif"];',
		'\tedge [fontname=" sans-serif"];',
		f'\tlabel={json.dumps(title,ensure_ascii=False)};',
		'\tlabelloc="t";',
		'\tstart [shape=point, width=0.15, label=""];',
		f'\tstart -> {json.dumps(str(automaton.initial_state),ensure_ascii=False)};',
	]

	for state in sorted(automaton.states, key=str):
		shape = "doublecircle" if state in automaton.final_states else "circle"
		lines.append(
			f'\t{json.dumps(str(state),ensure_ascii=False)} [shape={shape}, '
			f'label={json.dumps(str(state),ensure_ascii=False)}];'
		)

	edges = {}
	for state in sorted(automaton.transitions, key=str):
		for symbol, destinations in sorted(
			automaton.transitions[state].items(), key=lambda item: str(item[0])
		):
			for destination in sorted(destinations, key=str):
				edges.setdefault((state, destination), []).append(symbol)

	for (state, destination), symbols in sorted(
		edges.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
	):
		label = ",".join(sorted((str(symbol) for symbol in symbols)))
		lines.append(
			f'\t{json.dumps(str(state),ensure_ascii=False)} -> '
			f'{json.dumps(str(destination),ensure_ascii=False)} '
			f'[label={json.dumps(label,ensure_ascii=False)}];'
		)

	lines.append("}")
	return "\n".join(lines)


def render_automaton(automaton, title, output_path):
	"""Guarda el DOT y su imagen PNG usando el ejecutable Graphviz ``dot``.

	Args:
		automaton: Automata que se quiere renderizar.
		title: Titulo del grafico.
		output_path: Ruta donde se guardara la imagen PNG.

	Returns:
		La ruta del archivo PNG generado.

	Raises:
		RuntimeError: Si el ejecutable ``dot`` no esta disponible.
		subprocess.CalledProcessError: Si Graphviz no puede generar la imagen.
	"""
	output_path = Path(output_path)
	dot_path = output_path.with_suffix(".dot")
	dot_path.write_text(automaton_to_dot(automaton, title), encoding="utf-8")

	if shutil.which("dot") is None:
		raise RuntimeError(
			"No se encontro Graphviz. Instala Graphviz y agrega el comando 'dot' al PATH."
		)

	subprocess.run(
		["dot", "-Tpng", str(dot_path), "-o", str(output_path)],
		check=True,
		capture_output=True,
		text=True,
	)
	return output_path
