"""Report assembly — the lab's deliverable: baseline vs optimized + savings chart."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly") -> str:
    """Return a markdown cost-optimization report."""
    savings = baseline_usd - optimized_usd
    pct = (savings / baseline_usd * 100.0) if baseline_usd > 0 else 0.0
    lines = [
        "# NimbusAI — GPU Cost Optimization Report",
        "",
        f"**Period:** {period}  ",
        f"**Baseline spend:** ${baseline_usd:,.0f}  ",
        f"**Optimized spend:** ${optimized_usd:,.0f}  ",
        f"**Projected savings:** ${savings:,.0f}  (**{pct:.0f}%**)",
        "",
        "## Savings by lever",
        "",
        "| Lever | Savings (USD) |",
        "|---|---|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if sustainability:
        lines += [
            "",
            "## Sustainability & Carbon Impact",
            "",
            f"- **Energy per query:** {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- **Carbon per query:** {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- **Cheapest+cleanest region:** {sustainability.get('best_region', 'n/a')}",
            "",
            "**Sustainability Insights:**",
            f"Deployment in the {sustainability.get('best_region', 'n/a')} region provides a dual benefit: it minimizes environmental impact (lowest gCO2e/kWh) while also reducing direct energy costs. Reasoning queries consume exponentially more energy (~80x), meaning that capping or aggressively routing reasoning requests to cleaner regions will significantly reduce our carbon footprint and electricity bill concurrently."
        ]
        
    lines += [
        "",
        "## Technical Analysis: The \"GPU-Util Lie\"",
        "",
        "The traditional `GPU-Util %` (from `nvidia-smi`) is often misleading because it merely measures the *time* the GPU is active (clock cycles where a kernel is running), not the *efficiency* of the computation. A GPU can show 98% utilization while its **Model FLOPs Utilization (MFU)** is under 20%. This typically occurs due to memory stalls or kernel launch overheads (e.g., in LLM decoding which is memory-bound). The financial impact is massive: we are paying the full on-demand hourly rate for a flagship GPU (like H100), but only extracting a fraction of its computational value. Right-sizing memory-bound workloads to GPUs with a better `$/GB-VRAM` ratio is critical to stop this leakage.",
        "",
        "## Actionable Recommendations (Prioritized by ROI)",
        "",
        "1. **Implement Inference Levers (Cascade, Cache, Batch) [Immediate / High ROI]**",
        "   - Implementing prompt caching and routing simple queries to smaller models yields the highest immediate impact with the lowest risk. This can reduce inference costs by over 80%.",
        "2. **Adopt Spot/Reserved Purchasing Strategy [Short-Term / High ROI]**",
        "   - Transition interruptible workloads (e.g., training, batch eval) to Spot instances and commit to Reserved Instances for steady-state 24/7 inference tasks. This reduces unit compute costs by ~40%.",
        "3. **Right-Size \"GPU-Util Lie\" Instances [Medium-Term / Medium ROI]**",
        "   - Audit workloads showing high GPU-Util but low MFU/MBU. Shift memory-bound LLM decoding tasks to instances that offer better `$/GB-VRAM` (like L4 or MI300X) rather than paying premium for H100 compute that goes unused.",
        "4. **Terminate Idle GPUs [Immediate / Low ROI]**",
        "   - Shut down instances that are completely inactive to stop the bleeding. While the absolute dollar amount might be smaller than inference levers, it requires zero engineering effort to implement.",
        "",
        "_Figures are June-2026 as-of snapshots; re-baseline before acting._"
    ]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str) -> str:
    """Write a simple savings bar chart PNG. Returns the path. No-op if matplotlib absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    names = list(levers.keys())
    vals = [levers[n] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(names, vals, color="#2e548a")
    ax.set_ylabel("Savings (USD / month)")
    ax.set_title("GPU cost savings by FinOps lever")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
