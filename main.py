from config import SystemConfig
from models.process import Process
from simulation.simulator import Simulator
from strategies.fifo import FIFOStrategy
from strategies.look import LOOKStrategy
from strategies.nlook import NLOOKStrategy


def print_header(cache_name: str, strategy_name: str):
    print(f"Buffer cache {cache_name}")
    print(f"Device strategy {strategy_name}")
    print()


def scenario_1_simple_read():
    # Scenario 1 read sector 100
    print("=" * 70)
    print("SCENARIO 1: Process reads sector 100 (FIFO)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "FIFO")

    simulator = Simulator(config, FIFOStrategy)

    process_yyy = Process('yyy', [('r', 100)])
    simulator.add_process(process_yyy)

    simulator.run()
    print()


def scenario_2_simple_write():
    # Scenario 2 modification sector 100 FIFO
    print("=" * 70)
    print("SCENARIO 2: Process modifies sector 100 (FIFO)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "FIFO")

    simulator = Simulator(config, FIFOStrategy)

    process_yyy = Process('yyy', [('w', 100)])
    simulator.add_process(process_yyy)

    simulator.run()
    print()


def scenario_3_two_processes():
    # Scenario 3 read sector 100 modification sector 1000
    print("=" * 70)
    print("SCENARIO 3: Two processes, different sectors r 100 and w 1000 (FIFO)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "FIFO")

    simulator = Simulator(config, FIFOStrategy)

    process_yyy = Process('yyy', [('r', 100)])
    process_qqq = Process('qqq', [('w', 1000)])

    simulator.add_process(process_yyy)
    simulator.add_process(process_qqq)

    simulator.run()
    print()


def scenario_4_same_sector():
    # Scenario 4 Two processes read sector 100
    print("=" * 70)
    print("SCENARIO 4: Two processes, same sector (cache hit) (FIFO)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "FIFO")

    simulator = Simulator(config, FIFOStrategy)

    process_yyy = Process('yyy', [('r', 100)])
    process_qqq = Process('qqq', [('r', 100)])

    simulator.add_process(process_yyy)
    simulator.add_process(process_qqq)

    simulator.run()
    print()


def scenario_5_multiple_operations():
    # Scenario 5 The number of buffers in the buffer cache is insufficient for all the blocks accessed by the process.
    print("=" * 70)
    print("SCENARIO 5: Multiple operations, cache eviction (FIFO)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "FIFO")

    simulator = Simulator(config, FIFOStrategy)

    operations = [
        ('r', 100),
        ('r', 110),
        ('r', 120),
        ('r', 130),
        ('r', 140),
        ('r', 150),
        ('r', 160),
        ('r', 170),
        ('r', 180),
        ('r', 190),
        ('w', 200),
    ]

    process_yyy = Process('yyy', operations)
    simulator.add_process(process_yyy)

    simulator.run()
    print()


def scenario_6_look_strategy():
    # Scenario 6 LOOK read sector 100 modification sector 100
    print("=" * 70)
    print("SCENARIO 6: Two processes, same sector w 100 r 100 (LOOK)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "LOOK (track_read_max 1)")

    simulator = Simulator(config, LOOKStrategy)

    process_yyy = Process('yyy', [('r', 100)])
    process_qqq = Process('qqq', [('w', 100)])

    simulator.add_process(process_yyy)
    simulator.add_process(process_qqq)

    simulator.run()
    print()


def scenario_7_look_three_read_max_1():
    # Scenario 7 LOOK three read processes track_read_max 1
    print("=" * 70)
    print("SCENARIO 7: Three processes r 100, 110, 1500 (LOOK track_read_max 1)")
    print("=" * 70)
    print()

    config = SystemConfig()

    print_header("LFU (3 segments)", "LOOK (1)")

    simulator = Simulator(config, LOOKStrategy)

    process_yyy = Process('yyy', [('r', 100)])
    process_qqq = Process('qqq', [('r', 110)])
    process_eee = Process('eee', [('r', 1500)])

    simulator.add_process(process_yyy)
    simulator.add_process(process_qqq)
    simulator.add_process(process_eee)

    simulator.run()
    print()


def scenario_8_look_three_read_max_2():
    # Scenario 8 LOOK three read processes track_read_max 2
    print("=" * 70)
    print("SCENARIO 7: Three processes r 100, 110, 1500 (LOOK track_read_max 2)")
    print("=" * 70)
    print()

    config = SystemConfig()
    config.LOOK_TRACK_READ_MAX = 2

    print_header("LFU (3 segments)", "LOOK (2)")

    simulator = Simulator(config, LOOKStrategy)

    process_yyy = Process('yyy', [('r', 100)])
    process_qqq = Process('qqq', [('r', 110)])
    process_eee = Process('eee', [('r', 1500)])

    simulator.add_process(process_yyy)
    simulator.add_process(process_qqq)
    simulator.add_process(process_eee)

    simulator.run()
    print()


def scenario_9_nlook_complex_processes():
    # Scenario 9 NLOOK complex processes
    print("=" * 70)
    print("SCENARIO 7: Four processes (NLOOK num 10)")
    print("=" * 70)
    print()

    config = SystemConfig()
    print_header("LFU (3 segments)", "NLOOK (num 10)")

    simulator = Simulator(config, NLOOKStrategy)
    process_yyy = Process('yyy', [('r', 1000), ('r', 1500), ('r', 100)])
    process_qqq = Process('qqq', [('w', 150), ('r', 700), ('r', 1250)])
    process_eee = Process('eee', [('r', 3000), ('w', 1550), ('r', 2700)])
    process_nnn = Process('nnn', [('w', 1110), ('r', 3100)])

    simulator.add_process(process_yyy)
    simulator.add_process(process_qqq)
    simulator.add_process(process_eee)
    simulator.add_process(process_nnn)

    simulator.run()
    print()


def compare_strategies():
    print("=" * 70)
    print("STRATEGY COMPARISON")
    print("=" * 70)
    print()

    processes_config = [
        ('yyy', [('r', 1000), ('r', 1500), ('r', 100)]),
        ('qqq', [('w', 150), ('r', 700), ('r', 1250)]),
        ('eee', [('r', 2950), ('w', 250), ('r', 2700)]),
        ('nnn', [('w', 1110), ('r', 350)]),
        ('yyy1', [('r', 2100), ('r', 3700), ('r', 270)]),
        ('qqq1', [('w', 3290), ('r', 490), ('r', 1250)]),
        ('eee1', [('r', 380), ('w', 1550), ('r', 2300)]),
        ('nnn1', [('w', 1250), ('r', 190)])
    ]

    strategies = [
        ("FIFO", FIFOStrategy),
        ("LOOK", LOOKStrategy),
        ("NLOOK", NLOOKStrategy),
    ]

    results = {}

    for strategy_name, strategy_class in strategies:
        print(f"Testing {strategy_name}...", end=" ")

        config = SystemConfig()
        simulator = Simulator(config, strategy_class)

        for proc_name, operations in processes_config:
            process = Process(proc_name, operations)
            simulator.add_process(process)

        simulator.run()

        results[strategy_name] = {
            'total_time': simulator.current_time,
            'total_seeks': simulator.disk.total_seeks,
            'total_seek_time': simulator.disk.total_seek_time,
        }

        print(
            f"Done (Time: {int(simulator.current_time)} μs, Seeks: {simulator.disk.total_seeks}, Seek Time: {results[strategy_name]['total_seek_time']:.2f} ms)")
        print()

    print()
    print(f"{'Strategy':<15} {'Total Time (μs)':<20} {'Seeks':<10} {'Seek Time (ms)':<15}")
    print("-" * 70)

    for strategy_name in ['FIFO', 'LOOK', 'NLOOK']:
        stats = results[strategy_name]
        print(f"{strategy_name:<15} {int(stats['total_time']):<20} "
              f"{stats['total_seeks']:<10} {stats['total_seek_time']:<15.2f}")


def main():
    print("Available scenarios:")
    print("1. Sector 100 read operation (FIFO)")
    print("2. Sector 100 modification operation (FIFO)")
    print("3. Sector 100 read, sector 1000 modification (FIFO)")
    print("4. Sector 100 read two processes (FIFO)")
    print("5. Insufficient amount of buffers for all the blocks (FIFO)")
    print("6. Sector 100 read and write by different processes (LOOK track_read_max 1)")
    print("7. Sectors 100, 110, 1500 read by different processes (LOOK track_read_max 1)")
    print("8. Sectors 100, 110, 1500 read by different processes (LOOK track_read_max 2)")
    print("9. Four processes with different operations (NLOOK num 10)")
    print("0. Compare FIFO, LOOK, and NLOOK in complex situation")
    print()

    choice = input("Select scenario (1-9): ").strip()
    print()

    scenarios = {
        '1': scenario_1_simple_read,
        '2': scenario_2_simple_write,
        '3': scenario_3_two_processes,
        '4': scenario_4_same_sector,
        '5': scenario_5_multiple_operations,
        '6': scenario_6_look_strategy,
        '7': scenario_7_look_three_read_max_1,
        '8': scenario_8_look_three_read_max_2,
        '9': scenario_9_nlook_complex_processes,
        '0': compare_strategies
    }

    if choice in scenarios:
        scenarios[choice]()
    else:
        print("Invalid choice. Running default scenario...")
        scenario_1_simple_read()


if __name__ == "__main__":
    main()
