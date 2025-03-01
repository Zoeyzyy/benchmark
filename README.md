# OptiReduce Benchmarking Guide

This guide explains how to run benchmarks with OptiReduce under different network conditions using controlled background traffic to simulate various network environments.

**Note**: If you have already set up the environment using `make optireduce-full` from the ansible repository, you can skip directly to the [Running Training](#running-training) section.

## Installation Options

### Option 1: Using Ansible (Recommended)

The easiest way to install the benchmark is using our Ansible playbooks:

```bash
git clone https://github.com/OptiReduce/ansible.git
cd ansible
make benchmark-only
```

For detailed instructions on using the Ansible deployment, visit our [Ansible documentation](http://optireduce.github.io/ansible).

### Option 2: Using Benchmark Repository

We provide automated install scripts in our benchmark repository:

```bash
# Clone the benchmark repository
git clone https://github.com/OptiReduce/benchmark.git
cd benchmark

# Install benchmark
make install
```

### Option 3: Manual Installation

If you prefer to install manually, follow these steps:

1. Install Redis server:
```bash
sudo apt update
sudo apt install redis-server
```

2. Clone and build Gloo benchmark:
```bash
# Clone specific version of Gloo
git clone https://github.com/facebookincubator/gloo.git
cd gloo
git checkout e6d509b527712a143996f2f59a10480efa804f8b

# Create build directory
mkdir build
cd build

# Configure and build
cmake ../ -DUSE_REDIS=1 -DBUILD_BENCHMARK=1
make -j$(nproc)
```

## Background Traffic Setup

### 1. Start Redis Server

Choose any ONE node to run the Redis server:

```bash
# Start Redis server
redis-server --port 6199 --protected-mode no

# Clear Redis entries (run before each benchmark)
redis-cli -p 6199 FLUSHALL
```

**Important**: Always clear Redis entries before starting a new benchmark run.

### 2. Create Network Environment

You can simulate different network environments by varying the number of workers for background traffic script (`run_background.sh`). This will result in different tail-to-median latency ratios and allows you to simulate different network conditions by adjusting the `SIZE` parameter:

```bash
Usage: ./run_background.sh -s SIZE -r STARTING_RANK -t TIME [-H REDIS_HOST] [-p REDIS_PORT] [-d DEVICE]

Options:
  -s SIZE           Number of processes
  -r STARTING_RANK  Starting rank
  -t TIME           Iteration time in seconds
  -H REDIS_HOST     Redis host (default: 192.168.100.30)
  -p REDIS_PORT     Redis port (default: 6199)
  -d DEVICE         Network device (default: ens17)
```

#### Exmaple Low-Tail Environment (p99/p50 = 1.5x)

Run these commands on any two nodes:

```bash
# On first node
./run_background.sh -s 4 -r 0 -t 240000 -H <redis_host> -d ens17

# On second node
./run_background.sh -s 4 -r 1 -t 240000 -H <redis_host> -d ens17
```

#### Example High-Tail Environment (p99/p50 = 3x)

For the high-tail environment, increase the SIZE parameter:

```bash
# On first node
./run_background.sh -s 16 -r 0 -t 240000 -H <redis_host> -d ens17

# On second node
./run_background.sh -s 16 -r 1 -t 240000 -H <redis_host> -d ens17
```

#### Parameter Explanation

- `-s SIZE`: Number of processes to spawn. Higher values create more background traffic:
    - 4 processes: Creates low-tail environment (p99/p50 ≈ 1.5x)
    - 16 processes: Creates high-tail environment (p99/p50 ≈ 3x)
- `-r STARTING_RANK`: Starting rank for processes (0 or 1 for two-node setup)
- `-t TIME`: Duration of background traffic in seconds
- `-H REDIS_HOST`: Redis server IP address (must be same for all nodes)
- `-p REDIS_PORT`: Redis server port (default: 6199)
- `-d DEVICE`: Network interface name (e.g., ens17)

**Note: Environment Configuration** 
    The size parameters (4 and 16) are based on our test environment. You may need to adjust these values in your environment to achieve similar p99/p50 latency ratios. Monitor your network conditions and adjust accordingly.

## Running Training

1. Create a DPDK configuration file (`dpdk.cfg`) mapping IP addresses to MAC addresses:

```
192.168.100.10=AA:BB:CC:DD:EE:FF
192.168.100.11=AA:BB:CC:DD:EE:00
```

**Note**
    Ensure all nodes in your cluster are listed in the configuration file.

2. Clear Redis entries:
   ```bash
   redis-cli -p 6199 FLUSHALL
   ```

3. Start background traffic for desired environment (low-tail or high-tail) as shown above

4. Run the training script on each node. You have two options:

   ### Option 1: Run OptiReduce Only (Default)
   ```bash
   ./run_training.sh <MASTER_ADDR> <RANK> <NODES> <DEV> <MODEL>
   ```

   ### Option 2: Run All Communication Schemes
   ```bash
   RUN_ALL=1 ./run_training.sh <MASTER_ADDR> <RANK> <NODES> <DEV> <MODEL>
   ```

   This will run the following schemes in order:
   - NCCL with Ring algorithm
   - NCCL with Tree algorithm
   - Gloo with Ring algorithm
   - Gloo with BCube algorithm
   - Gloo with Transpose algorithm
   - OptiReduce

   Available models:
   - vgg19
   - bert
   - bart
   - roberta
   - gpt2

   Example for a 2-node setup with Mellanox NICs:
   ```bash
   # Run only OptiReduce
   # On master node (rank 0)
   ./run_training.sh 192.168.1.100 0 2 ens17 bert

   # On worker node (rank 1)
   ./run_training.sh 192.168.1.100 1 2 ens17 bert

   # Run all communication schemes
   # On master node (rank 0)
   RUN_ALL=1 ./run_training.sh 192.168.1.100 0 2 ens17 bert

   # On worker node (rank 1)
   RUN_ALL=1 ./run_training.sh 192.168.1.100 1 2 ens17 bert
   ```

   Parameters:
   - MASTER_ADDR: IP address of the master node
   - RANK: Node rank (0 for master, 1,2,... for workers)
   - NODES: Total number of nodes
   - DEV: Network device name (e.g., mlx5_0 for Mellanox NICs)
   - MODEL: One of the available models listed above

## Troubleshooting

### Core Allocation
- OptiReduce requires at least 4 dedicated CPU cores for running 
- Ensure `taskset -c 1-8` in run_training.sh matches your system's available cores for PyTorch
- The `--tr_threads_offset` parameter should be set to avoid core conflicts with the PyTorch app and must not overlap with the taskset cores
- Example: If using cores 1-8 for Pytorch, set `--tr_threads_offset 11` to ensure thread IDs don't overlap

### Timeout Settings
- The `--tr_timeout` parameter is crucial for proper operation
- Default values in the script:
  - vgg19: 135
  - bert: 350
  - bart: 370
  - roberta: 370
  - gpt2: 370
- You may need to adjust these based on your model size and network conditions
- For detailed explanation of timeout calculations, refer to our [Technical Details](http://optireduce.github.io/technical-details) page

### Customizing Training Parameters
You might need to modify the following parameters in run_training.sh for your specific use case:
```bash
case $MODEL in
    vgg19)
        BATCH_SIZE=128    # Adjust based on your GPU memory
        EPOCHS=150        # Increase/decrease based on model convergence
        TR_TIMEOUT=135    # Adjust based on network conditions and number of nodes
        ;;
    bert)
        BATCH_SIZE=16
        EPOCHS=5
        TR_TIMEOUT=350
        ;;
    # ... other models
esac
```

### Results

The following table compares the iteration time (**s/it**) for different communication strategies, lower is better:

| Model          | Env | NCCL-Ring | NCCL-Tree | Ring  | BCube | TAR+TCP | **OptiReduce** |
|---------------|-----|-----------|-----------|-------|-------|---------|--------------|
| **GPT-2**     | 1.5 | 1.70 s    | 1.52 s    | 2.20 s | 2.45 s | 2.12 s | **1.39 s**  |
|               | 3   | 2.26 s    | 1.91 s    | 2.66 s | 2.99 s | 2.36 s | **1.41 s**  |
| **GPT-2-large** | 1.5 | 7.76 s | 6.46 s | 8.96 s | 10.45 s | 7.92 s | **6.01 s**  |
|               | 3   | 10.12 s   | 9.34 s    | 10.60 s | 10.80 s | 8.48 s | **6.07 s**  |
| **BERT-large** | 1.5 | 5.01 s | 4.24 s | 6.10 s | 7.30 s | 5.90 s | **3.76 s**  |
|               | 3   | 6.53 s    | 5.21 s    | 8.11 s | 8.19 s | 6.46 s | **3.85 s**  |
| **BART-large** | 1.5 | 4.67 s | 4.07 s | 6.94 s | 7.72 s | 5.45 s | **3.80 s**  |
|               | 3   | 6.90 s    | 5.74 s    | 7.70 s | 8.11 s | 5.88 s | **3.90 s**  |
| **RoBERTa-large** | 1.5 | 4.75 s | 4.15 s | 6.12 s | 7.64 s | 5.94 s | **3.87 s**  |
|               | 3   | 7.30 s    | 5.51 s    | 8.09 s | 8.99 s | 6.71 s | **3.92 s**  |
| **Llama-3.2** | 1.5 | 12.92 s | 10.28 s | 15.15 s | 16.54 s | 11.25 s | **9.73 s**  |
|               | 3   | 17.28 s   | 15.72 s   | 18.84 s | 21.97 s | 14.59 s | **9.98 s**  |

---

**Analysis**
- **OptiReduce consistently outperforms all other methods** across different models and environments.
- Performance gains are especially significant for **larger models** (GPT-2-large, Llama-3.2), where OptiReduce achieves **up to 40% faster iteration time** in low-tail environment.
- The benefits are **more pronounced in multi-node environments** (`Env=3`), where communication bottlenecks become more severe and speedups reach around **2x**.

### Common Issues

1. **Performance Degradation**
   - Check CPU core allocation
   - Verify thread offset settings
   - Monitor system for other processes using assigned cores

2. **Training Failures**
   - Ensure adequate timeout values
   - Verify network device names
   - Check Redis server is running and accessible

3. **Network Device Issues**
   - Confirm correct device name (e.g., ens17)
   - Check DPDK binding status
   - Verify hugepages configuration

## Support

For issues specifically related to deployment:
1. Review the installation logs in detail
2. Open an issue in the github repository

For general OptiReduce questions and usage, please refer to our [official documentation](http://optireduce.github.io/).

## License

This deployment code is part of the OptiReduce project. Please refer to the main project page for license information.