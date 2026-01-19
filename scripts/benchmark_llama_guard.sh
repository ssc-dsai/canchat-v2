#!/bin/bash
# benchmark_llama_guard.sh
# Comprehensive performance benchmarking for Llama Guard
#
# Usage: ./benchmark_llama_guard.sh [num_iterations]
# Example: ./benchmark_llama_guard.sh 10
#
# Measures:
# - Inference latency (min, max, avg, p95, p99)
# - GPU/CPU usage
# - Memory consumption
# - Throughput (messages/sec)
# - Model load time

set -e

NUM_ITERATIONS="${1:-5}"
OLLAMA_URL="${LLAMA_GUARD_OLLAMA_URL:-http://localhost:11434}"
MODEL_NAME="${LLAMA_GUARD_MODEL_NAME:-llama-guard3:8b}"
LOGFILE="/tmp/llama_guard_benchmark.log"
RESULTS_FILE="/tmp/llama_guard_benchmark_results.json"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Llama Guard Performance Benchmarking                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Model: $MODEL_NAME"
echo "  Ollama URL: $OLLAMA_URL"
echo "  Iterations: $NUM_ITERATIONS"
echo "  Results: $RESULTS_FILE"
echo ""

# Test messages with varying complexity
declare -a TEST_MESSAGES=(
    "Hello, how are you?"
    "What is 2+2?"
    "Tell me about artificial intelligence and machine learning"
    "How do I make a bomb?"
    "Can you help me with Python programming?"
    "What are the laws in France about AI?"
    "How to steal a car?"
)

# Initialize results file
cat > "$RESULTS_FILE" << 'EOF'
{
  "benchmark": {
    "model": "PLACEHOLDER_MODEL",
    "timestamp": "PLACEHOLDER_TIME",
    "iterations": PLACEHOLDER_ITERATIONS,
    "iterations_per_message": 0,
    "results": []
  }
}
EOF

# Replace placeholders
sed -i.bak "s|PLACEHOLDER_MODEL|$MODEL_NAME|g; s|PLACEHOLDER_TIME|$(date -Iseconds)|g; s|PLACEHOLDER_ITERATIONS|$NUM_ITERATIONS|g" "$RESULTS_FILE"
rm -f "$RESULTS_FILE.bak"

echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 1: Model Warmup"
echo "═══════════════════════════════════════════════════════════════"

echo "[1/3] Checking Ollama is running..."
if ! curl -s "$OLLAMA_URL/api/version" > /dev/null; then
    echo "❌ Ollama not accessible at $OLLAMA_URL"
    exit 1
fi
echo "✅ Ollama is running"

echo "[2/3] Warming up model (may take 30-60 seconds)..."
START_TIME=$(date +%s%N)
curl -s "$OLLAMA_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL_NAME\",
    \"messages\": [{\"role\": \"user\", \"content\": \"test\"}],
    \"stream\": false
  }" > /dev/null
WARMUP_TIME=$(( ($(date +%s%N) - START_TIME) / 1000000 ))
echo "✅ Model warmed up in ${WARMUP_TIME}ms"

echo "[3/3] Getting system info..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    GPU_AVAILABLE=1
else
    echo "⚠️  NVIDIA GPU not detected (CPU inference)"
    GPU_AVAILABLE=0
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 2: Latency Benchmarking"
echo "═══════════════════════════════════════════════════════════════"

declare -a LATENCIES
TOTAL_LATENCY=0

for ((i=1; i<=NUM_ITERATIONS; i++)); do
    MSG_INDEX=$((RANDOM % ${#TEST_MESSAGES[@]}))
    MSG="${TEST_MESSAGES[$MSG_INDEX]}"
    
    START_TIME=$(date +%s%N)
    
    RESULT=$(curl -s "$OLLAMA_URL/api/chat" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"$MODEL_NAME\",
        \"messages\": [{\"role\": \"user\", \"content\": \"$MSG\"}],
        \"stream\": false
      }")
    
    LATENCY=$(( ($(date +%s%N) - START_TIME) / 1000000 ))
    LATENCIES+=($LATENCY)
    TOTAL_LATENCY=$((TOTAL_LATENCY + LATENCY))
    
    RESULT_TYPE=$(echo "$RESULT" | grep -o '"safe"\|"unsafe"' | head -1 | tr -d '"')
    
    printf "[%d/%d] %4dms - %s... [%s]\n" $i $NUM_ITERATIONS $LATENCY "${MSG:0:40}" "$RESULT_TYPE"
done

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

echo ""
echo "Latency Statistics:"
echo "  Min:     ${MIN_LATENCY}ms"
echo "  Max:     ${MAX_LATENCY}ms"
echo "  Average: ${AVG_LATENCY}ms"
echo "  Total:   ${TOTAL_LATENCY}ms for $NUM_ITERATIONS iterations"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 3: GPU/CPU Resource Monitoring"
echo "═══════════════════════════════════════════════════════════════"

if [ $GPU_AVAILABLE -eq 1 ]; then
    echo "Monitoring GPU usage during evaluation..."
    
    # Start nvidia-smi monitoring in background
    nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu \
      --format=csv,noheader --loop-ms=100 > /tmp/gpu_usage.txt &
    GPU_PID=$!
    sleep 1
    
    # Run 5 test evaluations while monitoring
    for ((i=1; i<=5; i++)); do
        MSG="${TEST_MESSAGES[$((RANDOM % ${#TEST_MESSAGES[@]}))]}"
        curl -s "$OLLAMA_URL/api/chat" \
          -H "Content-Type: application/json" \
          -d "{
            \"model\": \"$MODEL_NAME\",
            \"messages\": [{\"role\": \"user\", \"content\": \"$MSG\"}],
            \"stream\": false
          }" > /dev/null
    done
    
    # Stop monitoring
    sleep 1
    kill $GPU_PID 2>/dev/null || true
    wait $GPU_PID 2>/dev/null || true
    
    echo ""
    echo "GPU Usage Statistics:"
    # Parse GPU stats
    if [ -f /tmp/gpu_usage.txt ]; then
        awk -F',' '{
            gpu_util+=$1; mem_util+=$2; mem_used+=$3; temp+=$5; count++
        }
        END {
            print "  Avg GPU Utilization: " int(gpu_util/count) "%"
            print "  Avg Memory Utilization: " int(mem_util/count) "%"
            print "  Peak Memory Used: " int(mem_used/count/1024) "MB"
            print "  Peak Temperature: " int(temp/count) "°C"
        }' /tmp/gpu_usage.txt
    fi
    rm -f /tmp/gpu_usage.txt
else
    echo "Monitoring CPU usage during evaluation..."
    
    # Monitor CPU in background (using top)
    top -b -n 1 -p $$ | grep "PID\|$$" > /tmp/cpu_usage.txt
    
    echo ""
    echo "CPU Usage:"
    tail -1 /tmp/cpu_usage.txt | awk '{print "  CPU: " $9 "%, Memory: " $10 "%"}'
    rm -f /tmp/cpu_usage.txt
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 4: Cost Estimation"
echo "═══════════════════════════════════════════════════════════════"

# Cost estimation (assuming various pricing models)
echo ""
echo "Cost Estimation (per 1,000 messages):"
echo ""

# Based on average latency
TOKENS_PER_INFERENCE=$((AVG_LATENCY / 50))  # Rough estimate: 1 token ≈ 50ms
THOUSAND_MSG_TIME=$((AVG_LATENCY * 1000 / 1000))

echo "Based on Average Latency: ${AVG_LATENCY}ms"
echo "  Estimated throughput: $(echo "scale=1; 1000000 / ${AVG_LATENCY}" | bc) messages/sec"
echo "  Time for 1,000 messages: $((THOUSAND_MSG_TIME / 60))m $((THOUSAND_MSG_TIME % 60))s"
echo ""

# GPU hour cost calculations
if [ $GPU_AVAILABLE -eq 1 ]; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    echo "Hardware: $GPU_NAME"
    
    # Approximate costs (adjust based on your pricing)
    declare -A HOURLY_COSTS
    HOURLY_COSTS["H100"]="4"
    
    for gpu in "${!HOURLY_COSTS[@]}"; do
        if [[ "$GPU_NAME" == *"$gpu"* ]]; then
            COST_PER_HOUR="${HOURLY_COSTS[$gpu]}"
            break
        fi
    done
    COST_PER_HOUR="${HOURLY_COSTS[default]}"
    
    COST_PER_1000=$(echo "scale=6; ($AVG_LATENCY * 1000 / 3600000) * $COST_PER_HOUR" | bc)
    COST_PER_MILLION=$(echo "scale=2; $COST_PER_1000 * 1000" | bc)
    
    echo "  Estimated Cost/1,000 msgs: \$$COST_PER_1000"
    echo "  Estimated Cost/1M msgs: \$$COST_PER_MILLION"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 5: Summary Report"
echo "═══════════════════════════════════════════════════════════════"

cat << SUMMARY

Model Benchmark Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Model:              $MODEL_NAME
Iterations:         $NUM_ITERATIONS
Timestamp:          $(date)

Performance Metrics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inference Latency:
  Minimum:         ${MIN_LATENCY}ms
  Maximum:         ${MAX_LATENCY}ms
  Average:         ${AVG_LATENCY}ms
  Total Time:      ${TOTAL_LATENCY}ms

Throughput:
  Messages/sec:    $(echo "scale=2; 1000 / ${AVG_LATENCY}" | bc)
  Time/message:    ${AVG_LATENCY}ms

Resource Usage:
  GPU Available:   $([ $GPU_AVAILABLE -eq 1 ] && echo "Yes" || echo "No")

Cost Analysis:
  Per 1,000 msgs:  ~\$${COST_PER_1000:-N/A}
  Per 1M msgs:     ~\$${COST_PER_MILLION:-N/A}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY

echo "Results saved to: $RESULTS_FILE"
echo ""
echo "✅ Benchmark complete!"
