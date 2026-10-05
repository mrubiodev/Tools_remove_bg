#!/usr/bin/env python3
"""
remove_bg.py — Eliminador de fondos de imágenes usando rembg (U2Net).

Dependencias:
    pip install rembg Pillow onnxruntime

Uso:
    # Imagen individual:
    python remove_bg.py imagen.jpg

    # Imagen individual con salida explícita:
    python remove_bg.py imagen.jpg -o resultado.png

    # Procesamiento batch (directorio completo):
    python remove_bg.py ./imagenes/ -o ./salida/

    # Usar modelo alternativo (ver MODELOS más abajo):
    python remove_bg.py imagen.jpg --model u2netp

    # Añadir fondo de color tras eliminar el original:
    python remove_bg.py imagen.jpg --bg-color "#FFFFFF"

    # Alpha matting para bordes más suaves (cabello, pelo, etc.):
    python remove_bg.py imagen.jpg --alpha-matting
"""

import argparse
import sys
from pathlib import Path

from PIL import Image
try:
    from rembg import remove, new_session
except ImportError:
    print(
        "Error: module 'rembg' not found.\n"
        "Ensure you are running this script with the project's virtualenv.\n"
        "In PowerShell:\n"
        "  & .venv\\Scripts\\Activate.ps1\n"
        "  python remove_bg.py <imagen> -o resultado.png\n"
        "Or run directly with the venv python:\n"
        "  .venv\\Scripts\\python.exe remove_bg.py <imagen> -o resultado.png\n"
        "Or install requirements into the active interpreter:\n"
        "  pip install -r requirements.txt\n",
        file=sys.stderr,
    )
    sys.exit(1)

# GUI imports (solo usados si se lanza la ventana)
try:
    import tkinter as tk
    from tkinter import filedialog, colorchooser, messagebox, ttk
except Exception:
    tk = None

# ---------------------------------------------------------------------------
# MODELOS DISPONIBLES EN REMBG
# ---------------------------------------------------------------------------
# u2net          → General (por defecto). Bueno para la mayoría de casos.
# u2netp         → Versión ligera de u2net. Más rápido, algo menos preciso.
# u2net_human_seg→ Optimizado para personas/retratos.
# u2net_cloth_seg→ Segmentación de ropa.
# silueta        → Contornos limpios para siluetas simples.
# isnet-general-use → Alta precisión general, más lento.
# isnet-anime    → Optimizado para ilustraciones y anime.
# birefnet-general → Muy alta precisión (requiere más RAM).
# ---------------------------------------------------------------------------
MODELOS_VALIDOS = {
    "u2net", "u2netp", "u2net_human_seg", "u2net_cloth_seg",
    "silueta", "isnet-general-use", "isnet-anime", "birefnet-general",
}

EXTENSIONES_SOPORTADAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Elimina el fondo de imágenes usando rembg (U2Net/ISNet).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=None,
        help="Imagen de entrada o directorio con imágenes. (Opcional: si no se pasa, se abre GUI)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help=(
            "Salida: archivo .png (si input es imagen) o directorio (si input es "
            "directorio). Por defecto, mismo directorio con sufijo '_nobg'."
        ),
    )
    parser.add_argument(
        "--model",
        default="u2net",
        choices=MODELOS_VALIDOS,
        help="Modelo de segmentación a usar (por defecto: u2net).",
    )
    parser.add_argument(
        "--bg-color",
        default=None,
        metavar="COLOR",
        help=(
            "Color de fondo a aplicar tras eliminar el original. "
            "Formato hex: '#FFFFFF', '#000000', etc. Por defecto: transparente."
        ),
    )
    parser.add_argument(
        "--alpha-matting",
        action="store_true",
        help=(
            "Activa alpha matting para bordes más precisos (cabello, pelo, bordes "
            "complejos). Más lento."
        ),
    )
    parser.add_argument(
        "--alpha-fg",
        type=int,
        default=240,
        metavar="0-255",
        help="Umbral foreground para alpha matting (por defecto: 240).",
    )
    parser.add_argument(
        "--alpha-bg",
        type=int,
        default=10,
        metavar="0-255",
        help="Umbral background para alpha matting (por defecto: 10).",
    )
    parser.add_argument(
        "--alpha-erode",
        type=int,
        default=10,
        metavar="N",
        help="Tamaño de erosión para alpha matting (por defecto: 10).",
    )
    return parser.parse_args()


def hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """Convierte color hex (#RRGGBB o #RGB) a tupla RGBA con alpha=255."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        raise ValueError(f"Color inválido: '#{hex_color}'. Usa formato #RRGGBB.")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (r, g, b, 255)


def aplicar_fondo_color(imagen_rgba: Image.Image, color_rgba: tuple) -> Image.Image:
    """Compone la imagen RGBA sobre un fondo de color sólido."""
    fondo = Image.new("RGBA", imagen_rgba.size, color_rgba)
    fondo.paste(imagen_rgba, mask=imagen_rgba.split()[3])  # usa canal alpha como máscara
    return fondo.convert("RGB")  # convierte a RGB porque el fondo ya no es transparente


def procesar_imagen(
    ruta_entrada: Path,
    ruta_salida: Path,
    session,
    bg_color_rgba: tuple | None,
    alpha_matting: bool,
    alpha_fg: int,
    alpha_bg: int,
    alpha_erode: int,
) -> bool:
    """
    Procesa una imagen individual: elimina el fondo y guarda el resultado.
    Retorna True si tuvo éxito, False si hubo error.
    """
    try:
        with open(ruta_entrada, "rb") as f:
            datos_entrada = f.read()

        # Llamada principal a rembg
        datos_salida = remove(
            datos_entrada,
            session=session,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_fg,
            alpha_matting_background_threshold=alpha_bg,
            alpha_matting_erode_size=alpha_erode,
        )

        # Carga la imagen resultante (siempre RGBA con canal alpha)
        from io import BytesIO
        imagen = Image.open(BytesIO(datos_salida)).convert("RGBA")

        # Aplica fondo de color si se especificó
        if bg_color_rgba is not None:
            imagen = aplicar_fondo_color(imagen, bg_color_rgba)

        # Asegura que el directorio de salida existe
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        # Guarda siempre como PNG para preservar transparencia (o fondo sólido)
        imagen.save(ruta_salida, format="PNG")
        print(f"  ✓ {ruta_entrada.name} → {ruta_salida}")
        return True

    except Exception as e:
        print(f"  ✗ Error procesando '{ruta_entrada}': {e}", file=sys.stderr)
        return False


def resolver_salida_imagen(ruta_entrada: Path, salida_arg: Path | None) -> Path:
    """Determina la ruta de salida para una imagen individual."""
    if salida_arg is not None:
        # Si se especificó explícitamente, úsala (fuerza extensión .png)
        return salida_arg.with_suffix(".png")
    # Por defecto: mismo directorio, mismo nombre + sufijo, extensión .png
    return ruta_entrada.parent / f"{ruta_entrada.stem}_nobg.png"


def resolver_salida_batch(ruta_entrada: Path, dir_salida: Path | None) -> Path:
    """Determina el directorio de salida para procesamiento batch."""
    if dir_salida is not None:
        return dir_salida
    # Por defecto: subdirectorio 'nobg' dentro del directorio de entrada
    return ruta_entrada / "nobg"


def gui_get_args() -> argparse.Namespace:
    """Muestra una ventana Tkinter para seleccionar opciones cuando no hay args."""
    if tk is None:
        print("Error: tkinter no está disponible en este entorno.", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    root.title("Eliminar fondo — GUI")

    input_path = tk.StringVar()
    output_path = tk.StringVar()
    model_var = tk.StringVar(value="u2net")
    bg_color_var = tk.StringVar(value="")
    alpha_matting_var = tk.BooleanVar(value=False)
    alpha_fg_var = tk.IntVar(value=240)
    alpha_bg_var = tk.IntVar(value=10)
    alpha_erode_var = tk.IntVar(value=10)

    def choose_file():
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif")])
        if p:
            input_path.set(p)

    def choose_dir():
        p = filedialog.askdirectory()
        if p:
            input_path.set(p)

    def choose_output():
        p = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if p:
            output_path.set(p)

    def pick_color():
        c = colorchooser.askcolor()
        if c and c[1]:
            bg_color_var.set(c[1])

    row = 0
    tk.Label(root, text="Entrada:").grid(row=row, column=0, sticky="w", padx=6, pady=6)
    tk.Entry(root, textvariable=input_path, width=50).grid(row=row, column=1, columnspan=3, padx=6)
    tk.Button(root, text="Archivo...", command=choose_file).grid(row=row, column=4, padx=6)
    row += 1
    tk.Button(root, text="Directorio...", command=choose_dir).grid(row=row, column=4, padx=6)

    row += 1
    tk.Label(root, text="Salida (opcional):").grid(row=row, column=0, sticky="w", padx=6, pady=6)
    tk.Entry(root, textvariable=output_path, width=50).grid(row=row, column=1, columnspan=3, padx=6)
    tk.Button(root, text="Guardar como...", command=choose_output).grid(row=row, column=4, padx=6)

    row += 1
    tk.Label(root, text="Modelo:").grid(row=row, column=0, sticky="w", padx=6, pady=6)
    combo = ttk.Combobox(root, textvariable=model_var, values=sorted(MODELOS_VALIDOS), state="readonly")
    combo.grid(row=row, column=1, padx=6, sticky="w")

    tk.Label(root, text="Color fondo:").grid(row=row, column=2, sticky="w", padx=6)
    tk.Entry(root, textvariable=bg_color_var).grid(row=row, column=3, padx=6, sticky="w")
    tk.Button(root, text="Elegir", command=pick_color).grid(row=row, column=4, padx=6)

    row += 1
    tk.Checkbutton(root, text="Alpha matting", variable=alpha_matting_var).grid(row=row, column=0, sticky="w", padx=6, pady=6)
    tk.Label(root, text="fg:").grid(row=row, column=1, sticky="e")
    tk.Entry(root, textvariable=alpha_fg_var, width=6).grid(row=row, column=2, sticky="w")
    tk.Label(root, text="bg:").grid(row=row, column=3, sticky="e")
    tk.Entry(root, textvariable=alpha_bg_var, width=6).grid(row=row, column=4, sticky="w")

    row += 1
    tk.Label(root, text="Erode size:").grid(row=row, column=0, sticky="w", padx=6, pady=6)
    tk.Entry(root, textvariable=alpha_erode_var, width=6).grid(row=row, column=1, sticky="w")

    result = {}

    def on_process():
        if not input_path.get():
            messagebox.showerror("Error", "Debe seleccionar una entrada (archivo o directorio).")
            return
        result["input"] = input_path.get()
        result["output"] = output_path.get() or None
        result["model"] = model_var.get()
        result["bg_color"] = bg_color_var.get() or None
        result["alpha_matting"] = bool(alpha_matting_var.get())
        result["alpha_fg"] = int(alpha_fg_var.get())
        result["alpha_bg"] = int(alpha_bg_var.get())
        result["alpha_erode"] = int(alpha_erode_var.get())
        root.destroy()

    def on_cancel():
        root.destroy()

    row += 1
    tk.Button(root, text="Procesar", command=on_process, bg="#4CAF50", fg="white").grid(row=row, column=2, pady=10)
    tk.Button(root, text="Cancelar", command=on_cancel).grid(row=row, column=3, pady=10)

    root.resizable(False, False)
    root.mainloop()

    if not result:
        print("Operación cancelada.", file=sys.stderr)
        sys.exit(1)

    # Construye Namespace similar a argparse
    ns = argparse.Namespace()
    ns.input = Path(result["input"])
    ns.output = Path(result["output"]) if result["output"] is not None else None
    ns.model = result["model"]
    ns.bg_color = result["bg_color"]
    ns.alpha_matting = result["alpha_matting"]
    ns.alpha_fg = result["alpha_fg"]
    ns.alpha_bg = result["alpha_bg"]
    ns.alpha_erode = result["alpha_erode"]
    return ns


def main():
    args = parse_args()

    # Si no se proporcionaron argumentos por CLI, usar GUI
    if args.input is None:
        args = gui_get_args()

    # --- Validaciones previas ---
    if not args.input.exists():
        print(f"Error: la ruta '{args.input}' no existe.", file=sys.stderr)
        sys.exit(1)

    # Parsea color de fondo si se proporcionó
    bg_color_rgba = None
    if args.bg_color:
        try:
            bg_color_rgba = hex_to_rgba(args.bg_color)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Carga la sesión del modelo (se descarga automáticamente la primera vez)
    print(f"Cargando modelo '{args.model}'...")
    session = new_session(args.model)

    kwargs_matting = {
        "alpha_matting": args.alpha_matting,
        "alpha_fg": args.alpha_fg,
        "alpha_bg": args.alpha_bg,
        "alpha_erode": args.alpha_erode,
    }

    # --- Modo: imagen individual ---
    if args.input.is_file():
        if args.input.suffix.lower() not in EXTENSIONES_SOPORTADAS:
            print(
                f"Error: extensión '{args.input.suffix}' no soportada. "
                f"Usa: {', '.join(sorted(EXTENSIONES_SOPORTADAS))}",
                file=sys.stderr,
            )
            sys.exit(1)

        ruta_salida = resolver_salida_imagen(args.input, args.output)
        print(f"Procesando imagen individual...")
        ok = procesar_imagen(args.input, ruta_salida, session, bg_color_rgba, **kwargs_matting)
        sys.exit(0 if ok else 1)

    # --- Modo: batch (directorio) ---
    elif args.input.is_dir():
        dir_salida = resolver_salida_batch(args.input, args.output)

        # Recopila todas las imágenes soportadas recursivamente (nivel superior)
        imagenes = [
            f for f in sorted(args.input.iterdir())
            if f.is_file() and f.suffix.lower() in EXTENSIONES_SOPORTADAS
        ]

        if not imagenes:
            print(f"No se encontraron imágenes en '{args.input}'.", file=sys.stderr)
            sys.exit(1)

        print(f"Procesando {len(imagenes)} imagen(es) → '{dir_salida}'...")
        exitos = 0
        for img in imagenes:
            salida = dir_salida / f"{img.stem}_nobg.png"
            if procesar_imagen(img, salida, session, bg_color_rgba, **kwargs_matting):
                exitos += 1

        print(f"\nCompletado: {exitos}/{len(imagenes)} imágenes procesadas.")
        sys.exit(0 if exitos == len(imagenes) else 1)

    else:
        print(f"Error: '{args.input}' no es un archivo ni un directorio.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
