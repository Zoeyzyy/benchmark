#!/bin/bash

# Usage function
usage() {
    echo "Usage: $0 -s SIZE -r STARTING_RANK -t TIME [-H REDIS_HOST] [-p REDIS_PORT] [-d DEVICE]"
    echo "Options:"
    echo "  -s SIZE           Number of processes"
    echo "  -r STARTING_RANK  Starting rank"
    echo "  -t TIME           Iteration time in seconds"
    echo "  -H REDIS_HOST     Redis host (default: 192.168.100.30)"
    echo "  -p REDIS_PORT     Redis port (default: 6199)"
    echo "  -d DEVICE         Network device (default: eno33np0)"
    exit 1
}

# Paths and directories for the benchmark
INSTALL_DIR=$HOME
BENCHMARK_DIR=$INSTALL_DIR/gloo/build/gloo/benchmark

# Default values
REDIS_HOST="192.168.100.30"
REDIS_PORT="6199"
TCP_DEVICE="ens17"

# Parse input arguments
while getopts ":s:r:t:H:p:d:" opt; do
  case $opt in
    s) SIZE="$OPTARG"
    ;;
    r) STARTING_RANK="$OPTARG"
    ;;
    t) ITERATION_TIME="$OPTARG"s
    ;;
    H) REDIS_HOST="$OPTARG"
    ;;
    p) REDIS_PORT="$OPTARG"
    ;;
    d) TCP_DEVICE="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
        usage
    ;;
  esac
done

# Check if the necessary arguments are provided
if [ -z "$SIZE" ] || [ -z "$STARTING_RANK" ] || [ -z "$ITERATION_TIME" ]; then
    usage
fi

# Set other constant variables
TRANSPORT="tcp"
ELEMENTS="2048000"
COMMAND="new_allreduce_ring"

# Print configuration
echo "Running with configuration:"
echo "Size: $SIZE"
echo "Starting Rank: $STARTING_RANK"
echo "Iteration Time: $ITERATION_TIME"
echo "Redis Host: $REDIS_HOST"
echo "Redis Port: $REDIS_PORT"
echo "Network Device: $TCP_DEVICE"

# Execute the commands
RANK=$STARTING_RANK
while [ $RANK -lt $SIZE ]; do
  $BENCHMARK_DIR/benchmark \
    --size $SIZE \
    --rank $RANK \
    --redis-host $REDIS_HOST \
    --redis-port $REDIS_PORT \
    --transport $TRANSPORT \
    --tcp-device $TCP_DEVICE \
    --elements $ELEMENTS \
    --iteration-time $ITERATION_TIME \
    $COMMAND &
  RANK=$((RANK + 2))
done

# Wait for all background processes to complete
wait