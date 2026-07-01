# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,741  
**Projected savings:** $12,392  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $540 |
| Kill idle GPUs | $600 |

## Sustainability & Carbon Impact

- **Energy per query:** 0.24 Wh
- **Carbon per query:** 0.091 gCO2e
- **Cheapest+cleanest region:** europe-north1

**Sustainability Insights:**
Deployment in the europe-north1 region provides a dual benefit: it minimizes environmental impact (lowest gCO2e/kWh) while also reducing direct energy costs. Reasoning queries consume exponentially more energy (~80x), meaning that capping or aggressively routing reasoning requests to cleaner regions will significantly reduce our carbon footprint and electricity bill concurrently.

## Technical Analysis: The "GPU-Util Lie"

The traditional `GPU-Util %` (from `nvidia-smi`) is often misleading because it merely measures the *time* the GPU is active (clock cycles where a kernel is running), not the *efficiency* of the computation. A GPU can show 98% utilization while its **Model FLOPs Utilization (MFU)** is under 20%. This typically occurs due to memory stalls or kernel launch overheads (e.g., in LLM decoding which is memory-bound). The financial impact is massive: we are paying the full on-demand hourly rate for a flagship GPU (like H100), but only extracting a fraction of its computational value. Right-sizing memory-bound workloads to GPUs with a better `$/GB-VRAM` ratio is critical to stop this leakage.

## Actionable Recommendations (Prioritized by ROI)

1. **Implement Inference Levers (Cascade, Cache, Batch) [Immediate / High ROI]**
   - Implementing prompt caching and routing simple queries to smaller models yields the highest immediate impact with the lowest risk. This can reduce inference costs by over 80%.
2. **Adopt Spot/Reserved Purchasing Strategy [Short-Term / High ROI]**
   - Transition interruptible workloads (e.g., training, batch eval) to Spot instances and commit to Reserved Instances for steady-state 24/7 inference tasks. This reduces unit compute costs by ~40%.
3. **Right-Size "GPU-Util Lie" Instances [Medium-Term / Medium ROI]**
   - Audit workloads showing high GPU-Util but low MFU/MBU. Shift memory-bound LLM decoding tasks to instances that offer better `$/GB-VRAM` (like L4 or MI300X) rather than paying premium for H100 compute that goes unused.
4. **Terminate Idle GPUs [Immediate / Low ROI]**
   - Shut down instances that are completely inactive to stop the bleeding. While the absolute dollar amount might be smaller than inference levers, it requires zero engineering effort to implement.

_Figures are June-2026 as-of snapshots; re-baseline before acting._