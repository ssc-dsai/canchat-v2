#!/bin/bash
# performance_test_llama_guard.sh
# Practical performance & cost testing for Llama Guard on NVIDIA GPUs
#
# Usage: ./performance_test_llama_guard.sh [num_iterations] [model]
# Example: ./performance_test_llama_guard.sh 10 llama-guard3:8b
#
# Measures:
# - Inference latency
# - GPU utilization and memory usage
# - Inference cost estimation
# - Throughput
#
# Works with local Ollama CLI (reliable, avoids API issues)

set -e

NUM_ITERATIONS="${1:-100}"
MODEL_NAME="${2:-llama-guard3:8b}"
RESULTS_DIR="/tmp/llama_guard_perf_test"
mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$RESULTS_DIR/results_${TIMESTAMP}.txt"
CSV_FILE="$RESULTS_DIR/metrics_${TIMESTAMP}.csv"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║    Llama Guard Performance Test (NVIDIA GPU)                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Model: $MODEL_NAME"
echo "  Iterations: $NUM_ITERATIONS"
echo "  Results: $RESULTS_FILE"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Install from: https://ollama.com"
    exit 1
fi
echo "✅ Ollama installed: $(ollama --version)"

# Check NVIDIA (required)
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ NVIDIA GPU tools not found. Install nvidia-utils or CUDA toolkit"
    exit 1
fi
echo "✅ NVIDIA GPU detected:"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | sed 's/^/   /'

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 1: Model Availability Check"
echo "═══════════════════════════════════════════════════════════════"

# Test model availability
if ! ollama list 2>/dev/null | grep -q "$(echo $MODEL_NAME | cut -d: -f1)"; then
    echo "❌ Model $MODEL_NAME not found locally"
    echo "   Pull it with: ollama pull $MODEL_NAME"
    exit 1
fi
echo "✅ Model $MODEL_NAME available"

# Quick test run
echo "Testing model execution..."
TEST_RESULT=$(ollama run $MODEL_NAME "safe" 2>/dev/null | head -1)
if [[ "$TEST_RESULT" == "safe" ]] || [[ "$TEST_RESULT" == "unsafe" ]]; then
    echo "✅ Model responds correctly"
else
    echo "⚠️  Unexpected response: $TEST_RESULT"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 2: Performance Benchmarking"
echo "═══════════════════════════════════════════════════════════════"

# Test messages
declare -a TEST_MESSAGES=(
    "What is the capital of France?"
    "Tell me about machine learning"
    "How do I learn Python?"
    "How do I make a bomb?"
    "What are AI risks?"
    "Explain quantum computing"
    "How to hack a server?"
    "What is blockchain?"
)

# CSV header
echo "iteration,latency_ms,result,gpu_util_pct,gpu_memory_mb,gpu_temp_c" > "$CSV_FILE"

declare -a LATENCIES
TOTAL_LATENCY=0
SAFE_COUNT=0
UNSAFE_COUNT=0

echo ""
echo "Running $NUM_ITERATIONS iterations..."
echo ""

for ((i=1; i<=NUM_ITERATIONS; i++)); do
    MSG_INDEX=$((RANDOM % ${#TEST_MESSAGES[@]}))
    MSG="${TEST_MESSAGES[$MSG_INDEX]}"
    
    # Get pre-inference GPU metrics
    PRE_GPU=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader,nounits | head -1)
    PRE_GPU_UTIL=$(echo "$PRE_GPU" | awk -F',' '{print $1}')
    PRE_GPU_MEM=$(echo "$PRE_GPU" | awk -F',' '{print $2}')
    PRE_GPU_TEMP=$(echo "$PRE_GPU" | awk -F',' '{print $3}')
    
    # Run inference and time it
    START_TIME=$(date +%s%N)
    RESULT=$(ollama run $MODEL_NAME "$MSG" 2>/dev/null | head -1)
    END_TIME=$(date +%s%N)
    
    LATENCY=$(( (END_TIME - START_TIME) / 1000000 ))
    LATENCIES+=($LATENCY)
    TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))
    
    # Get post-inference GPU metrics
    POST_GPU=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader,nounits | head -1)
    POST_GPU_UTIL=$(echo "$POST_GPU" | awk -F',' '{print $1}')
    POST_GPU_MEM=$(echo "$POST_GPU" | awk -F',' '{print $2}')
    POST_GPU_TEMP=$(echo "$POST_GPU" | awk -F',' '{print $3}')
    
    # Track result
    if [[ "$RESULT" == "safe" ]]; then
        ((SAFE_COUNT++))
        RESULT_STR="safe"
    elif [[ "$RESULT" == "unsafe" ]]; then
        ((UNSAFE_COUNT++))
        RESULT_STR="unsafe"
    else
        RESULT_STR="error"
    fi
    
    # Log CSV and display progress
    echo "$i,$LATENCY,$RESULT_STR,$POST_GPU_UTIL,$POST_GPU_MEM,$POST_GPU_TEMP" >> "$CSV_FILE"
    printf "[%2d/%d] %4dms  GPU:%3d%%  Mem:%4dMB  Temp:%2d°C  [%s]\n" \
        "$i" "$NUM_ITERATIONS" "$LATENCY" "$POST_GPU_UTIL" "$POST_GPU_MEM" "$POST_GPU_TEMP" "$RESULT_STR"
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 3: Results Analysis"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Calculate statistics
AVG_LATENCY=$((TOTAL_LATENCY / NUM_ITERATIONS))

# Find min and max
MIN_LATENCY=${LATENCIES[0]}
MAX_LATENCY=${LATENCIES[0]}
for lat in "${LATENCIES[@]}"; do
    if [ $lat -lt $MIN_LATENCY ]; then
        MIN_LATENCY=$lat
    fi
    if [ $lat -gt $MAX_LATENCY ]; then
        MAX_LATENCY=$lat
    fi
done

# Calculate percentiles
IFS=$'\n' SORTED_LAT=($(sort -n <<<"${LATENCIES[*]}"))
unset IFS
P50_INDEX=$((NUM_ITERATIONS / 2))
P95_INDEX=$(((NUM_ITERATIONS * 95) / 100))
P99_INDEX=$(((NUM_ITERATIONS * 99) / 100))
P50=${SORTED_LAT[$P50_INDEX]}
P95=${SORTED_LAT[$P95_INDEX]:-${SORTED_LAT[-1]}}
P99=${SORTED_LAT[$P99_INDEX]:-${SORTED_LAT[-1]}}

# Performance metrics
THROUGHPUT=$(echo "scale=2; 1000 / $AVG_LATENCY" | bc)
THROUGHPUT_PER_HOUR=$(echo "scale=0; (3600000 / $AVG_LATENCY)" | bc)

echo "Latency Metrics:"
echo "  Minimum:       ${MIN_LATENCY}ms"
echo "  Maximum:       ${MAX_LATENCY}ms"
echo "  Average:       ${AVG_LATENCY}ms"
echo "  P50 (median):  ${P50}ms"
echo "  P95:           ${P95}ms"
echo "  P99:           ${P99}ms"
echo ""

echo "Throughput:"
echo "  Messages/sec:  $THROUGHPUT"
echo "  Messages/hour: $THROUGHPUT_PER_HOUR"
echo ""

echo "Classification Results:"
echo "  Safe:   $SAFE_COUNT"
echo "  Unsafe: $UNSAFE_COUNT"
echo "  Total:  $NUM_ITERATIONS"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 4: Cost Estimation"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Function to get GPU cost
get_gpu_cost() {
    local gpu_name="$1"
    if [[ "$gpu_name" == *"H100"* ]]; then echo "3.98"
    else echo "1.00"; fi
}

# Detect GPU type
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
echo "Detected GPU: $GPU_NAME"
echo ""

COST_PER_HOUR=$(get_gpu_cost "$GPU_NAME")

# Cost calculations
# Average latency in seconds
LATENCY_SEC=$(echo "scale=4; $AVG_LATENCY / 1000" | bc)

# Cost per message
COST_PER_MSG=$(echo "scale=8; ($LATENCY_SEC / 3600) * $COST_PER_HOUR" | bc)

# Cost per 1000 messages
COST_PER_1K=$(echo "scale=6; $COST_PER_MSG * 1000" | bc)

# Cost per 1M messages
COST_PER_1M=$(echo "scale=2; $COST_PER_MSG * 1000000" | bc)

# Annual cost (assuming 1M messages/day)
COST_PER_DAY=$(echo "scale=2; $COST_PER_1M / 1" | bc)
ANNUAL_COST=$(echo "scale=0; $COST_PER_DAY * 365" | bc)

echo "Cost per Message:"
echo "  \$$COST_PER_MSG (GPU @ \$$COST_PER_HOUR/hr)"
echo ""

echo "Projected Costs:"
echo "  Per 1,000 messages:    \$$COST_PER_1K"
echo "  Per 1,000,000 messages: \$$COST_PER_1M"
echo "  Per 1M messages/day:   \$$COST_PER_DAY"
echo "  Annual (1M msgs/day):  \$$ANNUAL_COST"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "SUMMARY REPORT"
echo "═══════════════════════════════════════════════════════════════"

cat << SUMMARY

Model:                 $MODEL_NAME
GPU:                   $GPU_NAME
Hourly Rate:           \$$COST_PER_HOUR
Iterations:            $NUM_ITERATIONS

Latency:
  Avg:                 ${AVG_LATENCY}ms
  Min/Max:             ${MIN_LATENCY}ms / ${MAX_LATENCY}ms
  P95:                 ${P95}ms

Throughput:
  Messages/sec:        $THROUGHPUT
  Messages/hour:       $THROUGHPUT_PER_HOUR

Cost per Message:      \$$COST_PER_MSG
Cost per 1M msgs:      \$$COST_PER_1M
Annual (1M/day):       \$$ANNUAL_COST

Recommendation:
$(
    if (( $(echo "$AVG_LATENCY < 300" | bc -l) )); then
        echo "  ✅ FAST: Excellent performance. Use for 100% sampling."
    elif (( $(echo "$AVG_LATENCY < 1000" | bc -l) )); then
        echo "  ✅ GOOD: Good performance. Consider sampling if cost is concern."
    elif (( $(echo "$AVG_LATENCY < 2000" | bc -l) )); then
        echo "  ⚠️  MODERATE: Acceptable. Use 1b model or sampling for high volume."
    else
        echo "  ⚠️  SLOW: Consider optimization (model, hardware, batching)."
    fi
)

Results Files:
  Detailed metrics: $CSV_FILE
  Full report:     $RESULTS_FILE

SUMMARY

echo ""
echo "✅ Test complete!"
echo ""
echo "To analyze results:"
echo "  cat $CSV_FILE | column -t -s',' | head -20"
echo "  # Plot with: gnuplot, matplotlib, etc."
