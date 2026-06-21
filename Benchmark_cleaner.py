import os
import pandas as pd

INPUT_FILE = "benchmark.csv"          # UPEWNIJ SIĘ, ŻE TEN PLIK ISTNIEJE
SHEET_NAME = "P1-30"
OUTPUT_FILE = "podsumowanie_solverow.xlsx"


def _load_input(path: str, sheet_name: str | None):
    ext = os.path.splitext(path)[1].lower()
    print("Ładuję plik:", path, "ext:", ext)
    if ext in [".xlsx", ".xlsm", ".xls"]:
        return pd.read_excel(path, sheet_name=sheet_name)
    if ext == ".csv":
        return pd.read_csv(path, sep=";")
    raise ValueError(f"Nieobsługiwane rozszerzenie pliku: {ext}")


def run_cleaner(group_by_col: str = "w"):
    print("run_cleaner START")
    df = _load_input(INPUT_FILE, SHEET_NAME)
    print("wczytano df, kolumny:", list(df.columns))

    if group_by_col not in df.columns:
        raise ValueError(f"Kolumna '{group_by_col}' nie istnieje w danych.")

    bool_cols = [
        "heuristic_success",
        "heuristic_matches_guaranteed",
        "cplex_success",
        "cplex_matches_guaranteed",
        "same_paths",
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    num_cols = [
        "heuristic_time_sec",
        "cplex_time_sec",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "."),
                errors="coerce",
            )

    g = df.groupby(group_by_col)

    solver1 = pd.DataFrame(
        {
            group_by_col: g.size().index,
            "czas_ms_heur": g["heuristic_time_sec"].mean() * 1000.0,
            "std_ms_heur": g["heuristic_time_sec"].std(ddof=1) * 1000.0,
            "skutecznosc_pct_heur": g["heuristic_success"].mean() * 100.0,
            "coverage_pct_heur": g["heuristic_matches_guaranteed"].mean() * 100.0,
        }
    ).reset_index(drop=True)

    solver2 = pd.DataFrame(
        {
            group_by_col: g.size().index,
            "czas_ms_cplex": g["cplex_time_sec"].mean() * 1000.0,
            "std_ms_cplex": g["cplex_time_sec"].std(ddof=1) * 1000.0,
            "skutecznosc_pct_cplex": g["cplex_success"].mean() * 100.0,
            "coverage_pct_cplex": g["cplex_matches_guaranteed"].mean() * 100.0,
        }
    ).reset_index(drop=True)

    same_paths_pct = (g["same_paths"].mean() * 100.0).reset_index()
    same_paths_pct.columns = [group_by_col, "same_paths_pct"]

    merged = (
        solver1.merge(same_paths_pct, on=group_by_col)
        .merge(solver2, on=group_by_col)
        .sort_values(by=group_by_col)
        .reset_index(drop=True)
    )

    print("merged shape:", merged.shape)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        merged.to_excel(
            writer,
            sheet_name="Podsumowanie",
            index=False,
            header=False,
            startrow=1,
            startcol=0,
        )

    print(f"Wyniki (grupowanie po '{group_by_col}') zapisane do: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_cleaner("k")