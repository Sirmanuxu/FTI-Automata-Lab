"""Punto de entrada para procesar y visualizar automatas."""

import argparse
import json
from pathlib import Path
from subprocess import CalledProcessError

try:
	import tkinter as tk
	from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError:
	tk = None
	filedialog = None
	messagebox = None
	ttk = None

from equivalence import accepts, verify_minimization
from io_handler import automaton_from_dict, automaton_to_dict, read_json, write_json
from minimizer import minimize_dfa
from nfa_to_dfa import complete_and_prune, nfa_to_dfa
from validator import trace_string
from visualizer import render_automaton


def process_automaton(json_path):
	"""Ejecuta las etapas necesarias y devuelve los automatas generados.

	Si el automata de entrada ya es un AFD completo y sin estados
	inalcanzables, no se ejecuta ninguna conversion y se conservan sus
	nombres de estado originales. En caso contrario se completa (agregando
	un estado trampa si hace falta), se poda, o se aplica la construccion
	por subconjuntos si es no determinista.

	Args:
		json_path: Ruta del archivo JSON con la definicion y las pruebas.

	Returns:
		Un diccionario con los datos originales, los tres automatas
		(``original``, ``dfa``, ``min``), si hizo falta convertir
		(``conversion``: "none", "complete_prune" o "subset") y el reporte
		de equivalencia formal contra el automata original.
	"""
	data = read_json(json_path)
	original = automaton_from_dict(data)
	original.validate()

	if original.is_nfa():
		dfa = nfa_to_dfa(original)
		conversion = "subset"
	else:
		dfa, changed = complete_and_prune(original)
		conversion = "complete_prune" if changed else "none"
	dfa.validate()

	minimized_dfa = minimize_dfa(dfa)
	minimized_dfa.validate()

	equivalence_report = verify_minimization(original, dfa, minimized_dfa)

	return {
		"data": data,
		"original": original,
		"dfa": dfa,
		"min": minimized_dfa,
		"conversion": conversion,
		"equivalence": equivalence_report,
	}


def count_transitions(automaton):
	"""Atajo para contar transiciones al armar la tabla comparativa."""
	return automaton.transition_count()


def run_test_strings(automata, test_strings):
	"""Corre los casos de prueba del JSON sobre cada etapa del automata.

	Args:
		automata: Diccionario con los automatas ``original``, ``dfa`` y
			``min`` (las mismas claves que devuelve ``process_automaton``).
		test_strings: Diccionario ``{"accept": [...], "reject": [...]}``
			tal como viene en el archivo de entrada.

	Returns:
		Lista de filas ``(cadena, esperado, {etapa: obtenido})``, una por
		cada cadena de prueba, en el orden en que aparecen en el archivo.
	"""
	rows = []
	for expected_label, strings in test_strings.items():
		expected = expected_label == "accept"
		for string in strings:
			obtained = {
				stage: accepts(automata[stage], string)
				for stage in ("original", "dfa", "min")
			}
			rows.append((string, expected, obtained))
	return rows


def save_minimized_automaton(json_path, minimized_dfa, output_path=None):
	"""Guarda el AFD minimo en formato JSON.

	Si no se indica una ruta, crea un archivo junto a la entrada con el sufijo
	``_min``. El archivo de entrada nunca se sobrescribe por defecto.
	"""
	if output_path is None:
		input_path = Path(json_path)
		output_path = input_path.with_name(f"{input_path.stem}_min.json")
	else:
		output_path = Path(output_path)

	write_json(output_path, automaton_to_dict(minimized_dfa))
	return output_path


CONVERSION_LABELS = {
	"none": "Ninguna: el automata de entrada ya era un AFD completo y sin estados inalcanzables",
	"complete_prune": "Se completo con un estado trampa y/o se podaron estados inalcanzables (sin subconjuntos)",
	"subset": "Construccion por subconjuntos (el automata de entrada era no determinista)",
}


def print_results(json_path, result, output_path):
	"""Imprime en consola los automatas generados y su verificacion.

	Args:
		json_path: Ruta del archivo JSON procesado.
		result: Diccionario devuelto por ``process_automaton``.
		output_path: Ruta donde se guardo el AFD minimo.
	"""
	original, dfa, minimized_dfa = result["original"], result["dfa"], result["min"]

	print(f"Automata cargado: {json_path}")
	print(f"Tipo de entrada: {'AFND' if original.is_nfa() else 'AFD'}")
	print(f"Conversion aplicada: {CONVERSION_LABELS[result['conversion']]}")
	print(
		f"Estados y transiciones: entrada={len(original.states)}/{count_transitions(original)}  "
		f"AFD={len(dfa.states)}/{count_transitions(dfa)}  "
		f"minimo={len(minimized_dfa.states)}/{count_transitions(minimized_dfa)}"
	)
	print(f"Salida JSON guardada en: {output_path}")

	print("\nVerificacion de equivalencia (requisito 3 de la consigna):")
	from equivalence import print_report
	print_report(result["equivalence"])

	test_strings = result["data"].get("test_strings", {})
	if test_strings:
		print("\nValidacion de los casos de prueba del archivo:")
		rows = run_test_strings(
			{"original": original, "dfa": dfa, "min": minimized_dfa}, test_strings
		)
		ok = 0
		for string, expected, obtained in rows:
			all_match = all(value == expected for value in obtained.values())
			ok += all_match
			status = "OK" if all_match else "ERROR"
			detalle = ", ".join(f"{stage}={value}" for stage, value in obtained.items())
			print(f"  {string!r} (esperado={expected}) [{status}]  {detalle}")
		print(f"  {ok}/{len(rows)} casos correctos en las tres etapas")

	print("\nAFD minimo generado:")
	print(json.dumps(automaton_to_dict(minimized_dfa), indent=4, ensure_ascii=False))


class AutomatonWindow:
	"""Ventana para ejecutar el flujo, comparar sus etapas y verificar la consigna."""

	STAGE_TITLES = {
		"nfa": "Automata de entrada",
		"dfa": "AFD",
		"min": "AFD minimo",
	}

	def __init__(self, root):
		"""Construye la ventana y sus controles graficos.

		Args:
			root: Ventana principal de Tkinter.
		"""
		self.root = root
		self.root.title("Automata Lab")
		self.root.geometry("1360x860")
		self.root.minsize(1040, 680)
		self.source_images = {}
		self.automata = {}
		self.result = None
		self.show_dfa_stage = True
		self.configure_styles()

		root.configure(bg="#eef2f6")
		header = tk.Frame(root, bg="#19324d", padx=24, pady=18)
		header.pack(fill="x")
		ttk.Label(header, text="AUTOMATA LAB", style="Brand.TLabel").pack(anchor="w")
		ttk.Label(
			header,
			text="Conversor y minimizador de automatas finitos",
			style="Header.TLabel",
		).pack(anchor="w", pady=(4, 0))

		controls = ttk.Frame(root, style="Toolbar.TFrame", padding=(24, 16))
		controls.pack(fill="x")
		ttk.Label(controls, text="Archivo de entrada", style="Field.TLabel").pack(side="left")
		self.path_var = tk.StringVar()
		ttk.Entry(controls, textvariable=self.path_var, style="Path.TEntry").pack(
			side="left", fill="x", expand=True, padx=(14, 10)
		)
		ttk.Button(
			controls, text="Elegir archivo", command=self.choose_file, style="Secondary.TButton"
		).pack(side="left")
		ttk.Button(
			controls, text="Procesar automata", command=self.process, style="Primary.TButton"
		).pack(side="left", padx=(10, 0))

		self.summary = tk.StringVar(value="Selecciona un archivo JSON para comenzar")
		ttk.Label(root, textvariable=self.summary, style="Summary.TLabel", padding=(24, 0, 24, 14)).pack(fill="x")

		self.notebook = ttk.Notebook(root)
		self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 16))

		diagrams_tab = ttk.Frame(self.notebook, padding=(0, 12, 0, 0))
		self.notebook.add(diagrams_tab, text="Diagramas")
		self.create_diagram_view(diagrams_tab)

		self.create_test_tab()
		self.create_results_tab()

		self.output = tk.Text(
			root, height=3, wrap="word", state="disabled",
			background="#ffffff", foreground="#405268", relief="flat",
			font=("TkDefaultFont", 10), padx=12, pady=8,
		)
		self.output.pack(fill="x", padx=24, pady=(0, 20))

	def configure_styles(self):
		"""Define una paleta clara y una jerarquia visual para la ventana."""
		style = ttk.Style(self.root)
		style.theme_use("clam")
		style.configure("Toolbar.TFrame", background="#ffffff")
		style.configure("Canvas.TFrame", background="#ffffff")
		style.configure("Brand.TLabel", background="#19324d", foreground="#8ee3cf", font=("TkDefaultFont", 11, "bold"))
		style.configure("Header.TLabel", background="#19324d", foreground="#ffffff", font=("TkDefaultFont", 22, "bold"))
		style.configure("Field.TLabel", background="#ffffff", foreground="#19324d", font=("TkDefaultFont", 10, "bold"))
		style.configure("Summary.TLabel", background="#eef2f6", foreground="#52657a", font=("TkDefaultFont", 10))
		style.configure("Note.TLabel", background="#f7f9fb", foreground="#67788c", font=("TkDefaultFont", 10, "italic"), padding=14)
		style.configure("Panel.TLabelframe", background="#ffffff", foreground="#19324d", bordercolor="#d5dde6", relief="solid")
		style.configure("Panel.TLabelframe.Label", background="#ffffff", foreground="#19324d", font=("TkDefaultFont", 12, "bold"))
		style.configure("PanelSubtitle.TLabel", background="#ffffff", foreground="#8492a3", font=("TkDefaultFont", 9))
		style.configure("DiagramTitle.TLabel", background="#ffffff", foreground="#19324d", font=("TkDefaultFont", 15, "bold"))
		style.configure("Path.TEntry", fieldbackground="#f7f9fb", foreground="#26384d", padding=8)
		style.configure("Primary.TButton", background="#1f9d8b", foreground="#ffffff", padding=(14, 8), font=("TkDefaultFont", 10, "bold"))
		style.map("Primary.TButton", background=[("active", "#177d70")])
		style.configure("Secondary.TButton", background="#e8eef4", foreground="#19324d", padding=(12, 8))
		style.map("Secondary.TButton", background=[("active", "#d9e3ec")])
		style.configure("Test.TFrame", background="#ffffff")
		style.configure("TestTitle.TLabel", background="#ffffff", foreground="#19324d", font=("TkDefaultFont", 17, "bold"))
		style.configure("TestText.TLabel", background="#ffffff", foreground="#52657a", font=("TkDefaultFont", 10))
		style.configure("Result.TLabel", background="#f7f9fb", foreground="#52657a", padding=14, font=("TkDefaultFont", 11, "bold"))
		style.configure("Accepted.TLabel", background="#e5f6f1", foreground="#147d6b", padding=14, font=("TkDefaultFont", 11, "bold"))
		style.configure("Rejected.TLabel", background="#fff0ed", foreground="#b34d3b", padding=14, font=("TkDefaultFont", 11, "bold"))
		style.configure("Ok.TLabel", background="#e5f6f1", foreground="#147d6b", padding=10, font=("TkDefaultFont", 10, "bold"))
		style.configure("Error.TLabel", background="#fff0ed", foreground="#b34d3b", padding=10, font=("TkDefaultFont", 10, "bold"))
		style.configure("Treeview", rowheight=26, font=("TkDefaultFont", 10))
		style.configure("Treeview.Heading", font=("TkDefaultFont", 10, "bold"))

	def create_diagram_view(self, parent):
		"""Crea un contenedor para recorrer los diagramas en vertical.

		El slot del AFD intermedio puede mostrar una imagen o, cuando no
		hizo falta ninguna conversion real, una nota explicando por que se
		omitio (para no repetir un diagrama identico al de entrada).
		"""
		container = ttk.Frame(parent, style="Canvas.TFrame")
		container.pack(fill="both", expand=True)
		canvas = tk.Canvas(container, background="#ffffff", highlightthickness=0)
		vertical_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
		horizontal_scroll = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
		canvas.configure(xscrollcommand=horizontal_scroll.set, yscrollcommand=vertical_scroll.set)
		canvas.grid(row=0, column=0, sticky="nsew")
		vertical_scroll.grid(row=0, column=1, sticky="ns")
		horizontal_scroll.grid(row=1, column=0, sticky="ew")
		container.columnconfigure(0, weight=1)
		container.rowconfigure(0, weight=1)

		content = ttk.Frame(canvas, style="Canvas.TFrame", padding=(24, 16))
		canvas.create_window((0, 0), window=content, anchor="nw")
		content.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))

		self.diagram_image_labels = {}
		self.diagram_note_labels = {}
		for position, key in enumerate(self.STAGE_TITLES):
			image_label = tk.Label(content, background="#ffffff", anchor="nw")
			note_label = ttk.Label(content, style="Note.TLabel", wraplength=760, justify="left")
			image_label.pack(anchor="w", pady=(0 if position == 0 else 24, 0))
			self.diagram_image_labels[key] = image_label
			self.diagram_note_labels[key] = note_label

	def show_diagram(self, key, image=None, note=None):
		"""Muestra la imagen o la nota de una etapa, ocultando la otra."""
		image_label = self.diagram_image_labels[key]
		note_label = self.diagram_note_labels[key]
		if image is not None:
			note_label.pack_forget()
			image_label.configure(image=image)
			image_label.pack(anchor="w")
		else:
			image_label.pack_forget()
			note_label.configure(text=note or "")
			note_label.pack(anchor="w", fill="x")

	def create_test_tab(self):
		"""Construye la pestaña para probar una cadena y ver su traza."""
		test_tab = ttk.Frame(self.notebook, style="Test.TFrame", padding=32)
		self.notebook.add(test_tab, text="Prueba de cadena")
		ttk.Label(test_tab, text="Probar una cadena", style="TestTitle.TLabel").pack(anchor="w")
		ttk.Label(
			test_tab,
			text="Ingresa una cadena para compararla en cada etapa y ver, paso a paso, "
			"que estados quedan activos al leer cada simbolo.",
			style="TestText.TLabel",
		).pack(anchor="w", pady=(6, 20))

		input_row = ttk.Frame(test_tab, style="Test.TFrame")
		input_row.pack(fill="x")
		ttk.Label(input_row, text="Cadena", style="Field.TLabel").pack(side="left")
		self.input_string_var = tk.StringVar()
		input_entry = ttk.Entry(input_row, textvariable=self.input_string_var, style="Path.TEntry")
		input_entry.pack(side="left", fill="x", expand=True, padx=14)
		input_entry.bind("<Return>", lambda event: self.test_string())
		ttk.Button(
			input_row, text="Probar cadena", command=self.test_string, style="Primary.TButton"
		).pack(side="left")

		self.test_status = tk.StringVar(value="Procesa un archivo antes de probar cadenas.")
		ttk.Label(test_tab, textvariable=self.test_status, style="TestText.TLabel").pack(anchor="w", pady=(18, 12))

		self.results_row = ttk.Frame(test_tab, style="Test.TFrame")
		self.results_row.pack(fill="x")
		self.result_labels = {}
		for key in ("nfa", "dfa", "min"):
			label = ttk.Label(self.results_row, text="Sin resultado", style="Result.TLabel", anchor="center")
			self.result_labels[key] = label

		ttk.Label(test_tab, text="Traza de la simulacion", style="Field.TLabel").pack(anchor="w", pady=(26, 8))
		ttk.Label(
			test_tab,
			text="Cada celda muestra el conjunto de estados activos tras leer el simbolo de esa fila "
			"(en un AFD siempre hay un unico estado).",
			style="TestText.TLabel",
		).pack(anchor="w", pady=(0, 10))
		self.trace_tree = ttk.Treeview(test_tab, show="headings", height=10)
		self.trace_tree.pack(fill="both", expand=True)

	def _layout_result_columns(self, keys):
		"""Muestra solo las columnas de resultado que corresponden."""
		for key, label in self.result_labels.items():
			label.grid_forget()
		for column, key in enumerate(keys):
			self.results_row.columnconfigure(column, weight=1)
			self.result_labels[key].grid(
				row=0, column=column, sticky="ew",
				padx=(0 if column == 0 else 6, 0),
			)

	def test_string(self):
		"""Evalua la cadena actual en cada etapa y arma la traza paso a paso."""
		if not self.automata:
			self.test_status.set("Procesa un archivo antes de probar cadenas.")
			return

		input_string = self.input_string_var.get()
		keys = ("nfa", "dfa", "min") if self.show_dfa_stage else ("nfa", "min")
		self._layout_result_columns(keys)

		traces = {}
		for key in keys:
			title = self.stage_titles[key]
			trace = trace_string(self.automata[key], input_string)
			traces[key] = trace
			label = self.result_labels[key]
			if trace["error"]:
				label.configure(text=f"{title}\n{trace['error']}", style="Rejected.TLabel")
			else:
				result = "ACEPTADA" if trace["accepted"] else "RECHAZADA"
				style = "Accepted.TLabel" if trace["accepted"] else "Rejected.TLabel"
				label.configure(text=f"{title}\n{result}", style=style)

		self._fill_trace_tree(keys, traces, input_string)
		self.test_status.set(f"Resultados para: {input_string or 'ε (cadena vacia)'}")

	def _fill_trace_tree(self, keys, traces, input_string):
		"""Llena la tabla de traza con una fila por simbolo leido."""
		tree = self.trace_tree
		tree.delete(*tree.get_children())

		columns = ["symbol"] + list(keys)
		tree["columns"] = columns
		tree.heading("symbol", text="Simbolo")
		tree.column("symbol", width=90, anchor="center", stretch=False)
		for key in keys:
			tree.heading(key, text=self.stage_titles[key])
			tree.column(key, anchor="w", stretch=True)

		step_count = len(next(iter(traces.values()))["steps"])
		for row in range(step_count):
			symbol, _ = traces[keys[0]]["steps"][row]
			symbol_text = "(inicio)" if symbol is None else symbol
			values = [symbol_text]
			for key in keys:
				if row < len(traces[key]["steps"]):
					_, states = traces[key]["steps"][row]
					if len(states) == 1:
						# Un unico estado activo: se muestra tal cual (en el
						# AFD/minimo el nombre ya es del estilo "{q0, q1}").
						values.append(next(iter(states)))
					else:
						values.append("{" + ", ".join(sorted(str(s) for s in states)) + "}")
				else:
					values.append("-")
			tree.insert("", "end", values=values)

	def create_results_tab(self):
		"""Construye la pestaña con la tabla comparativa y la verificacion."""
		tab = ttk.Frame(self.notebook, style="Test.TFrame", padding=32)
		self.notebook.add(tab, text="Resultados")

		ttk.Label(tab, text="Tabla comparativa", style="TestTitle.TLabel").pack(anchor="w")
		self.comparison_tree = ttk.Treeview(
			tab, show="headings", height=3,
			columns=("stage", "states", "transitions"),
		)
		self.comparison_tree.heading("stage", text="Etapa")
		self.comparison_tree.heading("states", text="Estados")
		self.comparison_tree.heading("transitions", text="Transiciones")
		self.comparison_tree.column("stage", width=260, anchor="w")
		self.comparison_tree.column("states", width=120, anchor="center")
		self.comparison_tree.column("transitions", width=140, anchor="center")
		self.comparison_tree.pack(fill="x", pady=(10, 24))

		ttk.Label(
			tab, text="Verificacion de equivalencia (consigna, punto 3)", style="TestTitle.TLabel"
		).pack(anchor="w")
		self.equivalence_frame = ttk.Frame(tab, style="Test.TFrame")
		self.equivalence_frame.pack(fill="x", pady=(10, 24))
		self.equivalence_labels = []

		ttk.Label(tab, text="Casos de prueba del archivo", style="TestTitle.TLabel").pack(anchor="w")
		self.cases_status = tk.StringVar(value="Procesa un archivo para ver sus casos de prueba.")
		ttk.Label(tab, textvariable=self.cases_status, style="TestText.TLabel").pack(anchor="w", pady=(6, 10))
		self.cases_tree = ttk.Treeview(
			tab, show="headings", height=8,
			columns=("string", "expected", "nfa", "dfa", "min", "status"),
		)
		for column, heading, width in (
			("string", "Cadena", 160),
			("expected", "Esperado", 90),
			("nfa", "Entrada", 90),
			("dfa", "AFD", 90),
			("min", "Minimo", 90),
			("status", "Resultado", 100),
		):
			self.cases_tree.heading(column, text=heading)
			self.cases_tree.column(column, width=width, anchor="center")
		self.cases_tree.pack(fill="both", expand=True)

	def _fill_equivalence_panel(self, report):
		"""Muestra el resultado de la verificacion formal de equivalencia."""
		for widget in self.equivalence_frame.winfo_children():
			widget.destroy()

		def show(string):
			return "ε (cadena vacia)" if string == "" else repr(string)

		rows = []
		if report["equivalent_to_original"]:
			rows.append(("OK", "3a) El minimo acepta el mismo lenguaje que el automata original (automata producto)."))
		else:
			rows.append(("ERROR", f"3a) Cadena que distingue al minimo del original: {show(report['counterexample'])}"))

		if report["string_difference"] is None:
			rows.append(("OK", f"3a) Prueba por cadenas: {report['strings_tested']} cadenas probadas (hasta longitud {report['max_length']}) sin diferencias."))
		else:
			rows.append(("ERROR", f"3a) Prueba por cadenas: difieren en {show(report['string_difference'])}."))

		if report["not_bigger_than_dfa"]:
			rows.append(("OK", f"3b) El minimo ({report['states_minimized']} estados) no supera al AFD ({report['states_dfa']} estados)."))
		else:
			rows.append(("ERROR", f"3b) El minimo tiene MAS estados que el AFD."))

		for status, text in rows:
			style = "Ok.TLabel" if status == "OK" else "Error.TLabel"
			label = ttk.Label(self.equivalence_frame, text=f"{'✓' if status == 'OK' else '✗'}  {text}", style=style, anchor="w", justify="left", wraplength=1000)
			label.pack(fill="x", pady=3)

	def _fill_cases_tree(self, result):
		"""Muestra los casos de prueba del archivo, si los tiene."""
		tree = self.cases_tree
		tree.delete(*tree.get_children())

		test_strings = result["data"].get("test_strings", {})
		if not test_strings:
			self.cases_status.set(
				"El archivo no incluye \"test_strings\"; no hay casos para validar "
				"automaticamente. Se recomienda agregarlos al JSON de entrada."
			)
			return

		rows = run_test_strings(
			{"original": result["original"], "dfa": result["dfa"], "min": result["min"]},
			test_strings,
		)
		ok = 0
		for string, expected, obtained in rows:
			all_match = all(value == expected for value in obtained.values())
			ok += all_match
			tree.insert(
				"", "end",
				values=(
					string or "ε",
					"ACEPTA" if expected else "RECHAZA",
					"ACEPTA" if obtained["original"] else "RECHAZA",
					"ACEPTA" if obtained["dfa"] else "RECHAZA",
					"ACEPTA" if obtained["min"] else "RECHAZA",
					"OK" if all_match else "ERROR",
				),
				tags=("ok" if all_match else "error",),
			)
		tree.tag_configure("ok", background="#e5f6f1")
		tree.tag_configure("error", background="#fff0ed")
		self.cases_status.set(f"{ok}/{len(rows)} casos correctos en las tres etapas.")

	def choose_file(self):
		"""Abre un selector de archivos y actualiza la ruta elegida."""
		path = filedialog.askopenfilename(
			title="Seleccionar automata",
			filetypes=(("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")),
		)
		if path:
			self.path_var.set(path)

	def process(self):
		"""Procesa el automata seleccionado y actualiza las tres pestañas."""
		json_path = self.path_var.get().strip()
		if not json_path:
			messagebox.showwarning("Falta el archivo", "Selecciona un archivo JSON.")
			return

		try:
			result = process_automaton(json_path)
			self.result = result
			original, dfa, minimized_dfa = result["original"], result["dfa"], result["min"]
			self.automata = {"nfa": original, "dfa": dfa, "min": minimized_dfa}

			input_title = "AFND original" if original.is_nfa() else "AFD de entrada"
			self.show_dfa_stage = result["conversion"] != "none"
			self.stage_titles = {"nfa": input_title, "dfa": "AFD", "min": "AFD minimo"}

			output_path = save_minimized_automaton(json_path, minimized_dfa)
			output_dir = Path(json_path).parent / "graficos"
			output_dir.mkdir(exist_ok=True)

			self.source_images = {}

			self._render_stage(json_path, output_dir, "nfa", original, input_title)

			if self.show_dfa_stage:
				dfa_title = (
					"AFD por construccion de subconjuntos"
					if result["conversion"] == "subset"
					else "AFD completado y podado (sin subconjuntos)"
				)
				self._render_stage(json_path, output_dir, "dfa", dfa, dfa_title)
			else:
				self.show_diagram(
					"dfa", note=(
						"El automata de entrada ya era un AFD completo y sin estados "
						"inalcanzables, asi que no hizo falta ninguna conversion: "
						"esta etapa es identica a la de entrada."
					),
				)

			self._render_stage(json_path, output_dir, "min", minimized_dfa, "AFD minimo")

			self.summary.set(
				f"Entrada ({'AFND' if original.is_nfa() else 'AFD'}): {len(original.states)} estados | "
				f"AFD: {len(dfa.states)} | Minimo: {len(minimized_dfa.states)} | "
				f"Conversion: {CONVERSION_LABELS[result['conversion']]}"
			)

			self._fill_comparison_tree(result)
			self._fill_equivalence_panel(result["equivalence"])
			self._fill_cases_tree(result)
			self._layout_result_columns(("nfa", "dfa", "min") if self.show_dfa_stage else ("nfa", "min"))
			self.trace_tree.delete(*self.trace_tree.get_children())

			self.set_output(output_dir, output_path)
		except (OSError, ValueError, RuntimeError, CalledProcessError) as error:
			messagebox.showerror("No se pudo procesar el automata", str(error))

	def _render_stage(self, json_path, output_dir, key, automaton, title):
		"""Genera y muestra el diagrama de una etapa."""
		image_path = output_dir / f"{Path(json_path).stem}_{key}.png"
		render_automaton(automaton, title, image_path)
		image = tk.PhotoImage(file=str(image_path))
		self.source_images[key] = image
		self.show_diagram(key, image=image)

	def _fill_comparison_tree(self, result):
		"""Llena la tabla comparativa de estados y transiciones."""
		tree = self.comparison_tree
		tree.delete(*tree.get_children())
		original, dfa, minimized_dfa = result["original"], result["dfa"], result["min"]
		rows = [("Entrada", original)]
		if self.show_dfa_stage:
			rows.append(("AFD", dfa))
		rows.append(("AFD minimo", minimized_dfa))
		for label, automaton in rows:
			tree.insert("", "end", values=(label, len(automaton.states), count_transitions(automaton)))

	def set_output(self, output_dir, output_path):
		"""Muestra las rutas de salida del procesamiento."""
		lines = [
			f"Salida JSON guardada en: {output_path}",
			f"Graficos guardados en: {output_dir}",
		]
		self.output.configure(state="normal")
		self.output.delete("1.0", "end")
		self.output.insert("1.0", "\n".join(lines))
		self.output.configure(state="disabled")



def main():
	"""Procesa los argumentos y ejecuta la interfaz o el modo de consola."""
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"json_path",
		help="Ruta al archivo JSON; si se omite, se abre la interfaz grafica",
		nargs="?",
	)
	parser.add_argument(
		"-o",
		"--output",
		help="Ruta del JSON de salida; por defecto se usa '<entrada>_min.json'",
	)
	arguments = parser.parse_args()

	if arguments.json_path:
		result = process_automaton(arguments.json_path)
		output_path = save_minimized_automaton(
			arguments.json_path, result["min"], arguments.output
		)
		print_results(arguments.json_path, result, output_path)
		return

	if ttk is None:
		raise RuntimeError(
			"La interfaz grafica requiere tkinter. Instala el paquete python3-tk "
			"para abrirla."
		)

	root = tk.Tk()
	AutomatonWindow(root)
	root.mainloop()


if __name__ == "__main__":
	main()
