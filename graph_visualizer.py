import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


FILE_PATH = "Właściwy_skoroszyt.xlsx"
OUTPUT_DIR = Path("wykresy")
OUTPUT_DIR.mkdir(exist_ok=True)

# Jeżeli mimo wszystko chcesz mieć podpis osi X zawsze jako "k",
# ustaw na True.
FORCE_X_LABEL_K = False

# Stałe kolumn w arkuszach *-Podsumowanie
COL_X = 0
COL_HEUR_TIME = 1
COL_HEUR_STD = 2
COL_HEUR_SUCCESS = 3
COL_HEUR_PATH_COVER = 4      # nieużywane w wykresie 4
COL_SAME_PATHS = 5
COL_CPLEX_TIME = 6
COL_CPLEX_STD = 7
COL_CPLEX_SUCCESS = 8
COL_CPLEX_PATH_COVER = 9     # nieużywane w wykresie 4


def safe_filename(text: str) -> str:
    text = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE)
    return text.strip("_")


def read_summary_sheet(file_path: str, sheet_name: str):
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

    x_label_raw = df.iat[0, COL_X]
    x_label = "k" if FORCE_X_LABEL_K else str(x_label_raw).strip()

    data = df.iloc[2:, :10].copy()

    numeric_cols = [
        COL_X,
        COL_HEUR_TIME,
        COL_HEUR_STD,
        COL_HEUR_SUCCESS,
        COL_HEUR_PATH_COVER,
        COL_SAME_PATHS,
        COL_CPLEX_TIME,
        COL_CPLEX_STD,
        COL_CPLEX_SUCCESS,
        COL_CPLEX_PATH_COVER,
    ]

    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=[COL_X]).reset_index(drop=True)

    return {
        "x_label": x_label,
        "x": data[COL_X],
        "heur_time": data[COL_HEUR_TIME],
        "heur_std": data[COL_HEUR_STD],
        "heur_success": data[COL_HEUR_SUCCESS],
        "same_paths": data[COL_SAME_PATHS],
        "cplex_time": data[COL_CPLEX_TIME],
        "cplex_std": data[COL_CPLEX_STD],
        "cplex_success": data[COL_CPLEX_SUCCESS],
    }


def set_common_style(ax, title, x_label, y_label):
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, linestyle="--", alpha=0.5)


def save_plot(fig, output_path: Path):
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_heuristic_time(sheet_name: str, d: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        d["x"], d["heur_time"], yerr=d["heur_std"],
        fmt="-o", capsize=4, linewidth=2, markersize=5,
        color="#1f77b4", label="Solver heurystyczny"
    )
    set_common_style(
        ax,
        f"{sheet_name} - solver heurystyczny",
        d["x_label"],
        "Czas obliczeń [ms]"
    )
    ax.legend()
    save_plot(fig, OUTPUT_DIR / f"{safe_filename(sheet_name)}_1_heurystyczny_czas.png")


def plot_cplex_time(sheet_name: str, d: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        d["x"], d["cplex_time"], yerr=d["cplex_std"],
        fmt="-o", capsize=4, linewidth=2, markersize=5,
        color="#d62728", label="Cplex"
    )
    set_common_style(
        ax,
        f"{sheet_name} - Cplex",
        d["x_label"],
        "Czas obliczeń [ms]"
    )
    ax.legend()
    save_plot(fig, OUTPUT_DIR / f"{safe_filename(sheet_name)}_2_cplex_czas.png")


def plot_log_compare(sheet_name: str, d: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        d["x"], d["heur_time"],
        "-o", linewidth=2, markersize=5,
        color="#1f77b4", label="Solver heurystyczny"
    )
    ax.plot(
        d["x"], d["cplex_time"],
        "-o", linewidth=2, markersize=5,
        color="#d62728", label="Cplex"
    )
    ax.set_yscale("log")
    set_common_style(
        ax,
        f"{sheet_name} - porównanie czasów (skala log)",
        d["x_label"],
        "Czas obliczeń [ms] - skala log"
    )
    ax.legend()
    save_plot(fig, OUTPUT_DIR / f"{safe_filename(sheet_name)}_3_porownanie_log.png")


def plot_percentages(sheet_name: str, d: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        d["x"], d["heur_success"],
        "-o", linewidth=2, markersize=5,
        color="#1f77b4", label="Skuteczność heurystycznego [%]"
    )
    ax.plot(
        d["x"], d["cplex_success"],
        "-o", linewidth=2, markersize=5,
        color="#d62728", label="Skuteczność Cplex [%]"
    )
    ax.plot(
        d["x"], d["same_paths"],
        "-o", linewidth=2, markersize=5,
        color="#2ca02c", label="Pokrycie się ścieżek [%]"
    )
    set_common_style(
        ax,
        f"{sheet_name} - skuteczność i pokrycie ścieżek",
        d["x_label"],
        "Wartość [%]"
    )
    ax.set_ylim(0, 105)
    ax.legend()
    save_plot(fig, OUTPUT_DIR / f"{safe_filename(sheet_name)}_4_procenty.png")


def main():
    xls = pd.ExcelFile(FILE_PATH, engine="openpyxl")
    summary_sheets = [s for s in xls.sheet_names if "Podsumowanie" in s]

    if not summary_sheets:
        raise ValueError("Nie znaleziono arkuszy podsumowujących.")

    for sheet_name in summary_sheets:
        d = read_summary_sheet(FILE_PATH, sheet_name)

        plot_heuristic_time(sheet_name, d)
        plot_cplex_time(sheet_name, d)
        plot_log_compare(sheet_name, d)
        plot_percentages(sheet_name, d)

    print(f"Gotowe. Wykresy zapisano w katalogu: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()