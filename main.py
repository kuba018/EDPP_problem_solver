from benchmark import BenchmarkConfig, run_benchmark

def main():
    cfg = BenchmarkConfig(
        p_values=range(8, 9),
        w_values=range(30, 31),
        k_values=range(2, 31),
        instances_per_config=100,
        output_csv="benchmark.csv",
    )
    run_benchmark(cfg)

if __name__ == "__main__":
    main()