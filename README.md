# Automata Lab — TP Integrador de Fundamentos Teóricos de la Informática

Programa en Python que, dada la descripción de un autómata finito (determinista
o no determinista), lo convierte en un AFD, lo minimiza y permite validar
cadenas sobre las tres etapas. Incluye una interfaz gráfica para comparar los
autómatas visualmente y una verificación formal de que el resultado es
equivalente al autómata de entrada.

## Requisitos

El programa usa **solo la biblioteca estándar de Python** (no hay ningún
`pip install` que hacer). Lo único que puede hacer falta instalar por fuera
de Python es:

| Requisito | Para qué se usa | Es obligatorio? |
|---|---|---|
| Python 3.8 o superior | Todo el programa | Sí |
| `tkinter` | La interfaz gráfica | Solo si se quiere usar la GUI |
| [Graphviz](https://graphviz.org/download/) (el comando `dot`) | Generar los diagramas (`.png`) | Solo si se quiere usar la GUI |

El **modo consola** (`python main.py archivo.json`) funciona sin instalar
nada más que Python.

### Instalar las dependencias opcionales

- **Windows:** `winget install Graphviz` (o el instalador de
  [graphviz.org](https://graphviz.org/download/), marcando la opción de
  agregarlo al PATH). `tkinter` ya viene incluido con Python.
- **macOS:** `brew install graphviz`. `tkinter` ya viene incluido con Python.
- **Linux (Ubuntu/Debian):** `sudo apt install graphviz python3-tk`

Para comprobar que Graphviz quedó bien instalado: `dot -V` debería imprimir
una versión.

## Cómo ejecutarlo

Parado en la carpeta del proyecto (la que tiene `main.py`):

```bash
# Modo consola: procesa un archivo y muestra el resultado por pantalla
python main.py tests/caso_1.json

# Elegir dónde se guarda el AFD minimo (por defecto es "<entrada>_min.json")
python main.py tests/caso_1.json -o salida.json

# Interfaz grafica (requiere tkinter y, para ver los diagramas, Graphviz)
python main.py
```

En Linux o macOS el comando puede ser `python3` en lugar de `python`.

## Estructura del proyecto

```
.
├── automaton.py       # Clase Automaton: estados, alfabeto, transiciones,
│                       # validación, chequeo de si ya es un AFD, etc.
├── nfa_to_dfa.py       # Conversión AFND→AFD por construcción de subconjuntos,
│                       # y completado/poda de un AFD que ya es determinista.
├── minimizer.py        # Minimización de un AFD por el algoritmo de Moore.
├── validator.py        # Simulación de cadenas (con traza paso a paso).
├── equivalence.py       # Verificación formal de equivalencia entre dos
│                        # autómatas (autómata producto + prueba por cadenas).
├── io_handler.py         # Lectura y escritura de autómatas en formato JSON.
├── visualizer.py          # Generación de diagramas con Graphviz.
├── main.py                 # Punto de entrada: CLI y GUI.
└── tests/
    ├── caso_1.json          # Caso chico: AFND que termina en "01".
    ├── caso_2.json           # Caso mediano: requiere varias rondas de minimización.
    ├── caso_3.json            # Caso mediano-grande: dos ramas no deterministas.
    └── graficos/               # Diagramas .dot/.png generados al procesar un archivo.
```

## Formato de entrada (JSON)

```json
{
  "description": "Texto opcional que describe el autómata",
  "alphabet": ["0", "1"],
  "states": ["q0", "q1", "q2"],
  "initial_state": "q0",
  "final_states": ["q2"],
  "transitions": {
    "q0": { "0": ["q0", "q1"], "1": ["q0"] },
    "q1": { "1": ["q2"] },
    "q2": {}
  },
  "test_strings": {
    "accept": ["01", "001"],
    "reject": ["0", "10"]
  }
}
```

- `transitions` admite más de un estado destino por símbolo (AFND) o exactamente
  uno (AFD). No se admiten transiciones épsilon.
- `description` y `test_strings` son opcionales. Si el archivo incluye
  `test_strings`, el programa valida esas cadenas contra las tres etapas
  (entrada, AFD y mínimo) y muestra si coinciden con lo esperado.

## Qué hace el programa, en resumen

1. Lee y valida el autómata de entrada.
2. Si es no determinista, lo convierte a AFD por construcción de subconjuntos.
   Si ya era un AFD pero estaba incompleto o tenía estados inalcanzables, lo
   completa y poda sin renombrar sus estados. Si ya era un AFD completo y sin
   estados inalcanzables, no hace ninguna conversión.
3. Minimiza el AFD resultante (algoritmo de Moore).
4. Verifica formalmente que el AFD mínimo es equivalente al autómata de
   entrada (autómata producto) y que no tiene más estados que el AFD.
5. Guarda el AFD mínimo en un archivo JSON con el mismo formato de entrada.
6. En la GUI, además: dibuja las tres etapas, permite probar una cadena y ver
   su traza paso a paso, y muestra una tabla comparativa de estados y
   transiciones junto con el resultado de los `test_strings` del archivo.

## Solución de problemas

- **"No se encontro Graphviz"**: instalar Graphviz como se indica arriba y
  verificar con `dot -V`. El modo consola funciona igual sin Graphviz.
- **"La interfaz grafica requiere tkinter"**: instalar el paquete de tkinter
  para tu sistema operativo (ver tabla de arriba).
- Los diagramas y el JSON de salida se generan junto al archivo procesado
  (`<entrada>_min.json` y una carpeta `graficos/`).
